import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import price_rows, summary
from comparison import exact_candidates, price_comparison
from data_access import get_datasets
from ui import chart, hero, metric, money, format_date, format_timestamp
from sample_comparison import render_samples

datasets = get_datasets()
steam, ps = datasets["steam"], datasets["playstation"]
hero(
    "PC × PLAYSTATION",
    "Steam və PS Store qiymətlərini müqayisə et.",
    "Əvvəl mağazalardakı oyunların ümumi qiymətlərinə bax. Sonra eyni oyunu seçib iki mağazanın qiymətini müqayisə et.",
)
overview, pair = st.tabs(["Mağazaların ümumi müqayisəsi", "Eyni oyunun qiymətləri"])
with overview:
    st.subheader("Oyun qiymətləri hansı aralıqdadır?")
    merged = pd.concat(
        [
            price_rows(frame, paid_only=True).assign(platform=label)
            for frame, label in ((steam, "Steam"), (ps, "PS Store"))
        ],
        ignore_index=True,
    )
    chart(
        px.box(
            merged,
            x="platform",
            y="price",
            color="platform",
            points=False,
            labels={"platform": "", "price": "Qiymət (USD)"},
            color_discrete_map={"Steam": "#13866d", "PS Store": "#2864dc"},
        ),
        "compare_distribution",
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Platforma": label,
                    "Qiyməti məlum ödənişli oyun": summary(frame)["median_price_n"],
                    "Median qiymət (USD)": summary(frame)["median_paid_price"],
                    "Qiyməti məlum olmayan oyun": summary(frame)["unknown_price"],
                    "Region": region,
                }
                for frame, label, region in (
                    (steam, "Steam", "AZ"),
                    (ps, "PS Store", "US"),
                )
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    render_samples(datasets)
with pair:
    candidates = exact_candidates(steam, ps)
    st.caption(
        f"Hər iki mağazada eyni adlı {len(candidates):,} oyun tapılıb."
    )
    method = st.radio(
        "Oyunları necə seçmək istəyirsən?",
        ["Eyni adlı oyunlardan seç", "Əl ilə iki oyun seç"],
        horizontal=True,
        key="pair_method",
    )
    si, pi = steam.set_index("id"), ps.set_index("id")
    if method == "Eyni adlı oyunlardan seç":
        if candidates.empty:
            st.info(
                "Avtomatik siyahıda uyğun oyun tapılmadı. İki mağazadan oyunları özün seçə bilərsən."
            )
            st.stop()
        candidate = st.selectbox(
            "Müqayisə ediləcək oyun",
            candidates.index.tolist(),
            format_func=lambda i: candidates.loc[i, "title_steam"],
            key="pair_candidate",
        )
        steam_id, ps_id = candidates.loc[candidate, ["id_steam", "id_ps"]]
    else:
        left, right = st.columns(2)
        with left:
            steam_id = st.selectbox(
                "Steam oyunu",
                si.index.tolist(),
                format_func=lambda i: si.loc[i, "title"],
                key="manual_steam",
            )
        with right:
            ps_id = st.selectbox(
                "PS Store oyunu",
                pi.index.tolist(),
                format_func=lambda i: pi.loc[i, "title"] + " · " + i,
                key="manual_ps",
            )
    sr, pr = si.loc[steam_id], pi.loc[ps_id]
    left, right = st.columns(2)
    for col, row, label, tone, identity in (
        (left, sr, "Steam", "steam", steam_id),
        (right, pr, "PS Store", "ps", ps_id),
    ):
        with col:
            metric(
                label,
                row["title"],
                "AZ / PC" if tone == "steam" else "US / " + ", ".join(row["platforms"]),
                tone,
            )
            st.caption(f"Mağaza ID-si: {identity}")
            st.text(f"Məhsul adı: {row['product_title'] or row['title']}")
            st.text(
                f"Versiya: {row['edition'] or 'Mağazada ayrıca versiya adı göstərilməyib'}"
            )
            st.caption(
                f"Buraxılış tarixi: {format_date(row['release_date'])} · Toplanma vaxtı (UTC): {format_timestamp(row['observed'])}"
            )
            st.link_button("Mağazada yoxla ↗", row["url"])
    checked = st.checkbox(
        "Eyni oyun və eyni versiya olduğunu yoxladım",
        value=False,
        key=f"verified_{steam_id}_{ps_id}",
    )
    if not checked:
        st.info(
            "Qiymət fərqi üçün eyni oyun və versiya olduğunu təsdiqlə."
        )
    else:
        result = price_comparison(sr, pr)
        if result is None:
            st.warning(
                "Seçilən oyunlardan ən az birinin dollarla (USD) qiyməti məlum deyil. Qiymət fərqini hesablamaq üçün hər iki qiymət lazımdır."
            )
        else:
            cards = [
                (
                    "Steam qiyməti",
                    money(result["steam_price"]),
                    "Azərbaycan mağazası",
                    "steam",
                ),
                ("PS Store qiyməti", money(result["ps_price"]), "ABŞ mağazası", "ps"),
                (
                    "Qiymət fərqi",
                    money(result["saving_usd"]),
                    result["cheaper"]
                    + (
                        " daha ucuzdur" if result["cheaper"] != "Bərabər" else " qiymət"
                    ),
                    "blue",
                ),
            ]
            for col, args in zip(st.columns(3), cards):
                with col:
                    metric(*args)
            chart(
                px.bar(
                    pd.DataFrame(
                        {
                            "Platforma": ["Steam", "PS Store"],
                            "Qiymət": [result["steam_price"], result["ps_price"]],
                        }
                    ),
                    x="Platforma",
                    y="Qiymət",
                    color="Platforma",
                    text_auto=".2f",
                    labels={"Qiymət": "Toplanan qiymət (USD)"},
                    color_discrete_map={"Steam": "#13866d", "PS Store": "#2864dc"},
                ),
                "pair_price",
            )
            if result["ps_relative_to_steam_pct"] is not None:
                st.caption(
                    f"PS Store qiymətinin Steam qiymətinə görə fərqi: {result['ps_relative_to_steam_pct']:+.2f}%."
                )
            else:
                st.caption(
                    "Faiz fərqi: — (Steam qiyməti $0)"
                )
