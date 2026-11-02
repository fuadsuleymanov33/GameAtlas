import streamlit as st
import pandas as pd
from analytics import PLATFORMS, price_rows
from ui import hero, format_timestamp
from data_access import get_datasets, project_root

from analytics import paths


def quality_page(datasets):
    st.subheader("Hansı məlumatlar tamdır, hansılar çatışmır?")
    for platform, frame in datasets.items():
        meta = PLATFORMS[platform]
        st.subheader(f"{meta['name']} · {meta['region']}")
        report = pd.DataFrame(
            [
                {"Göstərici": "Oyun sayı", "Say": len(frame)},
                {
                    "Göstərici": "Qiyməti məlum deyil",
                    "Say": int(frame["status"].eq("unknown").sum()),
                },
                {
                    "Göstərici": "Valyutası göstərilməyib",
                    "Say": int(frame["currency"].isna().sum()),
                },
                {
                    "Göstərici": "USD qiymət qrafiklərində sayılan",
                    "Say": len(price_rows(frame)),
                },
                {
                    "Göstərici": "Reytinq qrafiklərində sayılan",
                    "Say": int(frame["rating_eligible"].sum()),
                },
                {
                    "Göstərici": "Rəy sayı 0",
                    "Say": int(frame["rating_status"].eq("unrated").sum()),
                },
                {
                    "Göstərici": "Reytinq məlumatı yoxdur",
                    "Say": int(frame["rating_status"].eq("unknown").sum()),
                },
                {
                    "Göstərici": "Buraxılış tarixi məlum deyil",
                    "Say": int(frame["release_date"].isna().sum()),
                },
                {
                    "Göstərici": "Janr və etiket göstərilməyib",
                    "Say": int((~frame["categories"].map(bool)).sum()),
                },
                {
                    "Göstərici": "Toplanma tarixindən sonrakı buraxılışlar",
                    "Say": int(
                        frame["release_timing"].eq("after_observation_date").sum()
                    ),
                },
            ]
        )
        st.dataframe(report, hide_index=True, width="stretch")
        observed = frame["observed"].dropna()
        st.caption(
            f"Məlumatların toplandığı vaxt (UTC): {format_timestamp(observed.min() if len(observed) else None)} → {format_timestamp(observed.max() if len(observed) else None)}"
        )
        with st.expander(f"{meta['name']} məlumat faylının yeri"):
            st.code(str(paths(platform, project_root())[0]), language=None)


hero(
    "MƏLUMATLAR HAQQINDA",
    "Bu məlumatlar haradan gəlib?",
    "Toplanma vaxtına, çatışmayan məlumatlara və hesablamalarda istifadə olunan oyun sayına bax.",
)
quality_page(get_datasets())
