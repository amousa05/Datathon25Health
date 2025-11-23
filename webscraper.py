import csv
import time

import selenium

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URL = "https://www.hqontario.ca/system-performance/time-spent-in-emergency-departments"

# -------------------------------------------------------------------
# Helper: set up Selenium WebDriver (Chrome here, but you can swap)
# -------------------------------------------------------------------
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # Uncomment if you want headless mode:
    # options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    return driver


# -------------------------------------------------------------------
# Main scraping logic
# -------------------------------------------------------------------
def scrape_hqontario(output_csv="hqontario_ed_metrics.csv"):
    driver = get_driver()
    wait = WebDriverWait(driver, 15)

    try:
        driver.get(URL)

        # OPTIONAL: If you ever need to click "List all reporting Hospitals",
        # you can try this (wrapped in try/except so it doesn't crash if not needed):
        try:
            list_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(),'List all reporting Hospitals')]")
                )
            )
            list_btn.click()
            time.sleep(3)
        except Exception:
            # If the button isn't there or is already active, just continue
            pass

        # ------------------------------------------------------------------
        # 1) Find the comparison table and each hospital row in <tbody>
        # ------------------------------------------------------------------
        # We look for the table that follows the "Compare results across hospitals"
        # heading and then grab its <tbody> rows.
        tbody = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//h3[contains(., 'Compare results across hospitals') or "
                    "contains(., 'Compare results across hospitals for the indicator selected')]/"
                    "following::table[1]/tbody",
                )
            )
        )
        rows = tbody.find_elements(By.TAG_NAME, "tr")

        print(f"Found {len(rows)} hospital rows in the comparison table.")

        # ------------------------------------------------------------------
        # 2) Prepare CSV for output
        # ------------------------------------------------------------------
        # The example row you gave: 0.7,1.3,97,1.6,100
        # I'm also including the hospital name as first column (handy) —
        # if you *really* only want the 5 numbers, just drop 'hospitalname'
        # from writer.writerow below.
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "HospitalName",
                    "Metric1",
                    "Metric2",
                    "Metric3",
                    "Metric4",
                    "Metric5",
                ]
            )

            # ------------------------------------------------------------------
            # 3) For each hospital row: grab name, search, select, scrape metrics
            # ------------------------------------------------------------------
            for idx, row in enumerate(rows, start=1):
                # First <td> in the row is the hospital name
                tds = row.find_elements(By.TAG_NAME, "td")
                if not tds:
                    continue

                raw_name = tds[0].text
                if not raw_name.strip():
                    continue

                # Your requested trim logic:
                # - trim whitespace at beginning/end
                # - add space at the end
                # - trim again
                hospitalname = raw_name.strip()
                hospitalname = (hospitalname + " ").strip()

                print(f"[{idx}/{len(rows)}] Processing: {hospitalname}")

                # ------------------------------------------------------------------
                # Enter hospital name into the search bar
                # input#HospitalName.form-control.input-lg.ui-autocomplete-input
                # ------------------------------------------------------------------
                search_input = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "input#HospitalName.form-control.input-lg.ui-autocomplete-input",
                        )
                    )
                )

                # Clear previous value and type current hospital
                search_input.clear()
                search_input.send_keys(hospitalname)

                # Wait 3 seconds (as per your spec) for suggestions to appear
                time.sleep(3)

                # Select suggested result (Down arrow + Enter)
                search_input.send_keys(Keys.ARROW_DOWN)
                search_input.send_keys(Keys.ENTER)

                # Give the page time to update the metrics
                time.sleep(3)

                # ------------------------------------------------------------------
                # Scrape metrics:
                #   <h6 class="text-uppercase" id="surgery-period"> September 2025</h6>
                #   <font class="numberStyle2">0.7</font>
                #   <font class="numberStyle2">1.3</font>
                #   <span class="numberStyle2">97%</span>
                #   <font class="numberStyle2">1.6</font>
                #   <span class="numberStyle2">100%</span>
                #
                # We'll grab the first 5 .numberStyle2 values that appear on the page
                # after the hospital is selected.
                # ------------------------------------------------------------------
                try:
                    # Optional: wait for period element to be present (sanity check)
                    _ = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "h6#surgery-period.text-uppercase")
                        )
                    )
                except Exception:
                    # If period doesn't appear, we still try to read numbers
                    pass

                # Grab font/span with class numberStyle2
                number_elems = driver.find_elements(
                    By.CSS_SELECTOR, "font.numberStyle2, span.numberStyle2"
                )

                if len(number_elems) < 5:
                    print(
                        f"  Warning: found only {len(number_elems)} numberStyle2 elements. Skipping."
                    )
                    continue

                # Take the first 5 values, strip whitespace and '%' sign
                values = []
                for e in number_elems[:5]:
                    txt = e.text.strip().replace("%", "")
                    values.append(txt)

                if len(values) != 5:
                    print(f"  Warning: expected 5 numeric values, got {len(values)}. Skipping.")
                    continue

                # Write row: hospital name + five metrics
                writer.writerow([hospitalname] + values)

    finally:
        driver.quit()


if __name__ == "__main__":
    scrape_hqontario("hqontario_ed_metrics.csv")
    print("Scraping complete.")
