"""Clean the raw Comtrade downloads and build a single analysis panel.

The three raw files each describe one trade flow. This script reshapes them
into one tidy table with a single row per (HS chapter, year), attaches English
product names, derives the share variables the opportunity score needs, and
runs a set of data-quality checks.

Output: data/processed/trade_panel.csv

Usage
-----
    python src/clean_data.py
"""

from __future__ import annotations

import logging
import sys

import numpy as np
import pandas as pd

from config import DATASETS, PROCESSED_DIR, PROJECT_ROOT, RAW_DIR, YEARS
from hs_chapters import chapters_frame

logger = logging.getLogger("clean_data")

# Raw dataset key -> column name in the panel.
VALUE_COLUMNS = {
    "turkey_exports_to_france": "tr_to_france_usd",
    "turkey_exports_to_world": "tr_to_world_usd",
    "france_imports_from_world": "fr_from_world_usd",
}


def load_raw(key: str) -> pd.DataFrame:
    """Load one raw file and reduce it to (hs_code, year, value)."""
    path = RAW_DIR / DATASETS[key]["filename"]
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. Run 'python src/download_data.py' first."
        )

    frame = pd.read_csv(path, dtype={"cmdCode": str})
    frame = frame.rename(
        columns={"cmdCode": "hs_code", "refYear": "year", "primaryValue": VALUE_COLUMNS[key]}
    )
    frame = frame[["hs_code", "year", VALUE_COLUMNS[key]]].copy()

    # Codes must keep their leading zero to merge correctly with the reference.
    frame["hs_code"] = frame["hs_code"].str.zfill(2)
    frame["year"] = frame["year"].astype(int)

    # Comtrade occasionally reports the same chapter twice for one year when a
    # flow is split internally; summing is the correct aggregation here.
    duplicates = frame.duplicated(subset=["hs_code", "year"]).sum()
    if duplicates:
        logger.warning("   %s: %d duplicate chapter-year rows summed", key, duplicates)
        frame = frame.groupby(["hs_code", "year"], as_index=False).sum()

    logger.info("   %-28s %4d rows", key, len(frame))
    return frame


