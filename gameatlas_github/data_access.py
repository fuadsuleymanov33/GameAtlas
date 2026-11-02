"""DataFrame provider shared by pages; clean datasets are always read-only."""

import os
from pathlib import Path

import streamlit as st

from analytics import DEFAULT_PROJECT, load_platform, signature


def project_root():
    return Path(os.environ.get("GAME_ANALYTICS_PROJECT", str(DEFAULT_PROJECT)))


@st.cache_data(max_entries=8, show_spinner="Oyunlar yüklənir…")
def cached_platform(platform, root, fingerprint, schema=3):
    return load_platform(platform, Path(root))


def get_platform(platform):
    root = project_root()
    return cached_platform(platform, str(root), signature(platform, root), schema=3)


def get_datasets():
    return {name: get_platform(name) for name in ("steam", "playstation")}
