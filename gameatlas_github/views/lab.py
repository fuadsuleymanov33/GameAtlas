"""An exploratory workspace: budget discovery, genre evidence and a session list."""

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import PLATFORMS, filter_games, game_table, genre_stats
from data_access import get_datasets
from insights import (
    basket_summary,
    genre_overlap,
    primary_genres,
    ranked_games,
    support_profile,
    year_profile,
)
from ui import chart, hero, metric, money, game_bars


def remove_from_list():
    removed = set(st.session_state.get("lab_remove", []))
    st.session_state["atlas_wishlist"] = [
        identity
        for identity in st.session_state.get("atlas_wishlist", [])
        if identity not in removed
    ]


datasets = get_datasets()
hero(
    "OYUN KƏŞFİ",
    "Büdcənə uyğun oyun tap.",
    "Qiymət və reytinq həddini seç, uyğun oyunlara bax və bəyəndiklərini siyahına əlavə et.",
)
platform_name = st.radio(
    "Hansı mağazaya baxaq?",
    ["Steam", "PS Store"],
    horizontal=True,
    key="lab_platform",
)
platform = "steam" if platform_name == "Steam" else "playstation"
meta, frame = PLATFORMS[platform], datasets[platform]
genres = st.multiselect(
    "Janr və etiket seç",
    sorted({g for x in frame["categories"] for g in x}),
    key="lab_genres_" + platform,
    placeholder="Janr və ya etiket seç",
)
selected = filter_games(frame, genres=genres)
st.caption(
    (
        f"{len(frame):,} oyundan {len(selected):,}-i seçdiyin janrlara uyğundur."
        if genres
        else f"Janr seçilməyib: {len(frame):,} oyunun hamısı göstərilir."
    )
)
discovery, relations, timeline, evidence, collection = st.tabs(
    [
        "Oyun tap",
        "Janrlar və etiketlər",
        "Buraxılış ili və cihazlar",
        "Reytinq və rəy sayı",
        "Mənim siyahım",
    ]
)

