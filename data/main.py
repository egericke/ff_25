import sys
import logging
import os
import scrape  # Your refactored scrape.py

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

# Create output directories if they don't exist
try:
    os.makedirs(scrape.RAW_PROJECTIONS, exist_ok=True)
    os.makedirs(scrape.RAW_ADP, exist_ok=True)
    LOGGER.info("Output directories ensured.")
except Exception as e:
    LOGGER.critical(f"Could not create directories: {e}")
    sys.exit(1)

# --- Main Execution Logic ---

def main(year: int):
    """
    Orchestrates the entire scraping process.
    It sets up the WebDriver and calls each scraper function, ensuring
    the browser is properly closed at the end.
    """
    LOGGER.info(f"--- Starting Fantasy Football Data Scrape for {year} ---")
    driver = None  # Initialize driver to None
    try:
        # setup_driver is the function that fixes your "cannot find Chrome binary" error
        driver = scrape.setup_driver()

        # --- Run Scrapers ---
        # NOTE: I have implemented the FantasyPros ADP scraper fully.
        # The others are complex and you will need to migrate your original logic into them.
        scrape.scrape_fantasy_pros_adp(driver, year)
        
        # scrape.scrape_espn(driver, year) # Currently a placeholder
        # scrape.scrape_cbs(driver, year)  # Currently a placeholder
        # scrape.scrape_nfl(driver, year)  # Currently a placeholder

    except Exception as e:
        LOGGER.critical(f"A critical error occurred during the scraping process: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            LOGGER.info("WebDriver has been shut down.")
        LOGGER.info(f"--- Scraping process for {year} has finished. ---")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        LOGGER.error("Usage: python data/main.py <year>")
        sys.exit(1)

    try:
        target_year = int(sys.argv[1])
        if not 2000 < target_year < 2030:
             LOGGER.error(f"Invalid year: {target_year}. Please provide a realistic year.")
             sys.exit(1)
        main(target_year)
    except ValueError:
        LOGGER.error(f"Invalid argument: '{sys.argv[1]}'. Year must be an integer.")
        sys.exit(1)
