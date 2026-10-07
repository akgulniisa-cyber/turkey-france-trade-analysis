"""Rank HS chapters by Turkiye's untapped export potential in France.

The score answers one question: in which products does France buy a lot, can
Turkiye genuinely supply a lot, and is Turkiye still selling little to France?

Method
------
For each chapter the model estimates a realistic ceiling on Turkish exports to
France, then subtracts what is already sold. The ceiling is the *smaller* of
two limits, because a trade flow cannot exceed either side of it:

    demand ceiling = French imports from the world x attainable market share
    supply ceiling = Turkish effective supply      x attainable redirection

    untapped value = max(min(demand ceiling, supply ceiling) - current, 0)

Taking the minimum is the heart of the method. An additive score would let a
huge French market compensate for the absence of Turkish supply, which is why
an earlier version of this model ranked pharmaceuticals and mineral fuels at
the top: France buys enormous amounts of both, and Turkiye sells almost none,
but it has no capacity to fill either gap. The minimum makes those chapters
score near zero, and it also correctly empties chapters such as knitted apparel
where Turkiye is already at the ceiling.

Three inputs drive the result, matching the three questions the project asks:
French demand sets the demand ceiling, Turkish export strength sets the supply
ceiling, and Turkiye's current sales to France are what gets subtracted.

The supply-quality discount
---------------------------
Gross exports overstate what a country can really supply whenever it imports
the same goods it sells on. Turkiye's gold figures (chapter 71) are largely
bullion passing through Istanbul, and its fuel figures (chapter 27) are refined
product made from imported crude. Rather than hardcoding a list of suspect
products, the supply side is multiplied by a quality factor derived from the
net-export ratio, so every chapter is discounted in proportion to how much of
its export value is really re-export or processing.

Output: data/processed/opportunity_scores.csv

Usage
-----
    python src/opportunity_score.py
    python src/opportunity_score.py --top 25
"""

from __future__ import annotations

import argparse
import logging
import sys

import numpy as np
import pandas as pd

from config import (
    NET_EXPORT_CONFIDENCE_THRESHOLD,
    PROCESSED_DIR,
    PROJECT_ROOT,
    REDIRECT_PERCENTILE,
    SATURATION_PERCENTILE,
    SCORE_BASIS_YEARS,
)

logger = logging.getLogger("opportunity_score")


def load_panel() -> pd.DataFrame:
    """Load the cleaned panel produced by clean_data.py."""
    path = PROCESSED_DIR / "trade_panel.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing. Run 'python src/clean_data.py' first.")
    return pd.read_csv(path, dtype={"hs_code": str})


def recent_average(panel: pd.DataFrame, n_years: int) -> pd.DataFrame:
    """Average each chapter over the most recent n_years.

    Single-year trade figures are noisy: a delayed shipment or a swing in
    commodity prices can move a chapter sharply. Averaging the last few years
    gives a more stable picture of the underlying trade relationship.
    """
    years = sorted(int(year) for year in panel["year"].unique())[-n_years:]
    logger.info("Scoring on the average of %s", years)

    window = panel[panel["year"].isin(years)]
    # Chapter 99 collects confidential and unallocated trade. It is not a
    # product, so it cannot be an export opportunity.
    window = window[~window["is_special"]]

    value_columns = [
        "tr_to_france_usd",
        "tr_to_world_usd",
        "fr_from_world_usd",
        "tr_from_world_usd",
    ]
    keys = ["hs_code", "hs_short_name", "hs_name", "hs_section", "hs_section_name"]
    averaged = window.groupby(keys, as_index=False)[value_columns].mean()

    # Recompute the shares from the averaged values rather than averaging the
    # yearly shares, which would give small years the same weight as large ones.
    averaged["tr_share_in_france_pct"] = (
        averaged["tr_to_france_usd"] / averaged["fr_from_world_usd"].replace(0, np.nan)
    ) * 100
    averaged["france_share_of_tr_exports_pct"] = (
        averaged["tr_to_france_usd"] / averaged["tr_to_world_usd"].replace(0, np.nan)
    ) * 100
    total_trade = averaged["tr_to_world_usd"] + averaged["tr_from_world_usd"]
    averaged["tr_net_export_ratio"] = (
        averaged["tr_to_world_usd"] - averaged["tr_from_world_usd"]
    ) / total_trade.replace(0, np.nan)

    averaged["basis_years"] = ", ".join(str(year) for year in years)
    return averaged


def normalise_log(values: pd.Series) -> pd.Series:
    """Rescale positive values to 0-100 on a logarithmic scale.

    Trade values span six orders of magnitude, from a few million dollars to
    ninety billion. Without a log transform any ranking would be decided
    entirely by the handful of largest chapters.
    """
    logged = np.log10(values.clip(lower=0) + 1.0)
    span = logged.max() - logged.min()
    if span == 0:
        return pd.Series(50.0, index=values.index)
    return (logged - logged.min()) / span * 100.0


