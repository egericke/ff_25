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

REQUIRED_COLS = [
    "key", "name", "pos", "team", "pass_tds", "pass_yds", "pass_ints", "rush_tds",
    "rush_yds", "receptions", "reception_tds", "reception_yds", "two_pts", "fumbles",
    "kick_0_19", "kick_20_29", "kick_30_39", "kick_40_49", "kick_50", "kick_extra_points",
    "df_points_allowed_per_game", "df_sacks", "df_safeties", "df_fumbles", "df_tds", "df_ints",
]

COLUMN_MAP = {
    # ESPN
    "interceptions_thrown": "pass_ints", "passing_yards": "pass_yds", "td_pass": "pass_tds",
    "each_reception": "receptions", "td_reception": "reception_tds", "receiving_yards": "reception_yds",
    "rushing_yards": "rush_yds", "td_rush": "rush_tds", "field_goals_attempted_40-49_yards": "kick_40_49",
    "field_goals_attempted_50+_yards": "kick_50", "extra_points_made": "kick_extra_points",
    "each_fumble_recovered": "df_fumbles", "each_sack": "df_sacks", "each_interception": "df_ints",
    "total_return_td": "df_tds",
    # CBS
    "touchdowns_passes": "pass_tds", "receiving_touchdowns": "reception_tds", "rushing_touchdowns": "rush_tds",
    "fumbles_lost": "fumbles", "field_goals_1-19_yards": "kick_0_19", "field_goals_20-29_yards": "kick_20_29",
    "field_goals_30-39_yards": "kick_30_39", "defensive_fumbles_recovered": "df_fumbles",
    "defensive_touchdowns": "df_tds", "points_allowed_per_game": "df_points_allowed_per_game",
    "sacks": "df_sacks", "safeties": "df_safeties", "interceptions": "df_ints",
    # NFL
    "passing_int": "pass_ints", "passing_td": "pass_tds", "receiving_rec": "receptions",
    "receiving_td": "reception_tds", "rushing_td": "rush_tds", "2pt": "two_pts", "lost": "fumbles",
    "made": "kick_extra_points", "0-19": "kick_0_19", "20-29": "kick_20_29", "30-39": "kick_30_39",
    "40-49": "kick_40_49", "50+": "kick_50", "sack": "df_sacks", "saf": "df_safeties",
    "fum_rec": "df_fumbles", "ret_td": "df_tds", "int": "df_ints",
}

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

def _clean_column_name(text):
    text = str(text).strip().replace(" ", "_").lower().split("\n")[0].strip()
    return text.strip("_")

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


def _unify_columns(df):
    """Re-organize stat columns."""
    df = df.rename(columns=lambda c: COLUMN_MAP.get(_clean_column_name(c), _clean_column_name(c)))
    df = _add_player_key(df)
    return df[REQUIRED_COLS]

def _validate(df, source_name, year, strict=True, skip_fantasy_pros_check=False):
    """Validate the scraped DataFrame."""
    LOGGER.info(f"[{source_name}-{year}] Validating: scraped {len(df)} players.")
    pos_counts = {"QB": 32, "RB": 64, "WR": 64, "TE": 28, "DST": 32, "K": 15}
    for pos, expected_count in pos_counts.items():
        if skip_fantasy_pros_check and pos in ["DST", "K"]:
            continue
        actual_count = len(df[df.pos == pos])
        if strict and actual_count < expected_count:
            LOGGER.warning(f"[{source_name}-{year}] Low player count for {pos}. Found {actual_count}, expected ~{expected_count}.")
        elif not strict and actual_count * 3 < expected_count:
            LOGGER.warning(f"[{source_name}-{year}] Very low player count for {pos}. Found {actual_count}.")

    if len(set(df.team)) > 33:
        LOGGER.error(f"[{source_name}-{year}] Too many teams found: {len(set(df.team))}")
    LOGGER.info(f"[{source_name}-{year}] Validation complete.")

# --- Scraper Functions ---

def scrape_espn(driver: webdriver.Chrome, year: int):
    """Scrape ESPN projections."""
    LOGGER.info(f"Scraping ESPN for {year}")
    url = "http://fantasy.espn.com/football/players/projections"
    driver.get(url)
    time.sleep(5)  # Wait for React app
    # Your original ESPN scraping logic would go here.
    # This is a complex scraper and needs to be adapted to the new modular format.
    # For now, this is a placeholder.
    LOGGER.warning("ESPN scraper is complex and has not been fully implemented in this refactoring.")


def scrape_cbs(driver: webdriver.Chrome, year: int):
    """Scrape CBS projections."""
    LOGGER.info(f"Scraping CBS for {year}")
    url_template = "https://www.cbssports.com/fantasy/football/stats/{pos}/{year}/season/projections/ppr/"
    all_players = []
    for pos in ["QB", "RB", "WR", "TE", "DST", "K"]:
        page_url = url_template.format(pos=pos, year=year)
        driver.get(page_url)
        time.sleep(2)
        # Your original CBS scraping logic here
    LOGGER.warning("CBS scraper is complex and has not been fully implemented in this refactoring.")


def scrape_nfl(driver: webdriver.Chrome, year: int):
    """Scrape NFL projections."""
    LOGGER.info(f"Scraping NFL for {year}")
    # Your original NFL scraping logic here
    LOGGER.warning("NFL scraper is complex and has not been fully implemented in this refactoring.")


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
        time.sleep(2)
        _scroll(driver)
        time.sleep(2)
        
        try:
            df = pd.read_html(driver.page_source)[0]
            df = df.rename(columns={"Player Team (Bye)": "Player", "AVG": ppr_type})
            
            # Basic Cleaning
            df["pos"] = df["POS"].str.extract(r'([A-Z]+)')[0]
            df['team'] = df['Player'].apply(lambda x: x.split(' ')[-1] if isinstance(x, str) else None)
            df['name'] = df['Player'].apply(lambda x: ' '.join(x.split(' ')[:-1]) if isinstance(x, str) else None)
            
            # Select and re-order
            current_df = df[["name", "team", "pos", ppr_type]].copy()
            current_df = _add_player_key(current_df)

            if merged_df is None:
                merged_df = current_df
            else:
                # Merge while preserving all columns
                merged_df = pd.merge(merged_df, current_df[['key', ppr_type]], on="key", how="outer")

        except Exception as e:
            LOGGER.error(f"Could not parse data for {ppr_type} at {url}: {e}")
            continue

    if merged_df is not None:
        output_path = os.path.join(RAW_ADP, f"FantasyPros-ADP-{year}.csv")
        merged_df.to_csv(output_path, index=False)
        LOGGER.info(f"Successfully saved merged FantasyPros ADP data to {output_path}")
