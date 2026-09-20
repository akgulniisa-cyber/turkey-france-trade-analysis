"""Download the UN Comtrade datasets used by the analysis.

The script fetches, for every year in ``config.YEARS`` and at the 2-digit HS
level:

1. Turkiye exports to France        -> data/raw/turkey_exports_to_france.csv
2. Turkiye exports to the world     -> data/raw/turkey_exports_to_world.csv
3. France imports from the world    -> data/raw/france_imports_from_world.csv
4. Turkiye imports from the world   -> data/raw/turkey_imports_from_world.csv

The fourth flow is used to detect chapters where Turkiye is mainly a
re-exporter or a processor rather than a genuine supplier.

Usage
-----
    python src/download_data.py                 # download every missing year
    python src/download_data.py --force         # re-download everything
    python src/download_data.py --years 2023 2024
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from config import (
    COMMODITY_LEVEL,
    COMTRADE_BASE_URL,
    DATASETS,
    KEEP_COLUMNS,
    MAX_RETRIES,
    PROJECT_ROOT,
    RAW_DIR,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_BACKOFF_SECONDS,
    YEARS,
)

logger = logging.getLogger("download_data")

# Timestamp of the last API call, used to space out consecutive requests.
_last_request_time: float = 0.0


def _throttle() -> None:
    """Sleep so that two consecutive API calls are at least DELAY seconds apart.

    The public preview endpoint does not return an explicit 429 status when it
    is overloaded: it answers 200 with an empty body instead. Spacing the
    requests out is therefore the only reliable way to get complete data.
    """
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    wait = REQUEST_DELAY_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.monotonic()


def fetch_year(reporter: str, partner: str, flow: str, year: int) -> list[dict[str, Any]]:
    """Fetch one (dataset, year) combination from the Comtrade preview endpoint.

    Returns the list of raw records. Raises RuntimeError if the API keeps
    returning an unusable payload after MAX_RETRIES attempts.
    """
    params = {
        "reporterCode": reporter,
        "partnerCode": partner,
        "flowCode": flow,
        "period": str(year),
        "cmdCode": COMMODITY_LEVEL,
        # The three filters below pin the secondary dimensions to their
        # aggregate value, otherwise Comtrade may return the same trade split
        # across several transport modes or customs procedures.
        "partner2Code": "0",
        "customsCode": "C00",
        "motCode": "0",
    }

    last_error = "unknown error"
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        try:
            response = requests.get(
                COMTRADE_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:
            last_error = f"network error: {exc}"
        else:
            if response.status_code != 200:
                last_error = f"HTTP {response.status_code}"
            else:
                try:
                    payload = response.json()
                except ValueError:
                    last_error = "response was not valid JSON"
                else:
                    records = payload.get("data") or []
                    if records:
                        logger.info("      %d records received", len(records))
                        return records
                    # A 200 with no data means we were throttled, or that this
                    # year is genuinely not published yet. Retrying tells the
                    # two cases apart.
                    last_error = "empty payload (throttled or year not published)"

        if attempt < MAX_RETRIES:
            backoff = RETRY_BACKOFF_SECONDS * attempt
            logger.warning(
                "      attempt %d/%d failed (%s), retrying in %.0fs",
                attempt,
                MAX_RETRIES,
                last_error,
                backoff,
            )
            time.sleep(backoff)

    raise RuntimeError(
        f"Could not download reporter={reporter} partner={partner} "
        f"flow={flow} year={year}: {last_error}"
    )


def tidy(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Turn raw Comtrade records into a compact DataFrame with stable columns."""
    frame = pd.DataFrame.from_records(records)
    # Guard against columns the API may omit for a given query.
    for column in KEEP_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame[KEEP_COLUMNS].copy()

    # HS chapter codes must stay strings: "01" is a valid chapter, 1 is not.
    frame["cmdCode"] = frame["cmdCode"].astype(str).str.zfill(2)
    frame["primaryValue"] = pd.to_numeric(frame["primaryValue"], errors="coerce")
    frame["netWgt"] = pd.to_numeric(frame["netWgt"], errors="coerce")
    frame["refYear"] = pd.to_numeric(frame["refYear"], errors="coerce").astype("Int64")
    return frame


def load_existing(path: Path) -> pd.DataFrame | None:
    """Read an already downloaded CSV, or return None if it does not exist."""
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, dtype={"cmdCode": str})
    except (OSError, ValueError) as exc:
        logger.warning("   could not read %s (%s), it will be rebuilt", path.name, exc)
        return None


def download_dataset(
    spec: dict[str, str], years: list[int], force: bool
) -> pd.DataFrame | None:
    """Download every requested year of one dataset and write it to data/raw/."""
    path = RAW_DIR / spec["filename"]
    existing = None if force else load_existing(path)

    already_have: set[int] = set()
    if existing is not None and "refYear" in existing.columns:
        already_have = set(
            pd.to_numeric(existing["refYear"], errors="coerce").dropna().astype(int)
        )

    missing = [year for year in years if year not in already_have]
    logger.info("-> %s", spec["description"])
    if not missing:
        logger.info("   already complete for %s, skipping download", years)
        return existing

    frames = [existing] if existing is not None else []
    for year in missing:
        logger.info("   downloading %d ...", year)
        frames.append(tidy(fetch_year(spec["reporter"], spec["partner"], spec["flow"], year)))

    combined = pd.concat(frames, ignore_index=True)
    # A year could have been downloaded twice across runs; keep the newest row.
    combined = combined.drop_duplicates(subset=["refYear", "cmdCode"], keep="last")
    combined = combined.sort_values(["refYear", "cmdCode"]).reset_index(drop=True)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(path, index=False)
    logger.info("   saved %d rows to %s", len(combined), path.relative_to(PROJECT_ROOT))
    return combined


def summarise(results: dict[str, pd.DataFrame | None]) -> None:
    """Print a short human-readable report of what was downloaded."""
    print("\n" + "=" * 72)
    print("DOWNLOAD SUMMARY")
    print("=" * 72)

    for key, frame in results.items():
        if frame is None or frame.empty:
            print(f"\n{key}: NO DATA")
            continue
        years = sorted(frame["refYear"].dropna().unique().tolist())
        print(f"\n{key}")
        print(f"  rows        : {len(frame)}")
        print(f"  years       : {years}")
        print(f"  HS chapters : {frame['cmdCode'].nunique()}")
        by_year = frame.groupby("refYear")["primaryValue"].sum() / 1e9
        print("  total value per year (billion USD):")
        for year, value in by_year.items():
            print(f"      {year}: {value:12,.1f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download UN Comtrade datasets.")
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=YEARS,
        help="Years to download (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download years that are already present in data/raw/",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Downloading UN Comtrade data for years %s", args.years)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, pd.DataFrame | None] = {}
    failures: list[str] = []
    for key, spec in DATASETS.items():
        try:
            results[key] = download_dataset(spec, args.years, args.force)
        except RuntimeError as exc:
            logger.error("   FAILED: %s", exc)
            failures.append(key)
            results[key] = load_existing(RAW_DIR / spec["filename"])

    summarise(results)

    if failures:
        print(f"\n{len(failures)} dataset(s) incomplete: {', '.join(failures)}")
        print("Re-run the script to retry only the missing years.")
        return 1

    print(f"\nAll {len(DATASETS)} datasets downloaded successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