def compute_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Estimate the realistic ceiling, the untapped value and the score."""
    scored = frame.copy()

    # --- supply quality -----------------------------------------------------
    # Map the net-export ratio from [-1, +1] onto [0, 1]. A chapter Turkiye
    # only exports keeps almost all of its value; one it imports as much as it
    # exports keeps about half; one it mostly imports keeps very little.
    scored["supply_quality"] = ((scored["tr_net_export_ratio"] + 1.0) / 2.0).clip(0.0, 1.0)
    scored["supply_quality"] = scored["supply_quality"].fillna(0.5)
    scored["effective_supply_usd"] = scored["tr_to_world_usd"] * scored["supply_quality"]

    # --- the two ceilings ---------------------------------------------------
    saturation_share = scored["tr_share_in_france_pct"].quantile(SATURATION_PERCENTILE)
    redirect_share = scored["france_share_of_tr_exports_pct"].quantile(REDIRECT_PERCENTILE)
    logger.info(
        "Attainable market share (p%d): %.2f%% of the French market",
        int(SATURATION_PERCENTILE * 100),
        saturation_share,
    )
    logger.info(
        "Attainable redirection (p%d): %.2f%% of Turkish exports in a chapter",
        int(REDIRECT_PERCENTILE * 100),
        redirect_share,
    )

    scored["demand_ceiling_usd"] = scored["fr_from_world_usd"] * saturation_share / 100.0
    scored["supply_ceiling_usd"] = scored["effective_supply_usd"] * redirect_share / 100.0
    scored["potential_usd"] = np.minimum(
        scored["demand_ceiling_usd"], scored["supply_ceiling_usd"]
    )
    scored["binding_constraint"] = np.where(
        scored["demand_ceiling_usd"] < scored["supply_ceiling_usd"], "demand", "supply"
    )

    # --- the headline numbers ----------------------------------------------
    scored["untapped_value_usd"] = (
        scored["potential_usd"] - scored["tr_to_france_usd"]
    ).clip(lower=0.0)

    # The score is the untapped value rescaled so that the best chapter sits at
    # 100. Scaling linearly rather than logarithmically keeps the score
    # proportional to the prize: a chapter scoring 50 really is worth half of
    # the top one, which a log scale would hide by squeezing every ranked
    # chapter into the 90-100 band.
    best = scored["untapped_value_usd"].max()
    scored["opportunity_score"] = (
        scored["untapped_value_usd"] / best * 100.0 if best > 0 else 0.0
    )

    # --- diagnostics kept for the dashboard --------------------------------
    # These explain *why* a chapter scores as it does, but they are not the
    # score itself.
    scored["demand_score"] = normalise_log(scored["fr_from_world_usd"])
    scored["supply_score"] = normalise_log(scored["effective_supply_usd"])
    penetration = (
        scored["tr_share_in_france_pct"].fillna(0.0) / saturation_share
    ).clip(0.0, 1.0)
    scored["gap_score"] = (1.0 - penetration) * 100.0

    # Revealed comparative advantage: is Turkiye more specialised in this
    # product than the structure of French demand would suggest? Above 1 means
    # yes. France's import mix stands in for the world market here, which is a
    # fair proxy because France is a large and diversified importer.
    turkish_weight = scored["effective_supply_usd"] / scored["effective_supply_usd"].sum()
    french_weight = scored["fr_from_world_usd"] / scored["fr_from_world_usd"].sum()
    scored["rca"] = turkish_weight / french_weight.replace(0, np.nan)

    scored["low_supply_confidence"] = (
        scored["tr_net_export_ratio"] < NET_EXPORT_CONFIDENCE_THRESHOLD
    )

    scored = scored.sort_values("untapped_value_usd", ascending=False).reset_index(drop=True)
    scored.insert(0, "rank", range(1, len(scored) + 1))
    return scored


def report(scored: pd.DataFrame, top: int) -> None:
    """Print the ranking and the diagnostics that explain it."""
    basis = scored["basis_years"].iloc[0]
    print("\n" + "=" * 104)
    print(f"OPPORTUNITY RANKING - Turkish export potential in France (basis: {basis})")
    print("=" * 104)
    print(
        f"{'#':>3} {'HS':>3} {'Product':<30}  {'Score':>6}{'Untapped':>10}"
        f"{'Current':>9}{'Ceiling':>9}{'Limit':>8}{'FR mkt':>9}{'Share':>7}{'RCA':>6}"
    )
    print("-" * 104)
    for _, row in scored.head(top).iterrows():
        warning = "!" if row["low_supply_confidence"] else " "
        print(
            f"{row['rank']:>3} {row['hs_code']:>3} {row['hs_short_name'][:29]:<30}{warning} "
            f"{row['opportunity_score']:>6.1f}"
            f"{row['untapped_value_usd'] / 1e9:>9.2f}B"
            f"{row['tr_to_france_usd'] / 1e9:>8.2f}B"
            f"{row['potential_usd'] / 1e9:>8.2f}B"
            f"{row['binding_constraint']:>8}"
            f"{row['fr_from_world_usd'] / 1e9:>8.1f}B"
            f"{row['tr_share_in_france_pct']:>6.2f}%"
            f"{row['rca']:>6.2f}"
        )
    print("-" * 104)
    print("! = Turkiye is a net importer of this product, so its export figure")
    print("    partly reflects re-export or processing rather than own production.")
    print("Limit = which side binds: 'demand' means France's market is the")
    print("    constraint, 'supply' means Turkish capacity is.")

    total = scored["untapped_value_usd"].sum()
    print(f"\nTotal untapped value: ${total / 1e9:.1f}B")
    print(
        f"Top 10 account for ${scored.head(10)['untapped_value_usd'].sum() / 1e9:.1f}B "
        f"({scored.head(10)['untapped_value_usd'].sum() / total * 100:.0f}%)"
    )
    counts = scored["binding_constraint"].value_counts()
    print(
        f"Binding constraint: supply in {counts.get('supply', 0)} chapters, "
        f"demand in {counts.get('demand', 0)}"
    )

    print("\nSanity check - chapters the method should NOT rank highly")
    print("-" * 104)
    checks = {
        "27": "huge French market, but Turkiye refines imported crude",
        "30": "huge French market, Turkiye has almost no pharma industry",
        "90": "large French market, little Turkish capacity",
        "61": "Turkiye is strong, but already at its ceiling in France",
        "87": "Turkiye is strong, but already at its ceiling in France",
    }
    for code, reason in checks.items():
        match = scored[scored["hs_code"] == code]
        if match.empty:
            continue
        row = match.iloc[0]
        print(
            f"  {code} {row['hs_short_name'][:28]:<30} rank {row['rank']:>3}   "
            f"untapped ${row['untapped_value_usd'] / 1e9:.2f}B   {reason}"
        )

    print("\nEffect of the supply-quality discount")
    print("-" * 104)
    print(f"{'HS':>3}  {'Product':<30}{'Gross':>10}{'Quality':>9}{'Effective':>11}{'Rank':>6}")
    for code in ["27", "71", "72", "87", "61", "84"]:
        match = scored[scored["hs_code"] == code]
        if match.empty:
            continue
        row = match.iloc[0]
        print(
            f"{row['hs_code']:>3}  {row['hs_short_name'][:28]:<30}"
            f"{row['tr_to_world_usd'] / 1e9:>9.1f}B"
            f"{row['supply_quality']:>9.2f}"
            f"{row['effective_supply_usd'] / 1e9:>10.1f}B"
            f"{row['rank']:>6}"
        )


def report_chapter71(years: list[int]) -> None:
    """Show what chapter 71 is made of, and what the bullion exclusion removed."""
    path = PROCESSED_DIR / "chapter71_groups.csv"
    if not path.exists():
        return
    groups = pd.read_csv(path)
    groups = groups[groups["year"].isin(years)]
    averaged = groups.groupby(["group", "group_name", "excluded"], as_index=False)[
        ["tr_to_world_usd", "tr_from_world_usd", "tr_to_france_usd", "fr_from_world_usd"]
    ].mean()
    total_trade = averaged["tr_to_world_usd"] + averaged["tr_from_world_usd"]
    averaged["net_ratio"] = (
        averaged["tr_to_world_usd"] - averaged["tr_from_world_usd"]
    ) / total_trade.replace(0, np.nan)

    print("\nChapter 71 by heading group (bullion is excluded from the score)")
    print("-" * 104)
    print(
        f"{'Group':<30}{'TR exports':>12}{'TR imports':>12}{'Net ratio':>11}"
        f"{'TR->FR':>9}{'FR imports':>12}  {'In score':>8}"
    )
    for _, row in averaged.sort_values("tr_to_world_usd", ascending=False).iterrows():
        print(
            f"{row['group_name']:<30}"
            f"{row['tr_to_world_usd'] / 1e9:>11.2f}B"
            f"{row['tr_from_world_usd'] / 1e9:>11.2f}B"
            f"{row['net_ratio']:>11.2f}"
            f"{row['tr_to_france_usd'] / 1e9:>8.2f}B"
            f"{row['fr_from_world_usd'] / 1e9:>11.2f}B"
            f"  {'no' if row['excluded'] else 'yes':>8}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank HS chapters by export opportunity.")
    parser.add_argument(
        "--top", type=int, default=20, help="How many chapters to print (default: %(default)s)"
    )
    parser.add_argument(
        "--years",
        type=int,
        default=SCORE_BASIS_YEARS,
        help="Number of recent years to average (default: %(default)s)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        panel = load_panel()
    except FileNotFoundError as exc:
        logger.error(str(exc))
        return 1

    scored = compute_scores(recent_average(panel, args.years))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output = PROCESSED_DIR / "opportunity_scores.csv"
    scored.to_csv(output, index=False)
    logger.info("Saved %d scored chapters to %s", len(scored), output.relative_to(PROJECT_ROOT))

    report(scored, args.top)
    report_chapter71([int(year) for year in scored["basis_years"].iloc[0].split(", ")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
