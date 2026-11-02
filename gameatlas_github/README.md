# GameAtlas

An interactive game analytics app by Fuad Suleymanov, built with Python,
Streamlit, pandas, NumPy and Plotly. The interface is in Azerbaijani.

## Features

- Overview of 6,100 Steam game records and 1,500 PlayStation Store game records.
- Filters for title, genre, price, ratings, release year and device support.
- Price distributions, discounts and player review analysis.
- Store comparisons and same-title candidates, with edition confirmation before comparing prices.
- Budget-based game discovery and a session-based personal game list.
- Data completeness reports and collection timestamps.

## Data

The bundled data is a snapshot collected in October 2026, not live prices.
Steam data represents the Azerbaijan store; PlayStation data represents the US store.
The stores represent different regions and platforms. Matching names do not guarantee matching editions.
Missing prices are retained as unknown; unrated games are excluded from rating calculations.
Game records can overlap between stores; 7,600 records does not mean 7,600 unique games.
Bundled manifests verify the deployment dataset SHA-256 hashes and record counts.
Only source-file provenance paths were made relative; game values are unchanged.
The original game file hashes are retained separately in the manifests.
Deployment manifests omit local machine paths and references to files not included here.
The app reads bundled files and does not refresh prices from stores.

## Run locally

Use Python 3.11 or 3.12. From this directory:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Upload this directory's contents to a GitHub repository, preserving subfolders and hidden files.
2. At https://share.streamlit.io/ choose Create app and select that repository.
3. Select the branch containing the code and main file `app.py`.
4. In Advanced settings choose Python 3.11 or 3.12 and deploy.

Keep `.streamlit/config.toml`, `views/`, `steam/` and `playstation/` in the repository.
No API keys or secrets are needed for this snapshot-based version.

## Validation

```bash
python -m unittest test_analytics test_comparison test_insights
```
