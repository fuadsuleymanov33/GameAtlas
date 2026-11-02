import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import PLATFORMS, genre_stats, summary
from data_access import get_datasets
from insights import primary_genres, budget_distribution, discount_summary
from ui import chart, hero, metric, money

datasets = get_datasets()
hero(
    "STEAM VƏ PLAYSTATION OYUNLARI",
    "Oyun qiymətlərinə və rəylərinə bax.",
    "Steam və PS Store oyunlarını qiymətinə, janrına, endiriminə və oyunçu rəylərinə görə araşdır.",
)
ss, ps = [summary(datasets[p]) for p in ("steam", "playstation")]
cards = [
    ("Steam oyunları", f"{ss['games']:,}", "Azərbaycan mağazası · PC", "steam"),
    ("PS Store oyunları", f"{ps['games']:,}", "ABŞ mağazası · PS4 / PS5", "ps"),
    (
        "Qiyməti 0 olan oyunlar",
        f"{ss['free'] + ps['free']:,}",
        "Eyni oyun hər iki mağazada varsa, iki dəfə sayılır",
        "blue",
    ),
    (
        "Qiyməti məlum olmayan oyunlar",
        f"{ss['unknown_price'] + ps['unknown_price']:,}",
        "Qiyməti bilinməyən oyunlar pulsuz sayılmır",
        "amber",
    ),
]
for col, args in zip(st.columns(4), cards):
    with col:
        metric(*args)
st.subheader("Mağazalar üzrə ümumi məlumat")
for col, platform in zip(st.columns(2), ("steam", "playstation")):
    meta, result = PLATFORMS[platform], summary(datasets[platform])
    with col:
        st.markdown(
            f'<div class="platform-card {"ps-card" if platform == "playstation" else ""}"><div class="platform-kicker">{"PLAYSTATION / KONSOL" if platform == "playstation" else "STEAM / PC"}</div><h2>{meta["name"]}</h2><p>{result["games"]:,} oyun · Median qiymət {money(result["median_paid_price"])}</p><div class="mini-tags"><span>{"ABŞ" if platform == "playstation" else "Azərbaycan"} mağazası</span><span>{result["rated"]:,} rəyi olan oyun</span><span>{result["discounted"]:,} endirimli oyun</span></div></div>',
            unsafe_allow_html=True,
        )
        if st.button(
            f"{meta['name']} oyunlarını araşdır →",
            key=f"explore_{platform}",
            width="stretch",
        ):
            st.session_state["detail_platform"] = meta["name"]
            st.switch_page("views/detail.py")
left, right = st.columns(2)
with left:
    st.subheader("Oyunların neçə faizi ödənişlidir?")
    labels = {
        "paid": "Ödənişli",
        "free": "Qiyməti 0 olan",
        "unknown": "Naməlum",
        "conflict": "Ziddiyyətli",
    }
    records = [
        {
            "platform": PLATFORMS[p]["name"],
            "status": labels[status],
            "share": 100 * count / len(frame),
            "games": count,
        }
        for p, frame in datasets.items()
        for status, count in frame["status"].value_counts().items()
    ]
    status_figure = px.bar(
        pd.DataFrame(records),
        x="platform",
        y="share",
        color="status",
        barmode="stack",
        custom_data=["games"],
        labels={"platform": "", "share": "Toplanan oyunlarda pay (%)", "status": ""},
        color_discrete_map={
            "Ödənişli": "#2864dc",
            "Qiyməti 0 olan": "#13866d",
            "Naməlum": "#adbdcd",
            "Ziddiyyətli": "#c76a5b",
        },
    )
    status_figure.update_traces(
        hovertemplate="<b>%{x}</b><br>Pay: %{y:.1f}%<br>Oyun sayı: %{customdata[0]:,}<extra>%{fullData.name}</extra>"
    )
    chart(status_figure, "home_status")
with right:
    st.subheader("Janrlara görə oyun sayı")
    chosen = st.radio(
        "Mağaza", ["Steam", "PS Store"], horizontal=True, key="home_genres"
    )
    platform = "steam" if chosen == "Steam" else "playstation"
    mode = "Bütün janr və etiketlərdə say"
    if platform == "steam":
        mode = st.selectbox(
            "Oyunları necə qruplaşdıraq?",
            [
                "Hər oyunu bir qrupda say",
                "Bütün janr və etiketlərdə say",
            ],
            key="home_genre_basis",
        )
    counts = (
        (
            primary_genres(datasets[platform])
            if mode == "Hər oyunu bir qrupda say"
            else genre_stats(datasets[platform])
        )
        .head(10)
        .sort_values("games")
    )
    chart(
        px.bar(
            counts,
            x="games",
            y="categories",
            orientation="h",
            color_discrete_sequence=[PLATFORMS[platform]["color"]],
            text="games",
            labels={
                "games": "Oyun sayı",
                "categories": "",
            },
        ),
        "home_genres",
    )

st.subheader("Qiymətlər, endirimlər və rəylər")
budget_tab, evidence_tab = st.tabs(
    ["Qiymət aralıqları", "Endirim və məlumatların tamlığı"]
)
with budget_tab:
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
        labels={
            "budget": "Qiymət aralığı (USD)",
            "share": "Qiyməti məlum oyunlarda pay (%)",
        },
        color_discrete_map={"Steam": "#13866d", "PS Store": "#2864dc"},
    )
    fig.update_traces(
        hovertemplate="%{x}<br>Pay: %{y:.1f}%<br>%{customdata[0]:,} / %{customdata[1]:,} oyun<extra>%{fullData.name}</extra>"
    )
    chart(fig, "home_budget", height=370)
with evidence_tab:
    evidence = []
    for p, frame in datasets.items():
        d, s = discount_summary(frame), summary(frame)
        evidence.extend(
            [
                {
                    "platform": PLATFORMS[p]["name"],
                    "metric": "Rəy məlumatı var",
                    "share": 100 * s["rated"] / len(frame),
                },
                {
                    "platform": PLATFORMS[p]["name"],
                    "metric": "Dollarla qiyməti məlumdur",
                    "share": 100 * s["usd_price_n"] / len(frame),
                },
            ]
        )
    chart(
        px.bar(
            pd.DataFrame(evidence),
            x="metric",
            y="share",
            color="platform",
            barmode="group",
            text_auto=".1f",
            labels={"metric": "", "share": "Toplanan oyunlarda pay (%)"},
            color_discrete_map={"Steam": "#13866d", "PS Store": "#2864dc"},
        ),
        "home_coverage",
    )
    for col, p in zip(st.columns(2), datasets):
        d = discount_summary(datasets[p])
        with col:
            metric(
                PLATFORMS[p]["name"] + " · endirim medianı",
                "—" if d["median"] is None else f"{d['median']:.1f}%",
                f"{d['discounted']:,} endirimli oyunun medianı · {d['basis']:,} oyunda endirim hesablamaq olur",
                "steam" if p == "steam" else "ps",
            )
st.page_link(
    "views/lab.py",
    label="Büdcənə uyğun oyun tap →",
    icon=":material/experiment:",
)
st.page_link(
    "views/compare.py",
    label="Steam vs PS Store müqayisəsinə keç",
    icon=":material/compare_arrows:",
)
