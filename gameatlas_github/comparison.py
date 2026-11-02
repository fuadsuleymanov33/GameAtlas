"""Conservative pair candidates and explicit, observation-based price math."""

import math

import pandas as pd


def exact_candidates(steam, ps):
    """One-to-one title keys are candidates, never certified game/edition matches."""
    left = steam[
        steam["title_key"].map(lambda key: isinstance(key, str) and bool(key.strip()))
    ]
    right = ps[
        ps["title_key"].map(lambda key: isinstance(key, str) and bool(key.strip()))
    ]
    left = left[~left["title_key"].duplicated(keep=False)]
    right = right[~right["title_key"].duplicated(keep=False)]
    result = left[["id", "title", "title_key"]].merge(
        right[["id", "title", "title_key"]],
        on="title_key",
        suffixes=("_steam", "_ps"),
        validate="one_to_one",
    )
    return result.sort_values("title_steam").reset_index(drop=True)


def price_comparison(steam_row, ps_row):
    """Only known same-currency values. Semantic pairing is the caller's decision."""
    for row in (steam_row, ps_row):
        value = row["price"]
        if (
            not row["price_eligible"]
            or row["currency"] != "USD"
            or pd.isna(value)
            or not math.isfinite(value)
            or value < 0
        ):
            return None
    steam_price, ps_price = float(steam_row["price"]), float(ps_row["price"])
    difference = round(ps_price - steam_price, 2)
    return {
        "steam_price": steam_price,
        "ps_price": ps_price,
        "difference_usd": difference,
        "ps_relative_to_steam_pct": round(100 * difference / steam_price, 2)
        if steam_price > 0
        else None,
        "cheaper": "Steam"
        if difference > 0
        else "PS Store"
        if difference < 0
        else "Bərabər",
        "saving_usd": abs(difference),
    }
