"""Compare separate sample distributions without claiming matched-game effects."""

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import PLATFORMS, genre_stats, price_rows, summary
from insights import budget_distribution, discount_summary, year_profile
from ui import chart, metric

COLORS = {"Steam": "#13866d", "PS Store": "#2864dc"}


def render_samples(datasets):
    st.subheader("Oyunların neçə faizi bu qiymət aralığındadır?")
    bands = pd.concat(
        [
            budget_distribution(f).assign(platform=PLATFORMS[p]["name"])
            for p, f in datasets.items()
        ],
        ignore_index=True,
    )
    fig = px.bar(
        bands,
        x="budget",
        y="share",
        color="platform",
        barmode="group",
        custom_data=["games", "denominator"],
        labels={"budget": "USD aralığı", "share": "Qiyməti məlum oyunlarda pay (%)"},
        color_discrete_map=COLORS,
    )
    fig.update_traces(
        hovertemplate="%{x}<br>Pay: %{y:.1f}%<br>%{customdata[0]:,} / %{customdata[1]:,} oyun<extra>%{fullData.name}</extra>"
    )
    chart(fig, "compare_budget", height=360)
    rows = []
    for p, frame in datasets.items():
        paid = price_rows(frame, paid_only=True).sort_values("price").copy()
        paid["share"] = 100 * paid["price"].rank(method="max") / len(paid)
        rows.append(paid.drop_duplicates("price").assign(platform=PLATFORMS[p]["name"]))
    curve = pd.concat(rows, ignore_index=True)
    st.subheader("Bu məbləğə oyunların neçə faizini almaq olar?")
    if not curve.empty:
        fig = px.line(
            curve,
            x="price",
            y="share",
            color="platform",
            line_shape="hv",
            labels={
                "price": "Büdcə (USD)",
                "share": "Bu büdcəyə sığan oyunlar (%)",
            },
            color_discrete_map=COLORS,
        )
        fig.update_traces(
            hovertemplate="Büdcə: $%{x:.2f}<br>Bu büdcəyə sığan oyunlar: %{y:.1f}%<extra>%{fullData.name}</extra>"
        )
        chart(fig, "compare_ecdf", height=360)
    st.subheader("Endirimli oyunların payı və median reytinq")
    rows = []
    for col, (p, frame) in zip(st.columns(2), datasets.items()):
        s, d = summary(frame), discount_summary(frame)
        with col:
            metric(
                PLATFORMS[p]["name"] + " · reytinq medianı",
                "—" if s["median_rating"] is None else f"{s['median_rating']:.2f}",
                f"{PLATFORMS[p]['rating']} · {s['rated']:,} oyun",
                "steam" if p == "steam" else "ps",
            )
        if d["share"] is not None:
            rows.append(
                {
                    "platform": PLATFORMS[p]["name"],
                    "share": d["share"],
                    "games": d["discounted"],
                    "denominator": d["basis"],
                }
            )
    if rows:
        fig = px.bar(
            pd.DataFrame(rows),
            x="platform",
            y="share",
            color="platform",
            text_auto=".1f",
            custom_data=["games", "denominator"],
            labels={
                "platform": "",
                "share": "Endirimi hesablana bilən oyunlarda pay (%)",
            },
            color_discrete_map=COLORS,
        )
        fig.update_traces(
            hovertemplate="%{x}<br>Endirimli: %{y:.1f}%<br>%{customdata[0]:,} / %{customdata[1]:,} oyun<extra></extra>"
        )
        chart(fig, "compare_discount_share")
    st.subheader("Oyunlar buraxılış illərinə görə necə bölünür?")
    years = []
    for p, frame in datasets.items():
        profile = year_profile(frame)
        if not profile.empty:
            profile["share"] = 100 * profile["games"] / profile["games"].sum()
            years.append(profile.assign(platform=PLATFORMS[p]["name"]))
    if years:
        chart(
            px.line(
                pd.concat(years, ignore_index=True),
                x="year",
                y="share",
                color="platform",
                markers=True,
                hover_data=["games"],
                labels={
                    "year": "Mağazada göstərilən il",
                    "share": "Buraxılış ili məlum oyunlarda pay (%)",
                    "games": "Oyun sayı",
                },
                color_discrete_map=COLORS,
            ),
            "compare_release_share",
            height=360,
        )
    st.subheader("Janrlara görə median qiymət")
    for col, (p, frame) in zip(st.columns(2), datasets.items()):
        with col:
            st.markdown("**" + PLATFORMS[p]["name"] + "**")
            values = genre_stats(frame)
            values = (
                values[values["price_n"].gt(0)].head(10).sort_values("median_price")
            )
            if not values.empty:
                chart(
                    px.bar(
                        values,
                        x="median_price",
                        y="categories",
                        orientation="h",
                        hover_data=["price_n"],
                        labels={
                            "median_price": "Median qiymət (USD)",
                            "categories": "",
                            "price_n": "Qiyməti məlum oyun sayı",
                        },
                        color_discrete_sequence=[PLATFORMS[p]["color"]],
                    ),
                    "compare_genre_price_" + p,
                    height=410,
                )