def safe_share(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Percentage share that returns NaN instead of inf when the base is zero."""
    denominator = denominator.replace(0, np.nan)
    return (numerator / denominator) * 100.0


def build_panel() -> pd.DataFrame:
    """Merge the three flows, add product names and derive share variables."""
    logger.info("Loading raw files:")
    panel = None
    for key in VALUE_COLUMNS:
        frame = load_raw(key)
        panel = frame if panel is None else panel.merge(frame, on=["hs_code", "year"], how="outer")

    # A chapter absent from a file means no trade was reported, i.e. zero.
    for column in VALUE_COLUMNS.values():
        panel[column] = panel[column].fillna(0.0)

    logger.info("Attaching HS chapter names")
    reference = chapters_frame()
    panel = reference.merge(panel, on="hs_code", how="right")

    unknown = panel[panel["hs_name"].isna()]["hs_code"].unique()
    if len(unknown):
        logger.warning("   %d HS codes have no English name: %s", len(unknown), list(unknown))

    logger.info("Deriving share variables")
    # How much of the French market Turkiye already holds in this chapter.
    panel["tr_share_in_france_pct"] = safe_share(
        panel["tr_to_france_usd"], panel["fr_from_world_usd"]
    )
    # How much of Turkiye's exports in this chapter already go to France.
    panel["france_share_of_tr_exports_pct"] = safe_share(
        panel["tr_to_france_usd"], panel["tr_to_world_usd"]
    )

    # Weight of the chapter within each country's yearly total. These say how
    # important a product is for Turkish supply and for French demand.
    yearly_tr = panel.groupby("year")["tr_to_world_usd"].transform("sum")
    yearly_fr = panel.groupby("year")["fr_from_world_usd"].transform("sum")
    panel["tr_export_weight_pct"] = safe_share(panel["tr_to_world_usd"], yearly_tr)
    panel["fr_import_weight_pct"] = safe_share(panel["fr_from_world_usd"], yearly_fr)

    panel = panel.sort_values(["hs_code", "year"]).reset_index(drop=True)
    return panel


def validate(panel: pd.DataFrame) -> list[str]:
    """Run data-quality checks and return a list of problems found."""
    problems: list[str] = []

    expected_rows = panel["hs_code"].nunique() * len(YEARS)
    if len(panel) != expected_rows:
        problems.append(f"expected {expected_rows} rows, found {len(panel)}")

    missing_years = set(YEARS) - set(panel["year"].unique())
    if missing_years:
        problems.append(f"missing years: {sorted(missing_years)}")

    # Every chapter should be observed in every year.
    counts = panel.groupby("hs_code")["year"].nunique()
    incomplete = counts[counts != len(YEARS)]
    if len(incomplete):
        problems.append(f"{len(incomplete)} chapters do not cover all {len(YEARS)} years")

    for column in VALUE_COLUMNS.values():
        negatives = (panel[column] < 0).sum()
        if negatives:
            problems.append(f"{column}: {negatives} negative values")

    # Exports to France are a subset of exports to the world. A small tolerance
    # absorbs rounding in the reported figures.
    inconsistent = panel[panel["tr_to_france_usd"] > panel["tr_to_world_usd"] * 1.001]
    if len(inconsistent):
        problems.append(f"{len(inconsistent)} rows where TR->France exceeds TR->World")

    if panel["hs_name"].isna().any():
        problems.append(f"{panel['hs_name'].isna().sum()} rows without a product name")

    return problems


def report(panel: pd.DataFrame) -> None:
    """Print a readable summary of the cleaned panel."""
    print("\n" + "=" * 78)
    print("CLEANED PANEL")
    print("=" * 78)
    print(f"rows          : {len(panel)}")
    print(f"HS chapters   : {panel['hs_code'].nunique()}")
    print(f"years         : {sorted(panel['year'].unique().tolist())}")
    print(f"HS sections   : {panel['hs_section'].nunique()}")
    print(f"columns       : {len(panel.columns)}")

    latest = panel["year"].max()
    recent = panel[(panel["year"] == latest) & (~panel["is_special"])]

    print(f"\nTop 10 Turkish exports to France, {latest}")
    print("-" * 78)
    top = recent.nlargest(10, "tr_to_france_usd")
    print(
        f"{'HS':>3}  {'Product':<32}{'TR->FR':>10}{'FR imports':>12}{'TR share':>10}"
    )
    for _, row in top.iterrows():
        print(
            f"{row['hs_code']:>3}  {row['hs_short_name'][:31]:<32}"
            f"{row['tr_to_france_usd'] / 1e9:>9.2f}B"
            f"{row['fr_from_world_usd'] / 1e9:>11.1f}B"
            f"{row['tr_share_in_france_pct']:>9.1f}%"
        )

    print(f"\nLargest French import markets where Turkiye is weakest, {latest}")
    print("(big French demand, Turkish share below 1%)")
    print("-" * 78)
    weak = recent[recent["tr_share_in_france_pct"] < 1.0].nlargest(10, "fr_from_world_usd")
    print(
        f"{'HS':>3}  {'Product':<32}{'FR imports':>12}{'TR share':>10}{'TR->World':>12}"
    )
    for _, row in weak.iterrows():
        print(
            f"{row['hs_code']:>3}  {row['hs_short_name'][:31]:<32}"
            f"{row['fr_from_world_usd'] / 1e9:>11.1f}B"
            f"{row['tr_share_in_france_pct']:>9.2f}%"
            f"{row['tr_to_world_usd'] / 1e9:>11.1f}B"
        )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        panel = build_panel()
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1

    problems = validate(panel)
    if problems:
        logger.warning("Data-quality checks reported %d problem(s):", len(problems))
        for problem in problems:
            logger.warning("   - %s", problem)
    else:
        logger.info("All data-quality checks passed")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output = PROCESSED_DIR / "trade_panel.csv"
    panel.to_csv(output, index=False)
    logger.info("Saved panel to %s", output.relative_to(PROJECT_ROOT))

    # Read the file back and compare null counts. Some perfectly ordinary
    # strings (for example "NA") are treated as missing values when pandas
    # parses a CSV, which would silently corrupt a column that looked fine in
    # memory.
    reloaded = pd.read_csv(output, dtype={"hs_code": str})
    introduced = reloaded.isna().sum() - panel.isna().sum()
    corrupted = introduced[introduced > 0]
    if len(corrupted):
        logger.error("Round-trip check failed, columns gained nulls when re-read:")
        for column, count in corrupted.items():
            logger.error("   - %s: +%d nulls", column, count)
        return 1
    logger.info("Round-trip check passed (%d rows re-read cleanly)", len(reloaded))

    report(panel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
