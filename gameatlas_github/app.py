"""Light Game Atlas shell and file-backed page routing."""

import streamlit as st
from ui import apply_theme, migrate_label_choices

st.set_page_config(
    page_title="Game Atlas · Oyun qiymətləri və rəyləri",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()
migrate_label_choices()
st.sidebar.markdown(
    '<div class="atlas-sidebar-brand">GAME<span>ATLAS</span></div><p class="atlas-sidebar-sub">OYUNLAR · MƏLUMATLAR · KƏŞF</p>',
    unsafe_allow_html=True,
)
st.sidebar.caption("Steam: Azərbaycan · PS Store: ABŞ")
pages = [
    st.Page("views/home.py", title="Ana səhifə", icon=":material/home:", default=True),
    st.Page(
        "views/compare.py",
        title="Steam vs PS Store",
        icon=":material/compare_arrows:",
        url_path="compare",
    ),
    st.Page(
        "views/detail.py",
        title="Detallı analiz",
        icon=":material/insights:",
        url_path="detail",
    ),
    st.Page(
        "views/lab.py",
        title="Oyun kəşfi",
        icon=":material/experiment:",
        url_path="lab",
    ),
    st.Page(
        "views/quality.py",
        title="Məlumatlar haqqında",
        icon=":material/verified:",
        url_path="quality",
    ),
]
try:
    current_page = st.navigation(pages, position="hidden")
    st.sidebar.divider()
    st.sidebar.markdown("### Oyun filtrləri")
    if current_page.url_path != "detail":
        st.sidebar.page_link(
            pages[2], label="Filtrləri aç", icon=pages[2].icon, width="stretch"
        )
    st.markdown(
        '<div class="atlas-topline"><div class="atlas-wordmark">◈ GAME<span>ATLAS</span></div><span class="atlas-badge">STEAM + PLAYSTATION</span></div>',
        unsafe_allow_html=True,
    )
    # Keep navigation visible even when Streamlit collapses the sidebar.
    with st.container(key="atlas_navigation"):
        for column, page, label in zip(
            st.columns(5),
            pages,
            ["Ana səhifə", "Müqayisə", "Analiz", "Oyun kəşfi", "Məlumatlar"],
        ):
            with column:
                st.page_link(page, label=label, icon=page.icon, width="stretch")
    current_page.run()
except (OSError, ValueError, KeyError, TypeError) as exc:
    st.error("Oyun məlumatları yüklənmədi.")
    st.info(
        "Məlumat faylları çatışmır və ya yoxlamadan keçmir. Aşağıdakı texniki məlumatla problemi yoxlamaq olar."
    )
    with st.expander("Xətanın texniki məlumatı"):
        st.code(str(exc), language=None)
        st.write(
            "Steam: steam/data/clean; PS Store: playstation/bulk/data/clean. Bu qovluqlarda games_clean.json və publication_manifest.json fayllarını yoxla."
        )
st.markdown(
    '<div class="atlas-footer"><strong>GAME ATLAS</strong><span>Steam: Azərbaycan · PS Store: ABŞ · Toplanan oyun məlumatları</span></div>',
    unsafe_allow_html=True,
)
