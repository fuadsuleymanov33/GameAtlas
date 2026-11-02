"""Shared light UI components; HTML interpolations are escaped."""

from html import escape
from pathlib import Path

import streamlit as st
import plotly.express as px

CHART_LABELS = {
    "count": "Oyun sayı",
    "platform": "Mağaza",
    "status": "Qiymət növü",
    "games": "Oyun sayı",
    "price": "Qiymət (USD)",
    "rating": "Mağaza reytinqi",
    "votes": "Rəy sayı",
    "id": "Mağaza ID-si",
    "title": "Oyun",
    "categories": "Janr / etiket",
    "price_n": "Qiyməti məlum oyun sayı",
    "rating_n": "Reytinqi məlum oyun sayı",
    "weighted_rating": "Rəy sayı nəzərə alınan reytinq",
    "discount": "Endirim (%)",
    "saving_usd": "Endirim məbləği (USD)",
}


def migrate_label_choices():
    """Keep open sessions usable after display-option names have changed."""
    renamed = {
        "Əsas təkrarsız qrup": "Hər oyunu bir qrupda say",
        "Real janr üzvlüyü": "Bütün janr və etiketlərdə say",
        "Demo dizayn · süni indeks": "Hər oyunu bir qrupda say",
        "Demo · nümunə görünüş": "Hər oyunu bir qrupda say",
        "Rəy əsası ilə balanslı": "Rəy sayı nəzərə alınan reytinq",
        "Ən çox rəy / səs": "Ən çox rəy alanlar",
        "Ən münasib qiymət": "Ən ucuzdan bahaya",
        "Ən çox USD qənaəti": "Ən çox endirim məbləği",
        "Ortaq unikal oyun": "Hər iki janra aid oyun sayı",
        "Jaccard oxşarlığı (%)": "Janr oxşarlığı (%)",
        "Ad üzrə namizəd": "Eyni adlı oyunlardan seç",
        "Qiymət × reytinq": "Qiymət və reytinq",
        "Janr üzrə qiymət yayılması": "Janrlara görə qiymətlər",
        "Buraxılış ili × janr": "İl və janr üzrə oyun sayı",
        "Platforma dəstəyi": "Cihazlara görə oyun sayı",
        "Publisher üzrə oyunlar": "Nəşriyyatlara görə oyunlar",
        "Rəy / səs sayı: çoxdan": "Rəy sayı: çoxdan aza",
        "Rəy / reytinq: yüksəkdən": "Reytinq: yüksəkdən aşağıya",
        "Sıfır qiymətli": "Qiyməti 0 olan",
    }
    for key in (
        "home_genre_basis",
        "lab_order",
        "lab_overlap_mode",
        "pair_method",
        "chart_builder",
        "sort_steam",
        "sort_playstation",
        "statuses_steam",
        "statuses_playstation",
    ):
        value = st.session_state.get(key)
        if isinstance(value, str) and value in renamed:
            st.session_state[key] = renamed[value]
        elif isinstance(value, list):
            changed = [
                renamed.get(item, item) if isinstance(item, str) else item
                for item in value
            ]
            if changed != value:
                st.session_state[key] = changed


def apply_theme():
    css = Path(__file__).with_name("style.css").read_text(encoding="utf-8")
    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)


def hero(eyebrow, title, subtitle, tone="blue"):
    safe_tone = tone if tone in ("blue", "steam", "ps") else "blue"
    st.markdown(
        f'<section class="atlas-hero atlas-{safe_tone}"><div class="hero-copy">'
        f'<div class="hero-kicker"><span class="hero-dot"></span>{escape(eyebrow)}</div>'
        f"<h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>"
        '<div class="hero-art" aria-hidden="true"><div class="controller">'
        '<span class="dpad">✚</span><span class="joy joy-a"></span><span class="joy joy-b"></span>'
        '<span class="game-key key-a">A</span><span class="game-key key-b">B</span></div>'
        '<span class="floating-chip chip-one">OYNA ↗</span><span class="floating-chip chip-two">SEÇ · KƏŞF ET</span></div></section>',
        unsafe_allow_html=True,
    )


def section_title(title, subtitle=""):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def money(value):
    return "—" if value is None else f"${value:,.2f}"


def metric(label, value, caption="", tone="blue"):
    safe_tone = tone if tone in ("blue", "steam", "ps", "amber") else "blue"
    st.markdown(
        f'<div class="atlas-stat stat-{safe_tone}"><span class="stat-label">{escape(str(label))}</span>'
        f'<strong class="stat-value">{escape(str(value))}</strong><span class="stat-caption">{escape(str(caption))}</span></div>',
        unsafe_allow_html=True,
    )


def chart(figure, key, height=340):
    # Translate Plotly's fallback captions without altering trace values or IDs.
    for axis in [*figure.select_xaxes(), *figure.select_yaxes()]:
        if axis.title.text in CHART_LABELS:
            axis.title.text = CHART_LABELS[axis.title.text]
    for trace in figure.data:
        if trace.hovertemplate:
            template = trace.hovertemplate
            for field, label in CHART_LABELS.items():
                template = template.replace("<br>" + field + "=", "<br>" + label + ": ")
                if template.startswith(field + "="):
                    template = label + ": " + template[len(field) + 1 :]
            trace.hovertemplate = template
    figure.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Trebuchet MS, Verdana, sans-serif", size=14, color="#304c68"),
        margin=dict(l=12, r=18, t=64 if figure.layout.title.text else 28, b=22),
        title=dict(
            font=dict(family="Trebuchet MS, Verdana, sans-serif", size=15),
            x=0.04,
            xanchor="left",
        ),
        height=height,
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#c9dcf0",
            font=dict(
                family="Trebuchet MS, Verdana, sans-serif", size=14, color="#15304b"
            ),
        ),
        transition=dict(duration=320, easing="cubic-in-out"),
        legend=dict(title_text="", orientation="h", y=1.12, x=0),
        colorway=["#13866d", "#2864dc", "#df9b29", "#7c66bb", "#b86a60"],
    )
    figure.update_xaxes(
        gridcolor="rgba(32,74,106,.08)",
        zerolinecolor="rgba(32,74,106,.14)",
        automargin=True,
    )
    figure.update_yaxes(
        gridcolor="rgba(32,74,106,.08)",
        zerolinecolor="rgba(32,74,106,.14)",
        automargin=True,
    )
    st.plotly_chart(
        figure,
        width="stretch",
        theme=None,
        key="chart_" + key,
        config={"displaylogo": False},
    )


def format_date(iso):
    if not isinstance(iso, str) or not iso.strip():
        return "Məlum deyil"
    return iso[:10]


def format_timestamp(iso):
    if not isinstance(iso, str) or not iso.strip():
        return "Məlum deyil"
    return iso[:19].replace("T", " ")


def game_bars(frame, value, label, color, hover_data=()):
    """Keep different IDs separate even when display titles coincide."""
    fig = px.bar(
        frame,
        x=value,
        y="id",
        orientation="h",
        hover_name="title",
        hover_data=list(hover_data),
        labels={**CHART_LABELS, value: label, "id": "Mağaza ID-si"},
        color_discrete_sequence=[color],
    )
    fig.update_yaxes(
        title_text="",
        tickmode="array",
        tickvals=frame["id"].tolist(),
        ticktext=[
            title if len(title) <= 24 else title[:23] + "…" for title in frame["title"]
        ],
        tickfont=dict(size=11),
    )
    return fig
