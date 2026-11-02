"""Transparent sample statistics; missing observations are never imputed."""

import numpy as np
import pandas as pd

from analytics import price_rows

BUDGET_LABELS = ["$0", "$0–10", "$10–20", "$20–40", "$40–60", "$60+"]


def primary_genres(frame):
    """Steam's saved deduplication assignment, not a popularity estimate."""
    values = frame["primary_category"].fillna("Naməlum")
    return values.value_counts().rename_axis("categories").reset_index(name="games")


def budget_distribution(frame):
    known = price_rows(frame).copy()
    bands = pd.cut(
        known["price"], [-0.01, 0, 10, 20, 40, 60, np.inf], labels=BUDGET_LABELS
    )
    counts = bands.value_counts(sort=False).reindex(BUDGET_LABELS, fill_value=0)
    result = pd.DataFrame({"budget": BUDGET_LABELS, "games": counts.to_numpy()})
    result["share"] = result["games"] * 100 / len(known) if len(known) else np.nan
    result["denominator"] = len(known)
    return result


def genre_overlap(frame, labels):
    groups = {
        label: set(frame.loc[frame["categories"].map(lambda x: label in x), "id"])
        for label in labels
    }
    counts = pd.DataFrame(0, index=labels, columns=labels, dtype=int)
    similarity = pd.DataFrame(np.nan, index=labels, columns=labels)
    for left in labels:
        for right in labels:
            union = groups[left] | groups[right]
            counts.loc[left, right] = len(groups[left] & groups[right])
            if union:
                similarity.loc[left, right] = 100 * counts.loc[left, right] / len(union)
    return counts, similarity


def ranked_games(frame, minimum_votes=100, strength=200):
    """Shrink small-sample ratings toward the platform's observed mean."""
    rated = frame[frame["rating_eligible"] & frame["votes"].gt(0)].copy()
    prior = rated["rating"].mean()
    result = rated[rated["votes"].ge(minimum_votes)].copy()
    result["weighted_rating"] = (
        result["votes"] * result["rating"] + strength * prior
    ) / (result["votes"] + strength)
    return result.sort_values(
        ["weighted_rating", "votes", "id"], ascending=[False, False, True]
    )


def year_profile(frame):
    valid = frame[frame["year"].notna()].copy()
    if valid.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "games",
                "median_price",
                "price_n",
                "median_rating",
                "rating_n",
            ]
        )
    counts = valid.groupby("year")["id"].nunique().rename("games")
    prices = (
        price_rows(valid, paid_only=True)
        .groupby("year")["price"]
        .agg(median_price="median", price_n="count")
    )
    ratings = (
        valid[valid["rating_eligible"]]
        .groupby("year")["rating"]
        .agg(median_rating="median", rating_n="count")
    )
    result = counts.to_frame().join(prices).join(ratings).reset_index()
    result[["price_n", "rating_n"]] = (
        result[["price_n", "rating_n"]].fillna(0).astype(int)
    )
    result["year"] = result["year"].astype(int)
    return result


def support_profile(frame, platform):
    if platform == "steam":
        rows = []
        for label, column in (
            ("Windows", "is_windows"),
            ("macOS", "is_mac"),
            ("Linux", "is_linux"),
            ("VR", "is_vr"),
        ):
            rows.extend(
                [
                    {
                        "support": label,
                        "status": "Bəli",
                        "games": int(frame[column].eq(True).sum()),
                    },
                    {
                        "support": label,
                        "status": "Xeyr",
                        "games": int(frame[column].eq(False).sum()),
                    },
                    {
                        "support": label,
                        "status": "Naməlum",
                        "games": int(frame[column].isna().sum()),
                    },
                ]
            )
        return pd.DataFrame(rows)
    values = frame["platforms"].map(
        lambda x: " + ".join(sorted(set(x))) if x else "Naməlum"
    )
    return values.value_counts().rename_axis("support").reset_index(name="games")


def basket_summary(frame):
    unique = frame.drop_duplicates("id")
    known = price_rows(unique)
    return {
        "games": len(unique),
        "priced": len(known),
        "unknown": len(unique) - len(known),
        "observed_total": float(known["price"].sum()) if len(known) else None,
    }


def discount_summary(frame):
    known = price_rows(frame)
    basis = known[known["original_price"].gt(0) & known["discount"].notna()]
    discounted = basis[basis["discount"].gt(0)]
    return {
        "basis": len(basis),
        "discounted": len(discounted),
        "share": 100 * len(discounted) / len(basis) if len(basis) else None,
        "median": float(discounted["discount"].median()) if len(discounted) else None,
    }
