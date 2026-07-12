# RUAO Infographics

Automatically-updated infographics built from the [Reading University
Atmospheric Observatory](https://research.reading.ac.uk/meteorology/atmospheric-observatory/)
daily weather record.

**View it live:** https://Charlton-Perez.github.io/ruao-infographics/

## Structure

Each infographic idea lives in its own subfolder, so new ones can be added
without touching existing ones:

```
scripts/
  common/            shared helpers (data_utils.py — fetches the live CSV)
  hot_days_1976/      "2026 vs 1976" hot/dry/sunny comparison
    hot_days_30.py
    assets/           logo etc. used only by this infographic
docs/                  GitHub Pages site (served from here)
  index.html           the page — shows the six panels + a download picker
  hot_days_1976/
    hot_days_30.png    combined figure (download-only, not shown on the page)
    panels/*.png       the six individual panels (shown on the page)
```

`scripts/common/data_utils.py` fetches `ruao_data.csv` straight from the
[`ask_observatory`](https://github.com/Charlton-Perez/ask_observatory) repo's
raw file on every run — no copy of the data lives here, so figures are always
as current as that repo's daily update.

## Adding a new infographic

1. Create `scripts/<name>/your_script.py`. Import the shared loader with:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
   from data_utils import load_daily, coverage
   ```
2. Write output to `docs/<name>/...` (compute the path via
   `Path(__file__).resolve().parent.parent.parent / "docs" / "<name>"`).
3. Add a section to `docs/index.html` (and an entry in the downloads
   `<select>` if you want it downloadable).

The workflow (`.github/workflows/regenerate.yml`) automatically runs every
`.py` file it finds directly inside each `scripts/<name>/` folder (it skips
`scripts/common/`) — nothing needs to change there.

## Automatic regeneration

A scheduled GitHub Action runs daily at **12:20 UTC** — 20 minutes after
`ask_observatory`'s own data-fetch workflow, so it reliably picks up that
day's new observation — regenerates every infographic, and commits the
results if anything changed. It also runs on any push to `scripts/`, and can
be triggered manually from the Actions tab.

## Run locally

```bash
cd scripts/hot_days_1976
pip install -r ../requirements.txt
python hot_days_30.py
```

Set `RUAO_CSV_PATH=/path/to/ruao_data.csv` to use a local CSV instead of
fetching over the network (useful offline).

## License

Data collected by the University of Reading. Figures are provided as is, with
no warranty, for informational purposes during beta testing.
