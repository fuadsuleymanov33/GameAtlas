import streamlit as st
from analytics import PLATFORMS, filter_games, price_rows

STATUS_LABELS = {
    "Ödənişli": "paid",
    "Qiyməti 0 olan": "free",
    "Naməlum": "unknown",
    "Ziddiyyətli": "conflict",
}


def filters(frame, platform):
    def reset():
        defaults = {
            "query": "",
            "genres": [],
            "statuses": [],
            "price_active": False,
            "votes": 0,
            "rating_active": False,
            "year_active": False,
            "support": "Hamısı",
        }
        for prefix, value in defaults.items():
            st.session_state[prefix + "_" + platform] = value
        for prefix in ("price", "rating", "year"):
            st.session_state.pop(prefix + "_" + platform, None)

    names, prices, devices = st.columns(3)
    with names:
        query = st.text_input(
            "Oyun adı", placeholder="Məsələn: Elden Ring", key=f"query_{platform}"
        )
        labels = sorted({g for categories in frame["categories"] for g in categories})
        genres = st.multiselect(
            "Steam janrları və etiketləri" if platform == "steam" else "PS Store janrları",
            labels,
            key=f"genres_{platform}",
            placeholder="Janr və ya etiket seç",
        )
        statuses = st.multiselect(
            "Qiymət növü",
            list(STATUS_LABELS),
            key=f"statuses_{platform}",
            placeholder="Qiymət növü seç",
        )
    with prices:
        price_range = None
        if st.checkbox(
            "Qiymət aralığını seç (USD)", key=f"price_active_{platform}"
        ):
            known = price_rows(frame)
            ceiling = max(1.0, float(known["price"].max())) if not known.empty else 1.0
            price_range = st.slider(
                "Qiymət (USD)",
                0.0,
                ceiling,
                (0.0, ceiling),
                step=1.0,
                key=f"price_{platform}",
            )
        minimum_votes = st.number_input(
            "Ən az neçə rəy olsun?",
            min_value=0,
            step=100,
            key=f"votes_{platform}",
        )
        minimum_rating = None
        if st.checkbox("Minimum reytinq seç", key=f"rating_active_{platform}"):
            scale = float(PLATFORMS[platform]["scale"])
            minimum_rating = st.slider(
                "Minimum müsbət rəy (%)"
                if platform == "steam"
                else "Minimum reytinq (5 üzərindən)",
                0.0,
                scale,
                0.0,
                step=1.0 if platform == "steam" else 0.1,
                key=f"rating_{platform}",
            )
    with devices:
        year_range = None
        if st.checkbox("Buraxılış ili seç", key=f"year_active_{platform}"):
            years = frame["year"].dropna()
            if not years.empty:
                lo, hi = int(years.min()), int(years.max())
                year_range = st.slider(
                    "Buraxılış ili",
                    lo,
                    max(lo + 1, hi),
                    (lo, hi),
                    key=f"year_{platform}",
                )
        options = (
            ["Hamısı", "Windows", "macOS", "Linux", "VR"]
            if platform == "steam"
            else ["Hamısı", "PS4", "PS5", "PS4 və PS5"]
        )
        support = st.selectbox(
            "Hansı cihazda oynamaq olar?", options, key=f"support_{platform}"
        )
        st.button(
            "Filtrləri sıfırla", key="reset_" + platform, on_click=reset, width="stretch"
        )
    result = filter_games(
        frame,
        query,
        genres,
        [STATUS_LABELS[x] for x in statuses],
        price_range,
        minimum_votes,
        minimum_rating,
        year_range,
        support,
        platform,
    )
    st.caption(f"{len(frame):,} oyundan {len(result):,}-i seçiminə uyğundur.")
    return result
