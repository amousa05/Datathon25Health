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
    # options.add_argument("--headless=new")  # uncomment for headless
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
            # If button not there / already active, just continue
            pass

        # --------------------------------------------------------------
        # 1) Grab hospital names from the comparison table into a list
        # --------------------------------------------------------------
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

            # Skip province-level aggregates like "Ontario"
            if name.upper() in ("ONTARIO", "ALL ONTARIO", "PROVINCE TOTAL"):
                continue

            hospital_names.append(name)

        print(f"Collected {len(hospital_names)} hospital names.")

        # --------------------------------------------------------------
        # 2) Open CSV and write header
        # --------------------------------------------------------------
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "HOSPITAL",
                "DATE",
                "WT_FA_E",         # Wait Time to First Assessment in ED
                "LS_E_LU_NA",      # Length of Stay ED Low-Urgency, Not Admitted
                "PCNT_F_4H_TT",    # % finished within 4h target time
                "LS_E_HU_NA",      # Length of Stay ED High-Urgency, Not Admitted
                "PCNT_F_8H_TT",    # % finished within 8h target time
                "LS_E_A",          # Length of Stay ED - All (Admitted)
                "PCNT_AFE_8H_TT"   # % admitted from ED within 8h target time
            ])

            # ----------------------------------------------------------
            # 3) Loop over hospital names (strings only => no stale elems)
            # ----------------------------------------------------------
            for idx, raw_name in enumerate(hospital_names, start=1):
                # Your trim logic: strip, add space, strip again
                hospitalname = raw_name.strip()
                hospitalname = (hospitalname + " ").strip()

                print(f"[{idx}/{len(hospital_names)}] Processing: {hospitalname}")

                # Find the search input every iteration
                search_input = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "input#HospitalName.form-control.input-lg.ui-autocomplete-input",
                        )
                    )
                )

                # Clear and type hospital name
                search_input.clear()
                search_input.send_keys(hospitalname)

                # Wait for suggestions to appear
                time.sleep(3)

                # Select first suggestion (Down + Enter)
                search_input.send_keys(Keys.ARROW_DOWN)
                search_input.send_keys(Keys.ENTER)

                # Let page update metrics
                time.sleep(3)

                # ------------------------------------------------------
                # Get DATE (period)
                # ------------------------------------------------------
                try:
                    period_elem = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "h6#surgery-period.text-uppercase")
                        )
                    )
                    # Uppercase to match example "SEPTEMBER 2025"
                    period_text = period_elem.text.strip().upper()
                except Exception:
                    print("  Warning: could not find period text; skipping hospital.")
                    continue

                # ------------------------------------------------------
                # Get metrics from <font/span class="numberStyle2">
                # ------------------------------------------------------
                number_elems = driver.find_elements(
                    By.CSS_SELECTOR, "font.numberStyle2, span.numberStyle2"
                )

                # We still require at least the first 5 metrics
                if len(number_elems) < 5:
                    print(
                        f"  Warning: found only {len(number_elems)} numberStyle2 elements. Skipping."
                    )
                    continue

                def clean_value(idx):
                    """Return cleaned text for numberStyle2 at position idx, or '' if missing."""
                    if len(number_elems) > idx:
                        return number_elems[idx].text.strip().replace("%", "")
                    return ""

                # Base 5 metrics (must exist)
                wt_fa_e      = clean_value(0)  # Wait time to first assessment
                ls_e_lu_na   = clean_value(1)  # LOS low urgency, not admitted
                pcnt_f_4h_tt = clean_value(2)  # % finished in 4h
                ls_e_hu_na   = clean_value(3)  # LOS high urgency, not admitted
                pcnt_f_8h_tt = clean_value(4)  # % finished in 8h

                # Extra 2 metrics (optional; blank if missing)
                ls_e_a          = clean_value(5)  # LOS admitted
                pcnt_afe_8h_tt  = clean_value(6)  # % admitted finished within 8h

                # Write CSV row:
                # HOSPITAL,DATE,0.7,2.3,88,3.9,94,23.7,17
                writer.writerow([
                    hospitalname,
                    period_text,
                    wt_fa_e,
                    ls_e_lu_na,
                    pcnt_f_4h_tt,
                    ls_e_hu_na,
                    pcnt_f_8h_tt,
                    ls_e_a,
                    pcnt_afe_8h_tt
                ])

    finally:
        driver.quit()


if __name__ == "__main__":
    scrape_hqontario("hqontario_ed_all_metrics.csv")
    print("Scraping complete.")