with discovery:
    st.subheader("Qiymətə və reytinqə görə oyun seç")
    minimum, maximum, middle, right = st.columns(4)
    minimum_price = minimum.number_input(
        "Minimum qiymət (USD)",
        min_value=0.0,
        max_value=1000.0,
        value=0.0,
        step=5.0,
        key="lab_min_price_" + platform,
    )
    budget = maximum.number_input(
        "Maksimum qiymət (USD)",
        min_value=0.0,
        max_value=1000.0,
        value=20.0,
        step=5.0,
        key="lab_budget_" + platform,
    )
    votes = middle.number_input(
        "Ən az neçə rəy olsun?",
        min_value=0,
        value=100,
        step=100,
        key="lab_votes_" + platform,
    )
    threshold = right.slider(
        "Minimum müsbət rəy (%)"
        if platform == "steam"
        else "Minimum reytinq (5 üzərindən)",
        0.0,
        float(meta["scale"]),
        80.0 if platform == "steam" else 4.0,
        step=1.0 if platform == "steam" else 0.1,
        key="lab_rating_" + platform,
    )
    ranked = ranked_games(frame, minimum_votes=votes)
    if minimum_price > budget:
        st.warning(
            "Minimum qiymət maksimum qiymətdən böyük ola bilməz. Qiymət hədlərini düzəlt."
        )
    choices = filter_games(
        ranked, genres=genres, price_range=(minimum_price, budget), minimum_rating=threshold
    )
    order = st.selectbox(
        "Oyunları necə sıralayaq?",
        [
            "Rəy sayı nəzərə alınan reytinq",
            "Ən çox rəy alanlar",
            "Ən ucuzdan bahaya",
            "Ən çox endirim məbləği",
        ],
        key="lab_order",
    )
    choices["saving_usd"] = choices["original_price"] - choices["price"]
    choices.loc[choices["discount"].isna(), "saving_usd"] = float("nan")
    column, asc = {
        "Rəy sayı nəzərə alınan reytinq": ("weighted_rating", False),
        "Ən çox rəy alanlar": ("votes", False),
        "Ən ucuzdan bahaya": ("price", True),
        "Ən çox endirim məbləği": ("saving_usd", False),
    }[order]
    choices = choices.sort_values(
        [column, "id"], ascending=[asc, True], na_position="last"
    )
    a, b, c = st.columns(3)
    with a:
        metric(
            "Büdcəyə uyğun oyun",
            f"{len(choices):,}",
            "Qiymət və reytinq filtrlərinə uyğun olanlar",
            "steam" if platform == "steam" else "ps",
        )
    with b:
        metric(
            "Median qiymət",
            money(None if choices.empty else choices["price"].median()),
            "Seçilən oyunların USD qiymətlərindən",
        )
    with c:
        metric(
            "Qiyməti 0 olan oyunlar",
            str(int(choices["price"].eq(0).sum())),
            "Dollarla qiyməti məlum olanlar",
        )
    if choices.empty:
        st.info(
            "Bu qiymət və reytinqə uyğun oyun tapılmadı. Minimum qiyməti azalt, maksimum qiyməti artır, minimum reytinqi azalt və ya janrı dəyiş."
        )
    else:
        limit = st.slider("Göstərilən oyun sayı", 5, 100, 20, step=5, key="lab_limit")
        shown = choices.head(limit)
        fig = px.scatter(
            shown,
            x="price",
            y="weighted_rating",
            size="votes",
            size_max=25,
            hover_name="title",
            custom_data=["rating", "votes"],
            labels={
                "price": "Qiymət (USD)",
                "weighted_rating": "Balanslı reytinq",
                "votes": "Rəy sayı",
            },
            color_discrete_sequence=[meta["color"]],
        )
        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>USD: %{x:.2f}<br>Rəy sayı nəzərə alınan reytinq: %{y:.2f}<br>Mağaza reytinqi: %{customdata[0]:.2f}<br>Rəy sayı: %{customdata[1]:,}<extra></extra>"
        )
        chart(fig, "lab_discovery", height=390)
        display = shown[
            ["title", "price", "rating", "votes", "weighted_rating", "saving_usd"]
        ].rename(
            columns={
                "title": "Oyun",
                "price": "USD",
                "rating": meta["rating"],
                "votes": "Rəy sayı",
                "weighted_rating": "Balanslı reytinq",
                "saving_usd": "Qənaət USD",
            }
        )
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            column_config={
                "USD": st.column_config.NumberColumn(format="%.2f"),
                "Balanslı reytinq": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        indexed = shown.set_index("id")
        picked = st.multiselect(
            "Siyahına əlavə etmək istədiyin oyunları seç",
            indexed.index.tolist(),
            format_func=lambda i: indexed.loc[i, "title"] + " · " + i,
            key="lab_picks_" + platform,
            placeholder="Siyahına əlavə etmək üçün oyun seç",
        )
        if st.button(
            "＋ Seçilmiş oyunları siyahıma əlavə et", key="lab_add", width="stretch"
        ):
            saved = set(st.session_state.get("atlas_wishlist", []))
            st.session_state["atlas_wishlist"] = sorted(saved | set(picked))
            st.success(
                f"Seçdiyin oyunlar siyahıya əlavə edildi. Siyahıda {len(st.session_state['atlas_wishlist'])} mağaza üzrə oyun var."
            )

with relations:
    stats = genre_stats(selected)
    if stats.empty:
        st.info("Bu seçimdə janr məlumatı yoxdur.")
    else:
        left, right = st.columns(2)
        with left:
            st.subheader(
                "Hər oyunu bir qrupda saydıqda"
                if platform == "steam"
                else "PS Store janrlarına görə oyun sayı"
            )
            values = (
                (primary_genres(selected) if platform == "steam" else stats)
                .head(12)
                .sort_values("games")
            )
            chart(
                px.bar(
                    values,
                    x="games",
                    y="categories",
                    orientation="h",
                    text="games",
                    labels={"games": "Oyun sayı", "categories": ""},
                    color_discrete_sequence=[meta["color"]],
                ),
                "lab_primary",
                height=410,
            )
        with right:
            st.subheader("Janrların qiyməti və reytinqi")
            valid = stats[stats["price_n"].gt(0) & stats["rating_n"].gt(0)]
            if valid.empty:
                st.info(
                    "Bu janrlarda qiymət və reytinq medianlarını hesablamaq üçün məlumat yoxdur."
                )
            else:
                chart(
                    px.scatter(
                        valid,
                        x="median_price",
                        y="median_rating",
                        size="games",
                        size_max=38,
                        hover_name="categories",
                        hover_data=["price_n", "rating_n"],
                        labels={
                            "median_price": "Median qiymət (USD)",
                            "median_rating": meta["rating"] + " medianı",
                            "games": "Janrdakı oyun sayı",
                            "price_n": "Qiyməti məlum oyun sayı",
                            "rating_n": "Reytinqi məlum oyun sayı",
                        },
                        color_discrete_sequence=[meta["color"]],
                    ),
                    "lab_genre_bubble",
                    height=410,
                )
        st.subheader("Hansı janrlar eyni oyunlarda rast gəlinir?")
        count = st.slider(
            "Cədvəldə göstərilən janr sayı", 3, 15, 8, key="lab_overlap_n"
        )
        labels = stats.head(count)["categories"].tolist()
        counts, similarity = genre_overlap(selected, labels)
        mode = st.radio(
            "Cədvəldə nə göstərilsin?",
            ["Hər iki janra aid oyun sayı", "Janr oxşarlığı (%)"],
            horizontal=True,
            key="lab_overlap_mode",
        )
        overlap_figure = px.imshow(
            counts if mode == "Hər iki janra aid oyun sayı" else similarity,
            text_auto=True if mode == "Hər iki janra aid oyun sayı" else ".1f",
            aspect="auto",
            color_continuous_scale="Teal" if platform == "steam" else "Blues",
            labels={"color": mode, "x": "Janr / etiket", "y": "Janr / etiket"},
        )
        overlap_figure.update_traces(
            hovertemplate="<b>%{y} × %{x}</b><br>"
            + (
                "Oxşarlıq: %{z:.1f}%"
                if mode == "Janr oxşarlığı (%)"
                else "Ortaq oyun: %{z:,}"
            )
            + "<extra></extra>"
        )
        chart(overlap_figure, "lab_overlap", height=480)

with timeline:
    st.subheader("Oyunların buraxılış illəri")
    years = year_profile(selected)
    if years.empty:
        st.info("Seçilən oyunların buraxılış ili məlum deyil.")
    else:
        chart(
            px.area(
                years,
                x="year",
                y="games",
                markers=True,
                labels={
                    "year": "Mağazada göstərilən il",
                    "games": "Oyun sayı",
                },
                color_discrete_sequence=[meta["color"]],
            ),
            "lab_year_counts",
            height=360,
        )
    st.subheader("Oyunları hansı cihazlarda oynamaq olar?")
    support = support_profile(selected, platform)
    chart(
        px.bar(
            support,
            x="support",
            y="games",
            color="status" if platform == "steam" else None,
            barmode="stack",
            labels={
                "support": "Cihaz",
                "games": "Oyun",
                "status": "",
            },
            color_discrete_map={
                "Bəli": meta["color"],
                "Xeyr": "#b9c9d8",
                "Naməlum": "#e9b86a",
            },
            color_discrete_sequence=[meta["color"]],
        ),
        "lab_support",
        height=350,
    )

with evidence:
    st.subheader("Çox rəy alan və yüksək reytinqli oyunlar")
    strength = st.slider(
        "Az rəyli oyunların balını nə qədər tənzimləyək?",
        0,
        1000,
        200,
        step=50,
        key="lab_strength",
    )
    minimum = st.number_input(
        "Liderlərdə ən az neçə rəy olsun?",
        min_value=0,
        value=100,
        step=100,
        key="lab_evidence_votes",
    )
    ranks = ranked_games(frame, minimum_votes=minimum, strength=strength)
    ranks = filter_games(ranks, genres=genres).head(15)
    if ranks.empty:
        st.info("Bu qədər rəyi olan oyun tapılmadı. Minimum rəy sayını azalt.")
    else:
        left, right = st.columns(2)
        with left:
            st.markdown(f"**Balanslı reytinqə görə ilk {len(ranks)} oyun**")
            chart(
                game_bars(
                    ranks.sort_values("weighted_rating"),
                    "weighted_rating",
                    "Balanslı reytinq",
                    meta["color"],
                    ["rating", "votes"],
                ),
                "lab_ranked",
                height=500,
            )
        with right:
            most_votes = (
                selected[selected["rating_eligible"]]
                .nlargest(15, "votes")
                .sort_values("votes")
            )
            st.markdown(f"**Ən çox rəy alan {len(most_votes)} oyun**")
            chart(
                game_bars(most_votes, "votes", "Rəy sayı", "#8c61c5"),
                "lab_votes",
                height=500,
            )

with collection:
    st.subheader("Öz oyun siyahın")
    all_rows = pd.concat(
        [f.assign(platform=PLATFORMS[p]["name"]) for p, f in datasets.items()],
        ignore_index=True,
    )
    saved_ids = st.session_state.get("atlas_wishlist", [])
    saved = all_rows[all_rows["id"].isin(saved_ids)]
    if saved.empty:
        st.info("Siyahın boşdur. Oyun tap bölməsində oyunları seçib əlavə et.")
    else:
        stats = basket_summary(saved)
        left, middle, right = st.columns(3)
        with left:
            metric(
                "Siyahıdakı oyun",
                str(stats["games"]),
                "Eyni mağaza məhsulu bir dəfə sayılır",
            )
        with middle:
            metric(
                "Məlum qiymətlərin cəmi",
                money(stats["observed_total"]),
                f"{stats['games']} oyundan {stats['priced']}-inin USD qiyməti məlumdur",
                "steam",
            )
        with right:
            metric(
                "Qiyməti cəmdə sayılmayan",
                str(stats["unknown"]),
                "Qiyməti və ya valyutası məlum deyil",
                "amber",
            )
        if stats["unknown"]:
            st.warning(
                "Bəzi oyunların qiyməti məlum olmadığı üçün göstərilən cəm bütün siyahının qiyməti deyil."
            )
        table = game_table(saved)
        table.insert(1, "Platforma", saved["platform"].to_numpy())
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={"Mağaza": st.column_config.LinkColumn(display_text="Aç")},
        )
        remove = st.multiselect(
            "Siyahıdan çıxar",
            saved["id"].tolist(),
            format_func=lambda i: saved.set_index("id").loc[i, "title"] + " · " + i,
            key="lab_remove",
            placeholder="Çıxarmaq istədiyin oyunları seç",
        )
        st.button(
            "Seçilənləri siyahıdan çıxar",
            key="lab_remove_button",
            on_click=remove_from_list,
        )
        st.download_button(
            "Siyahımı JSON kimi endir",
            saved.to_json(orient="records", force_ascii=False, indent=2),
            file_name="game_atlas_my_list.json",
            mime="application/json",
            key="lab_export",
        )
