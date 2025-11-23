import csv
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://www.hqontario.ca/system-performance/time-spent-in-emergency-departments"


def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless=new")  # uncomment if you want headless
    driver = webdriver.Chrome(options=options)
    return driver


def scrape_hqontario(output_csv="hqontario_ed_metrics.csv"):
    driver = get_driver()
    wait = WebDriverWait(driver, 15)

    try:
        driver.get(URL)

        # Try clicking "List all reporting Hospitals" if present
        try:
            list_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(),'List all reporting Hospitals')]")
                )
            )
            list_btn.click()
            time.sleep(3)
        except Exception:
            # If button not there / already active, continue
            pass

        # ------------------------------------------------------------------
        # 1) Grab the hospital comparison table body
        #    and extract hospital names into a Python list
        # ------------------------------------------------------------------
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

        hospital_names = []
        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if not tds:
                continue
            name = tds[0].text.strip()
            if not name:
                continue

            # Skip aggregate rows like "Ontario"
            if name.upper() in ("ONTARIO", "ALL ONTARIO", "PROVINCE TOTAL"):
                continue

            hospital_names.append(name)

        print(f"Collected {len(hospital_names)} hospital names.")

        # ------------------------------------------------------------------
        # 2) Open CSV and write header
        # ------------------------------------------------------------------
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "HOSPITAL",
                "DATE",
                "WT_FA_E",       # Wait Time to First Assessment in ED
                "LS_E_LU_NA",    # Length of Stay ED Low-Urgency, Not Admitted
                "PCNT_F_4H_TT",  # % finished within 4h target time
                "LS_E_HU_NA",    # Length of Stay ED High-Urgency, Not Admitted
                "PCNT_F_8H_TT"   # % finished within 8h target time
            ])

            # ------------------------------------------------------------------
            # 3) Loop over hospital names (plain strings => no stale elements)
            # ------------------------------------------------------------------
            for idx, raw_name in enumerate(hospital_names, start=1):
                # Your trim logic: strip, add space, strip
                hospitalname = raw_name.strip()
                hospitalname = (hospitalname + " ").strip()

                print(f"[{idx}/{len(hospital_names)}] Processing: {hospitalname}")

                # Find and use the search bar each iteration
                search_input = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "input#HospitalName.form-control.input-lg.ui-autocomplete-input",
                        )
                    )
                )

                # Clear previous value and type new one
                search_input.clear()
                search_input.send_keys(hospitalname)

                # Wait for autocomplete suggestions
                time.sleep(3)

                # Select first suggestion (Down + Enter)
                search_input.send_keys(Keys.ARROW_DOWN)
                search_input.send_keys(Keys.ENTER)

                # Give the page time to update metrics
                time.sleep(3)

                # ------------------------------------------------------------------
                # Scrape DATE and metrics
                # ------------------------------------------------------------------
                try:
                    period_elem = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "h6#surgery-period.text-uppercase")
                        )
                    )
                    period_text = period_elem.text.strip()
                except Exception:
                    print("  Warning: could not find period text; skipping hospital.")
                    continue

                # Collect numeric metrics
                number_elems = driver.find_elements(
                    By.CSS_SELECTOR, "font.numberStyle2, span.numberStyle2"
                )

                if len(number_elems) < 5:
                    print(
                        f"  Warning: found only {len(number_elems)} numberStyle2 elements. Skipping."
                    )
                    continue

                values = []
                for e in number_elems[:5]:
                    txt = e.text.strip().replace("%", "")
                    values.append(txt)

                if len(values) != 5:
                    print(
                        f"  Warning: expected 5 numeric values, got {len(values)}. Skipping."
                    )
                    continue

                # Row: hospital, date, 0.7,1.3,97,1.6,100
                writer.writerow([hospitalname, period_text] + values)

    finally:
        driver.quit()


if __name__ == "__main__":
    scrape_hqontario("hqontario_ed_metrics.csv")
    print("Scraping complete.")
