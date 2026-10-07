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
    # Turkiye's own imports are not part of the opportunity story directly, but
    # they reveal which chapters are dominated by re-export and processing
    # rather than by domestic production. Gold (chapter 71) and refined fuels
    # (chapter 27) are the textbook cases: large export figures that rest on
    # equally large imports of the same goods.
    "turkey_imports_from_world": {
        "reporter": TURKIYE_CODE,
        "partner": WORLD_CODE,
        "flow": "M",
        "filename": "turkey_imports_from_world.csv",
        "description": "Turkiye's imports from the whole world, by HS chapter",
    },
}

# --------------------------------------------------------------------------
# Chapter 71 drill-down
# --------------------------------------------------------------------------
# At 2-digit level chapter 71 mixes two very different businesses: gold and
# silver bullion, whose flows follow metal prices and investor demand, and
# jewellery, which Turkiye genuinely manufactures. The same four flows are
# therefore downloaded at 4-digit level for this chapter only, and the bullion
# headings are taken out of the chapter before it is scored.
DRILLDOWN_CHAPTER = "71"
DRILLDOWN_FILENAME = "chapter71_hs4.csv"

# Heading -> (short name, group). The groups are what the score and the
# dashboard work with; the headings are kept for reference.
CHAPTER71_HEADINGS: dict[str, tuple[str, str]] = {
    "7101": ("Pearls", "stones"),
    "7102": ("Diamonds", "stones"),
    "7103": ("Precious and semi-precious stones", "stones"),
    "7104": ("Synthetic stones", "stones"),
    "7105": ("Stone dust and powder", "stones"),
    "7106": ("Silver, unwrought or semi-manufactured", "bullion"),
    "7107": ("Base metal clad with silver", "bullion"),
    "7108": ("Gold, unwrought or semi-manufactured", "bullion"),
    "7109": ("Base metal clad with gold", "bullion"),
    "7110": ("Platinum, unwrought or semi-manufactured", "bullion"),
    "7111": ("Base metal clad with platinum", "bullion"),
    "7112": ("Precious metal waste and scrap", "bullion"),
    "7113": ("Jewellery of precious metal", "jewellery"),
    "7114": ("Goldsmiths' and silversmiths' wares", "jewellery"),
    "7115": ("Other articles of precious metal", "jewellery"),
    "7116": ("Articles of pearls and stones", "jewellery"),
    "7117": ("Imitation jewellery", "jewellery"),
    "7118": ("Coin", "bullion"),
}

CHAPTER71_GROUP_NAMES = {
    "stones": "Pearls and precious stones",
    "bullion": "Bullion, coin and scrap",
    "jewellery": "Jewellery and articles",
}

# Groups removed from chapter 71 before scoring. Bullion is a store of value,
# not a product an exporter competes on, so it cannot be an export
# opportunity in the sense this project uses.
CHAPTER71_EXCLUDED_GROUPS = {"bullion"}

# --------------------------------------------------------------------------
# Opportunity score
# --------------------------------------------------------------------------
# The opportunity of a chapter is the gap between what Turkiye could
# realistically sell to France and what it sells today. The ceiling is the
# smaller of two limits, because a trade flow cannot exceed either side of it:
#
#   demand ceiling = French market size  x  an attainable market share
#   supply ceiling = Turkish capacity    x  an attainable redirection to France
#
# Taking the minimum is what stops the ranking being dominated by huge French
# markets that Turkiye has no capacity to serve, such as pharmaceuticals.

# The score is computed on the average of the last N years rather than on a
# single year, so that one unusual year does not drive the ranking.
SCORE_BASIS_YEARS = 3

# Attainable market share, read off the distribution of the shares Turkiye
# already holds in France. The 90th percentile is about 4%, which is what it
# achieves in the chapters where it is well established.
SATURATION_PERCENTILE = 0.90

# Attainable redirection, read off the distribution of how much of Turkiye's
# exports in a chapter already go to France. The 95th percentile is about 9%,
# against an average of 3.9% across all goods, so it represents an ambitious
# but observed level of integration rather than an arbitrary target.
REDIRECT_PERCENTILE = 0.95

# Chapters below this net-export ratio are reported with a warning. They are
# not removed from the ranking, because the supply-quality discount already
# reduces their score; the flag exists so the dashboard can mark them.
NET_EXPORT_CONFIDENCE_THRESHOLD = -0.25

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
