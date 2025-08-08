# data/scrape.py

"""Projections and ADP scrapers, refactored for robustness and best practices."""

import logging
import os
import re
import time
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup, NavigableString
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration and Constants ---

LOGGER = logging.getLogger(__name__)
DIR = os.path.dirname(__file__)
RAW_PROJECTIONS = os.path.join(DIR, "raw", "projections")
RAW_ADP = os.path.join(DIR, "raw", "adp")

TEAM_TO_ABRV_MAP = {
    "Cardinals": "ARI", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF",
    "Panthers": "CAR", "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE",
    "Cowboys": "DAL", "Broncos": "DEN", "Lions": "DET", "Packers": "GB",
    "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX", "Chiefs": "KC",
    "Las Vegas": "LV", "Raiders": "LV", "Dolphins": "MIA", "Vikings": "MIN",
    "Patriots": "NE", "Saints": "NO", "Giants": "NYG", "N.Y. Giants": "NYG",
    "Jets": "NYJ", "N.Y. Jets": "NYJ", "Eagles": "PHI", "Steelers": "PIT",
    "Chargers": "LAC", "L.A. Chargers": "LAC", "49ers": "SF", "Seahawks": "SEA",
    "Rams": "LAR", "L.A. Rams": "LAR", "Buccaneers": "TB", "Titans": "TEN",
    "Commanders": "WSH", "Team": "WSH",
}
ABRV_TO_TEAM_MAP = {v: k for k, v in TEAM_TO_ABRV_MAP.items()}

# --- WebDriver Management ---

def setup_driver() -> webdriver.Chrome:
    """Initializes a Selenium WebDriver with robust options for headless environments."""
    LOGGER.info("Setting up new Chrome WebDriver instance.")
    options = Options()
    arguments = [
        "--headless", "--no-sandbox", "--disable-dev-shm-usage", "--start-maximized",
        "--enable-automation", "--window-size=1200x900", "--disable-browser-side-navigation",
        "--disable-gpu",
    ]
    for arg in arguments:
        options.add_argument(arg)
    
    # ** THE FIX **: Explicitly tells Selenium where your Chrome binary is.
    options.binary_location = "/usr/bin/google-chrome"
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    LOGGER.info("WebDriver setup complete.")
    return driver

# --- Helper Functions ---

def _scroll(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

def _add_player_key(df):
    name_regex = re.compile(r"[^a-z ]+")
    def create_key(row):
        name_text = str(row.get("name", "")).lower().replace("sr", "").replace("st.", "").strip()
        name_text = name_regex.sub("", name_text).strip().replace("  ", " ").split(" ")
        last_name = name_text[1] if len(name_text) > 1 else name_text[0]
        pos = row.get('pos', 'NA')
        team = row.get('team', 'NA')
        return f'{last_name}_{pos}_{team}'

    df["key"] = df.apply(create_key, axis=1)
    return df.drop_duplicates(subset=["key"])

# --- Scraper Functions ---

def scrape_fantasy_pros_adp(driver: webdriver.Chrome, year: int):
    """Scrape Fantasy Pros ADP."""
    LOGGER.info(f"Scraping FantasyPros ADP for {year}")
    urls = {
        "std": f"https://www.fantasypros.com/nfl/adp/overall.php?year={year}",
        "half_ppr": f"https://www.fantasypros.com/nfl/adp/half-point-ppr-overall.php?year={year}",
        "ppr": f"https://www.fantasypros.com/nfl/adp/ppr-overall.php?year={year}",
    }
    merged_df = None
    for ppr_type, url in urls.items():
        LOGGER.info(f"Fetching {ppr_type} ADP from {url}")
        driver.get(url)
        time.sleep(3) # Increased wait time for reliability
        
        try:
            # Use pandas to directly parse the HTML table
            dfs = pd.read_html(driver.page_source)
            if not dfs:
                LOGGER.error(f"No tables found at {url}")
                continue
            
            df = dfs[0]
            df = df.rename(columns={"Player Team (Bye)": "Player", "AVG": ppr_type, "Pos": "pos"})
            
            # Data Cleaning
            df["pos"] = df["pos"].str.extract(r'([A-Z]+)')[0]
            df['team'] = df['Player'].apply(lambda x: x.split()[-1] if isinstance(x, str) else None)
            df['name'] = df['Player'].apply(lambda x: ' '.join(x.split()[:-1]) if isinstance(x, str) else None)
            
            current_df = df[["name", "team", "pos", ppr_type]].copy()
            current_df = _add_player_key(current_df)

            if merged_df is None:
                merged_df = current_df
            else:
                merged_df = pd.merge(merged_df, current_df[['key', ppr_type]], on="key", how="outer")

        except Exception as e:
            LOGGER.error(f"Could not parse data for {ppr_type} at {url}: {e}")
            continue

    if merged_df is not None:
        output_path = os.path.join(RAW_ADP, f"FantasyPros-ADP-{year}.csv")
        merged_df.to_csv(output_path, index=False)
        LOGGER.info(f"Successfully saved merged FantasyPros ADP data to {output_path}")
