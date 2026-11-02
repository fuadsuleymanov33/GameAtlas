"""Read-only analytics of separately verified Steam and PS datasets."""

import hashlib
import json
from pathlib import Path

import pandas as pd

DEFAULT_PROJECT = Path(__file__).resolve().parent
PLATFORMS = {
    "steam": {
        "name": "Steam",
        "region": "AZ",
        "color": "#13866d",
        "rating": "Müsbət rəy faizi",
        "scale": 100,
    },
    "playstation": {
        "name": "PS Store",
        "region": "US",
        "color": "#2864dc",
        "rating": "Reytinq (5 üzərindən)",
        "scale": 5,
    },
}


def paths(platform, project=DEFAULT_PROJECT):
    folder = project / (
        "steam/data/clean" if platform == "steam" else "playstation/bulk/data/clean"
    )
    return folder / "games_clean.json", folder / "publication_manifest.json"


def signature(platform, project=DEFAULT_PROJECT):
    return tuple(
        (p.stat().st_mtime_ns, p.stat().st_size) for p in paths(platform, project)
    )


def strict_json(body):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Təkrar JSON açarı: " + key)
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Sonlu olmayan JSON rəqəmi: " + value)

    return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)


def load_platform(platform, project=DEFAULT_PROJECT):
    data_file, manifest_file = paths(platform, project)
    body = data_file.read_bytes()
    manifest = strict_json(manifest_file.read_bytes())
    if (
        manifest["platform"] != platform
        or hashlib.sha256(body).hexdigest()
        != manifest["files_sha256"]["games_clean.json"]
    ):
        raise ValueError("Məlumatın platforması və ya fayl izi təsdiqlənmədi")
    rows = strict_json(body)
    if not isinstance(rows, list) or len(rows) != manifest["games"]:
        raise ValueError("Oyun sayı manifestlə uyğun deyil")
    records = []
    for row in rows:
        a = row["analysis"]
        if a["platform"] != platform or a["schema_version"] != 1:
            raise ValueError("Analitika sxemi uyğun deyil")
        eligible = a["price_eligible"] is True
        if eligible and (
            a["price_status"] not in ("paid", "free")
            or row["final_price"] is None
            or row["currency"] is None
        ):
            raise ValueError("Naməlum qiymət hesablamaya daxil edilib")
        rated = a["rating_eligible"] is True
        if rated and (
            a["rating_count"] is None
            or a["rating_count"] <= 0
            or a["rating_value"] is None
        ):
            raise ValueError("Rəysiz oyun reytinq hesablamasına daxil edilib")
        records.append(
            {
                "id": a["record_id"],
                "title_key": a["title_key"],
                "title": row["title"],
                "categories": a["observed_categories"],
                "primary_category": row.get("category")
                if platform == "steam"
                else None,
                "status": a["price_status"],
                "currency": row["currency"],
                "price": row["final_price"],
                "original_price": row["original_price"],
                "price_eligible": eligible,
                "discount": a["discount_pct"],
                "rating": a["rating_value"] if rated else None,
                "votes": a["rating_count"],
                "rating_eligible": rated,
                "rating_status": a["rating_status"],
                "release_date": row["release_date"],
                "year": row["release_year"],
                "release_timing": a["release_timing_at_observation"],
                "observed": a["observed_at_utc"],
                "publisher": row.get("publisher"),
                "product_title": row.get("product_title"),
                "edition": row.get("edition"),
                "edition_type": row.get("edition_type"),
                "product_id": row.get("source_product_id"),
                "release_scope": a["release_date_scope"],
                "platforms": row.get("platforms") or [],
                "is_windows": row.get("is_windows"),
                "is_mac": row.get("is_mac"),
                "is_linux": row.get("is_linux"),
                "is_vr": row.get("is_vr"),
                "url": row["store_url"],
                "issues": a["issue_codes"],
            }
        )
    frame = pd.DataFrame(records)
    if frame["id"].duplicated().any():
        raise ValueError("Əsas cədvəldə təkrar oyun ID-si var")
    for column in ("price", "original_price", "discount", "rating", "votes", "year"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def filter_games(
    frame,
    query="",
    genres=(),
    statuses=(),
    price_range=None,
    minimum_votes=0,
    minimum_rating=None,
    year_range=None,
    support="Hamısı",
    platform="steam",
):
    result = frame.copy()
    if query.strip():
        result = result[
            result["title"]
            .str.casefold()
            .str.contains(query.strip().casefold(), regex=False)
        ]
    if genres:
        wanted = set(genres)
        result = result[
            result["categories"].map(lambda labels: bool(wanted.intersection(labels)))
        ]
    if statuses:
        result = result[result["status"].isin(statuses)]
    if price_range is not None:
        result = result[
            result["price_eligible"]
            & result["currency"].eq("USD")
            & result["price"].between(*price_range)
        ]
    if minimum_votes > 0:
        result = result[result["rating_eligible"] & result["votes"].ge(minimum_votes)]
    if minimum_rating is not None:
        result = result[result["rating_eligible"] & result["rating"].ge(minimum_rating)]
    if year_range is not None:
        result = result[result["year"].between(*year_range)]
    if support != "Hamısı":
        if platform == "steam":
            column = {
                "Windows": "is_windows",
                "macOS": "is_mac",
                "Linux": "is_linux",
                "VR": "is_vr",
            }[support]
            result = result[result[column].eq(True)]
        elif support == "PS4 və PS5":
            result = result[
                result["platforms"].map(lambda labels: {"PS4", "PS5"} <= set(labels))
            ]
        else:
            result = result[result["platforms"].map(lambda labels: support in labels)]
    return result


def price_rows(frame, paid_only=False):
    result = frame[frame["price_eligible"] & frame["currency"].eq("USD")]
    return result[result["status"].eq("paid")] if paid_only else result


def summary(frame):
    paid = price_rows(frame, paid_only=True)
    known = price_rows(frame)
    discounts = known[known["discount"].notna() & known["discount"].gt(0)]
    rated = frame[frame["rating_eligible"]]
    return {
        "games": len(frame),
        "free": int(frame["status"].eq("free").sum()),
        "unknown_price": int(frame["status"].eq("unknown").sum()),
        "median_paid_price": None if paid.empty else float(paid["price"].median()),
        "median_price_n": len(paid),
        "usd_price_n": len(known),
        "discounted": len(discounts),
        "rated": len(rated),
        "median_rating": None if rated.empty else float(rated["rating"].median()),
    }


def genre_stats(frame):
    exploded = frame[frame["categories"].map(bool)].explode("categories")
    if exploded.empty:
        return pd.DataFrame(
            columns=[
                "categories",
                "games",
                "median_price",
                "price_n",
                "median_rating",
                "rating_n",
            ]
        )
    counts = exploded.groupby("categories")["id"].nunique().rename("games")
    priced = (
        price_rows(exploded, paid_only=True)
        .groupby("categories")["price"]
        .agg(median_price="median", price_n="count")
    )
    rated = (
        exploded[exploded["rating_eligible"]]
        .groupby("categories")["rating"]
        .agg(median_rating="median", rating_n="count")
    )
    joined = counts.to_frame().join(priced).join(rated)
    joined[["price_n", "rating_n"]] = (
        joined[["price_n", "rating_n"]].fillna(0).astype(int)
    )
    return joined.reset_index().sort_values(
        ["games", "categories"], ascending=[False, True]
    )


def game_table(frame):
    table = frame[
        [
            "title",
            "status",
            "price",
            "currency",
            "discount",
            "rating",
            "votes",
            "release_date",
            "categories",
            "url",
        ]
    ].copy()
    table["status"] = table["status"].map(
        {
            "paid": "Ödənişli",
            "free": "Qiyməti 0 olan",
            "unknown": "Naməlum",
            "conflict": "Ziddiyyətli",
        }
    )
    table["categories"] = table["categories"].map(lambda values: ", ".join(values))
    return table.rename(
        columns={
            "title": "Oyun",
            "status": "Qiymət növü",
            "price": "Qiymət",
            "currency": "Valyuta",
            "discount": "Endirim %",
            "rating": "Reytinq",
            "votes": "Rəy sayı",
            "release_date": "Buraxılış tarixi",
            "categories": "Janr / etiket",
            "url": "Mağaza",
        }
    )
