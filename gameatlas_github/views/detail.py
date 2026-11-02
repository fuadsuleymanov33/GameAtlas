import streamlit as st
import pandas as pd
import plotly.express as px
from analytics import PLATFORMS, game_table, genre_stats, price_rows, summary
from ui import chart, money, hero
from data_access import get_platform

from filters import filters, STATUS_LABELS


def dashboard(frame, platform):
    meta = PLATFORMS[platform]
    hero(
        "OYUN ANALİZİ / " + meta["region"],
        f"{meta['name']} oyunlarını araşdır",
        f"{len(frame):,} oyun arasından seçim et. Aşağıdakı filtrlərlə oyun adını, janrı, qiyməti və minimum reytinqi dəyişə bilərsən.",
        "steam" if platform == "steam" else "ps",
    )
    with st.expander("Oyunları filtrlə", expanded=True):
        selected = filters(frame, platform)
    result = summary(selected)
    cols = st.columns(4)
    cols[0].metric("Filtrə uyğun oyun", f"{result['games']:,}")
    cols[1].metric(
        "Median qiymət", money(result["median_paid_price"])
    )
    cols[1].caption(f"USD · {result['median_price_n']:,} oyun")
    cols[2].metric("Qiyməti 0 olan", f"{result['free']:,}")
    cols[3].metric("Qiyməti məlum deyil", f"{result['unknown_price']:,}")
    if selected.empty:
        st.info(
            "Bu filtrlərə uyğun oyun tapılmadı. Qiymət və reytinq həddini azalt və ya filtrləri sıfırla."
        )
        return selected
    overview, prices, ratings, games = st.tabs(
        ["Ümumi baxış", "Qiymət və endirim", "Oyunçu rəyləri", "Oyun cədvəli"]
    )
    accent = meta["color"]
    with overview:
        st.subheader("Ödənişli və 0 qiymətli oyunlar")
        counts = (
            selected["status"]
            .value_counts()
            .rename_axis("status")
            .reset_index(name="games")
        )
        counts["status"] = counts["status"].map(
            {v: k for k, v in STATUS_LABELS.items()}
        )
        chart(
            px.pie(
                counts,
                names="status",
                values="games",
                hole=0.65,
                color="status",
                labels={"status": "Qiymət növü", "games": "Oyun sayı"},
                color_discrete_map={
                    "Ödənişli": accent,
                    "Qiyməti 0 olan": "#c49128",
                    "Naməlum": "#8ca0b6",
                    "Ziddiyyətli": "#ef7b7b",
                },
            ),
            f"status_{platform}",
        )
        st.subheader("Oyunlar hansı illərdə çıxıb?")
        years = (
            selected["year"]
            .dropna()
            .astype(int)
            .value_counts()
            .sort_index()
            .rename_axis("year")
            .reset_index(name="games")
        )
        if years.empty:
            st.info("Buraxılış ili məlum deyil.")
        else:
            chart(
                px.bar(
                    years,
                    x="year",
                    y="games",
                    labels={
                        "year": "Mağazada yazılan buraxılış ili",
                        "games": "Oyun sayı",
                    },
                    color_discrete_sequence=[accent],
                ),
                f"years_{platform}",
            )
    with prices:
        known = price_rows(selected)
        st.caption(
            f"Seçilən {len(selected):,} oyundan {len(known):,}-inin dollarla (USD) qiyməti məlumdur."
        )
        if known.empty:
            st.info(
                "Seçilən oyunların dollarla qiyməti məlum deyil. Qiymət qrafikləri üçün filtrləri dəyiş."
            )
        else:
            left, right = st.columns(2)
            with left:
                st.subheader("Oyunlar hansı qiymətlərdədir?")
                chart(
                    px.histogram(
                        known,
                        x="price",
                        nbins=25,
                        labels={"price": "Qiymət (USD)"},
                        color_discrete_sequence=[accent],
                    ),
                    f"price_hist_{platform}",
                )
            with right:
                st.subheader("Janrlara görə median qiymət")
                genres = genre_stats(selected)
                valid = (
                    genres[genres["price_n"].gt(0)].head(12).sort_values("median_price")
                )
                if valid.empty:
                    st.info(
                        "Bu seçimdə həm janrı, həm ödənişli USD qiyməti məlum olan oyun yoxdur."
                    )
                else:
                    chart(
                        px.bar(
                            valid,
                            x="median_price",
                            y="categories",
                            orientation="h",
                            hover_data=["price_n"],
                            labels={
                                "median_price": "Median qiymət (USD)",
                                "categories": "",
                                "price_n": "Hesablamadakı oyun sayı",
                            },
                            color_discrete_sequence=[accent],
                        ),
                        f"genre_prices_{platform}",
                    )
            discounted = known[known["discount"].gt(0)].copy()
            st.subheader("Toplanan oyunların endirimləri")
            st.caption(
                f"{len(discounted):,} oyunda endirim var."
            )
            if discounted.empty:
                st.info(
                    "Bu seçimdə qiymətlərindən endirim hesablaya bildiyimiz oyun yoxdur."
                )
            else:
                discounted["saving"] = (
                    discounted["original_price"] - discounted["price"]
                )
                chart(
                    px.histogram(
                        discounted,
                        x="discount",
                        nbins=20,
                        labels={"discount": "Endirim (%)"},
                        color_discrete_sequence=["#c49128"],
                    ),
                    f"discount_hist_{platform}",
                )
                savings = discounted.nlargest(10, "saving").sort_values("saving")
                chart(
                    px.bar(
                        savings,
                        x="saving",
                        y="title",
                        orientation="h",
                        hover_data=["price", "discount"],
                        labels={
                            "saving": "Qənaət (USD)",
                            "title": "",
                            "price": "Qiymət",
                            "discount": "Endirim %",
                        },
                        color_discrete_sequence=[accent],
                    ),
                    f"savings_{platform}",
                )
                st.caption(
                    f"Əvvəlki qiymətlə endirimli qiymət arasındakı dollar fərqi ən böyük olan {len(savings)} oyun göstərilir."
                )
    with ratings:
        rated = selected[selected["rating_eligible"]]
        st.subheader(meta["rating"])
        st.caption(
            f"Seçilən {len(selected):,} oyundan {len(rated):,}-inin reytinqi və ən az bir rəyi var."
        )
        if rated.empty:
            st.info("Bu seçimdə reytinqi və rəy sayı məlum olan oyun yoxdur.")
        else:
            left, right = st.columns(2)
            with left:
                chart(
                    px.histogram(
                        rated,
                        x="rating",
                        nbins=20,
                        labels={
                            "rating": "Müsbət rəy (%)"
                            if platform == "steam"
                            else "Reytinq (5 üzərindən)"
                        },
                        color_discrete_sequence=[accent],
                    ),
                    f"rating_hist_{platform}",
                )
            with right:
                chart(
                    px.scatter(
                        rated,
                        x="votes",
                        y="rating",
                        log_x=True,
                        hover_name="title",
                        opacity=0.5,
                        labels={
                            "votes": "Rəy sayı (loqarifmik şkala)",
                            "rating": meta["rating"],
                        },
                        color_discrete_sequence=[accent],
                    ),
                    f"votes_ratings_{platform}",
                )
            joint = price_rows(rated)
            if not joint.empty:
                st.subheader("Qiymət və oyunçu reytinqi")
                chart(
                    px.scatter(
                        joint,
                        x="price",
                        y="rating",
                        hover_name="title",
                        hover_data=["votes"],
                        opacity=0.5,
                        labels={
                            "price": "Qiymət (USD)",
                            "rating": meta["rating"],
                            "votes": "Rəy sayı",
                        },
                        color_discrete_sequence=[accent],
                    ),
                    f"price_rating_{platform}",
                )
    with games:
        st.subheader("Seçiminə uyğun oyunlar")
        sort = st.selectbox(
            "Sıralama",
            [
                "Ad: A–Z",
                "Qiymət: aşağıdan",
                "Rəy sayı: çoxdan aza",
                "Reytinq: yüksəkdən aşağıya",
            ],
            key=f"sort_{platform}",
        )
        column, ascending = {
            "Ad: A–Z": ("title", True),
            "Qiymət: aşağıdan": ("price", True),
            "Rəy sayı: çoxdan aza": ("votes", False),
            "Reytinq: yüksəkdən aşağıya": ("rating", False),
        }[sort]
        table = game_table(
            selected.sort_values(
                [column, "id"], ascending=[ascending, True], na_position="last"
            )
        )
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            height=500,
            column_config={
                "Mağaza": st.column_config.LinkColumn("Mağaza", display_text="Aç"),
                "Qiymət": st.column_config.NumberColumn(format="%.2f"),
                "Reytinq": st.column_config.NumberColumn(format="%.2f"),
                "Endirim %": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.download_button(
            "Filtrə uyğun oyunları JSON kimi endir",
            data=selected.to_json(orient="records", force_ascii=False, indent=2),
            file_name=f"{platform}_filtered_analytics.json",
            mime="application/json",
            key=f"download_{platform}",
        )
    return selected


# File-backed pages support Streamlit navigation and AppTest.
platform_name = st.selectbox(
    "Analiz platforması", ["Steam", "PS Store"], key="detail_platform"
)
platform = "steam" if platform_name == "Steam" else "playstation"
selected = dashboard(get_platform(platform), platform)
if selected is not None and not selected.empty:
    with st.expander("Öz qrafikini qur", expanded=False):
        kind = st.selectbox(
            "Qrafikdə nə göstərilsin?",
            [
                "Qiymət və reytinq",
                "Janrlara görə qiymətlər",
                "İl və janr üzrə oyun sayı",
                "Cihazlara görə oyun sayı",
                "Nəşriyyatlara görə oyunlar",
            ],
            key="chart_builder",
        )
        meta = PLATFORMS[platform]
        if kind == "Qiymət və reytinq":
            joint = price_rows(selected[selected["rating_eligible"]])
            if joint.empty:
                st.info(
                    "Bu seçimdə həm USD qiyməti, həm reytinqi məlum olan oyun yoxdur."
                )
            else:
                logarithmic = st.checkbox(
                    "Böyük qiymət fərqlərini sıxılmış şkala ilə göstər",
                    key="builder_log",
                )
                if logarithmic:
                    joint = joint[joint["price"].gt(0)]
                if joint.empty:
                    st.info("Bu seçimdə qiyməti 0-dan böyük olan oyun yoxdur.")
                else:
                    chart(
                        px.scatter(
                            joint,
                            x="price",
                            y="rating",
                            log_x=logarithmic,
                            hover_name="title",
                            hover_data=["votes"],
                            color_discrete_sequence=[meta["color"]],
                            labels={
                                "price": "Qiymət (USD)",
                                "rating": meta["rating"],
                                "votes": "Rəy sayı",
                            },
                        ),
                        "builder_scatter",
                    )
        elif kind == "Janrlara görə qiymətlər":
            priced = price_rows(selected, paid_only=True)
            expanded = priced[priced["categories"].map(bool)].explode("categories")
            top = genre_stats(selected).head(10)["categories"]
            expanded = expanded[expanded["categories"].isin(top)]
            if expanded.empty:
                st.info(
                    "Bu seçimdə ödənişli USD qiyməti və janrı məlum olan oyun yoxdur."
                )
            else:
                chart(
                    px.box(
                        expanded,
                        x="price",
                        y="categories",
                        orientation="h",
                        points=False,
                        color_discrete_sequence=[meta["color"]],
                        labels={"price": "Qiymət (USD)", "categories": ""},
                    ),
                    "builder_box",
                    height=420,
                )
        elif kind == "İl və janr üzrə oyun sayı":
            valid = selected[
                selected["year"].notna() & selected["categories"].map(bool)
            ].explode("categories")
            valid = valid[
                valid["categories"].isin(genre_stats(selected).head(10)["categories"])
            ]
            if valid.empty:
                st.info("Bu qrafik üçün həm ili, həm janrı məlum olan oyun tapılmadı.")
            else:
                matrix = valid.pivot_table(
                    index="categories",
                    columns="year",
                    values="id",
                    aggfunc="nunique",
                    fill_value=0,
                )
                matrix.columns = matrix.columns.astype(int)
                chart(
                    px.imshow(
                        matrix,
                        aspect="auto",
                        color_continuous_scale="Blues"
                        if platform == "playstation"
                        else "Greens",
                        labels={
                            "x": "Mağazada yazılan buraxılış ili",
                            "y": "Janr / etiket",
                            "color": "Oyun sayı",
                        },
                    ),
                    "builder_heatmap",
                    height=420,
                )
        elif kind == "Cihazlara görə oyun sayı":
            if platform == "steam":
                counts = {
                    label: int(selected[column].eq(True).sum())
                    for label, column in (
                        ("Windows", "is_windows"),
                        ("macOS", "is_mac"),
                        ("Linux", "is_linux"),
                        ("VR", "is_vr"),
                    )
                }
            else:
                counts = (
                    selected["platforms"]
                    .map(lambda labels: " + ".join(labels) if labels else "Naməlum")
                    .value_counts()
                    .to_dict()
                )
            chart(
                px.bar(
                    pd.DataFrame(
                        {"Dəstək": list(counts), "Oyun": list(counts.values())}
                    ),
                    x="Dəstək",
                    y="Oyun",
                    color_discrete_sequence=[meta["color"]],
                ),
                "builder_support",
            )
        else:
            if platform == "steam":
                st.info(
                    "Toplanan Steam məlumatlarında oyunun nəşriyyatı göstərilməyib. Bu qrafik PS Store üçün mövcuddur."
                )
            else:
                counts = (
                    selected["publisher"]
                    .dropna()
                    .value_counts()
                    .head(12)
                    .sort_values()
                    .rename_axis("Nəşriyyat")
                    .reset_index(name="Oyun")
                )
                if counts.empty:
                    st.info("Seçilən oyunların nəşriyyat məlumatı yoxdur.")
                else:
                    chart(
                        px.bar(
                            counts,
                            x="Oyun",
                            y="Nəşriyyat",
                            orientation="h",
                            color_discrete_sequence=[meta["color"]],
                        ),
                        "builder_publishers",
                        height=420,
                    )
