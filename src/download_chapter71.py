"""Download the 4-digit breakdown of HS chapter 71 for the four trade flows.

Chapter 71 ("Precious stones and metals") is the one chapter where the 2-digit
figure is misleading: it adds gold bullion, a financial flow, to jewellery, a
manufactured product. This script fetches the same four flows as
``download_data.py`` but for the 18 headings 7101-7118 only, so that
``clean_data.py`` can take the bullion out of the chapter.

Output: data/raw/chapter71_hs4.csv, one row per (flow, year, heading)

Usage
-----
    python src/download_chapter71.py              # download every missing year
    python src/download_chapter71.py --force      # re-download everything
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from config import (
    CHAPTER71_HEADINGS,
    DATASETS,
    DRILLDOWN_FILENAME,
    PROJECT_ROOT,
    RAW_DIR,
    YEARS,
)
from download_data import fetch_year, load_existing, tidy

logger = logging.getLogger("download_chapter71")

HEADING_CODES = ",".join(CHAPTER71_HEADINGS)


def download(years: list[int], force: bool) -> pd.DataFrame:
    """Fetch every missing (dataset, year) pair and write the combined file."""
    path = RAW_DIR / DRILLDOWN_FILENAME
    existing = None if force else load_existing(path)

    already_have: set[tuple[str, int]] = set()
    if existing is not None:
        already_have = set(zip(existing["dataset"], existing["refYear"].astype(int)))

    frames = [existing] if existing is not None else []
    for key, spec in DATASETS.items():
        missing = [year for year in years if (key, year) not in already_have]
        logger.info("-> %s", spec["description"])
        if not missing:
            logger.info("   already complete, skipping download")
            continue
        for year in missing:
            logger.info("   downloading %d ...", year)
            records = fetch_year(
                spec["reporter"], spec["partner"], spec["flow"], year, cmd_code=HEADING_CODES
            )
            frame = tidy(records)
            frame.insert(0, "dataset", key)
            frames.append(frame)

            # Write after every year so that an interrupted run keeps what it
            # has already fetched.
            combined = pd.concat(frames, ignore_index=True)
            combined.to_csv(path, index=False)

    combined = pd.concat(frames, ignore_index=True)
    combined["cmdCode"] = combined["cmdCode"].astype(str)
    combined = combined.drop_duplicates(subset=["dataset", "refYear", "cmdCode"], keep="last")
    combined = combined.sort_values(["dataset", "refYear", "cmdCode"]).reset_index(drop=True)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(path, index=False)
    logger.info("Saved %d rows to %s", len(combined), path.relative_to(PROJECT_ROOT))
    return combined


def summarise(frame: pd.DataFrame) -> None:
    """Print the value of each heading group per flow for the latest year."""
    latest = int(frame["refYear"].max())
    recent = frame[frame["refYear"] == latest].copy()
    recent["group"] = recent["cmdCode"].map(lambda code: CHAPTER71_HEADINGS[code][1])
    table = recent.pivot_table(
        index="group", columns="dataset", values="primaryValue", aggfunc="sum"
    ) / 1e9

    print("\n" + "=" * 72)
    print(f"CHAPTER 71 BY HEADING GROUP, {latest} (billion USD)")
    print("=" * 72)
    print(table.round(2).to_string())


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the 4-digit breakdown of chapter 71.")
    parser.add_argument("--years", type=int, nargs="+", default=YEARS)
    parser.add_argument("--force", action="store_true", help="Re-download every year")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    try:
        frame = download(args.years, args.force)
    except RuntimeError as exc:
        logger.error("FAILED: %s", exc)
        print("Re-run the script to retry only the missing years.")
        return 1

    summarise(frame)
    return 0


if __name__ == "__main__":
    sys.exit(main())
