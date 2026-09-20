"""Central configuration for the Turkey-France trade opportunity project.

All constants that describe *what* we download and *where* we store it live
here, so that the download, cleaning, scoring and dashboard scripts all agree
on the same definitions.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Project paths
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# --------------------------------------------------------------------------
# UN Comtrade API
# --------------------------------------------------------------------------
# The "preview" endpoint of the UN Comtrade v1 API is public: it needs no
# subscription key, but it returns at most 500 rows per request and it
# throttles clients that send requests too quickly.  Because one year of
# 2-digit HS data is only ~97 rows, we stay far below the row limit by
# requesting one year at a time.
COMTRADE_BASE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

# Seconds to wait between two consecutive API calls.  The public endpoint
# silently returns an empty payload when it is hit too fast, so we are
# deliberately conservative here.
REQUEST_DELAY_SECONDS = 6.0

# How many times a single year/dataset request is retried before giving up.
MAX_RETRIES = 4

# Base delay for the exponential backoff applied after a failed request.
RETRY_BACKOFF_SECONDS = 10.0

# Timeout (seconds) for a single HTTP request.
REQUEST_TIMEOUT_SECONDS = 90

# --------------------------------------------------------------------------
# Analysis scope
# --------------------------------------------------------------------------
# UN Comtrade M49 country codes.
TURKIYE_CODE = "792"
FRANCE_CODE = "251"
WORLD_CODE = "0"

# Years covered by the study.
YEARS = [2020, 2021, 2022, 2023, 2024]

# "AG2" asks Comtrade to aggregate the commodity dimension at the 2-digit
# HS level, i.e. the 97 HS chapters.
COMMODITY_LEVEL = "AG2"

# --------------------------------------------------------------------------
# The three datasets the analysis is built on
# --------------------------------------------------------------------------
# Each entry describes one Comtrade query:
#   reporter  - the country that reports the trade flow
#   partner   - the counterpart country ("0" means the rest of the world)
#   flow      - "X" for exports, "M" for imports
#   filename  - name of the CSV written into data/raw/
DATASETS = {
    "turkey_exports_to_france": {
        "reporter": TURKIYE_CODE,
        "partner": FRANCE_CODE,
        "flow": "X",
        "filename": "turkey_exports_to_france.csv",
        "description": "Turkiye's exports to France, by HS chapter",
    },
    "turkey_exports_to_world": {
        "reporter": TURKIYE_CODE,
        "partner": WORLD_CODE,
        "flow": "X",
        "filename": "turkey_exports_to_world.csv",
        "description": "Turkiye's exports to the whole world, by HS chapter",
    },
    "france_imports_from_world": {
        "reporter": FRANCE_CODE,
        "partner": WORLD_CODE,
        "flow": "M",
        "filename": "france_imports_from_world.csv",
        "description": "France's imports from the whole world, by HS chapter",
    },
}

# Columns kept from the raw Comtrade payload.  The API returns ~45 columns,
# most of which are empty for aggregated 2-digit data.
KEEP_COLUMNS = [
    "refYear",
    "reporterCode",
    "partnerCode",
    "flowCode",
    "cmdCode",
    "primaryValue",
    "netWgt",
    "classificationCode",
]
