# RUAO Infographics

Automatically-updated infographics built from the [Reading University
Atmospheric Observatory](https://research.reading.ac.uk/meteorology/atmospheric-observatory/)
daily weather record.

**View it live:** https://Charlton-Perez.github.io/ruao-infographics/

Each infographic has its own page and its own URL, e.g.:
https://Charlton-Perez.github.io/ruao-infographics/hot_days_1976/

The root page is just a landing page linking to each one with a short
description.

## Structure

Each infographic idea lives in its own subfolder — in `scripts/` for the
generator and in `docs/` for its page and images — so new ones can be added
without touching existing ones:

```
scripts/
  common/            shared helpers (data_utils.py — fetches the live CSV)
  hot_days_1976/      "2026 vs 1976" hot/dry/sunny comparison
    hot_days_30.py
    assets/           logo etc. used only by this infographic
docs/                  GitHub Pages site (served from here)
  index.html           root landing page — links to each infographic below
  assets/cc-by.png      shared CC-BY badge, used by the landing page
  hot_days_1976/
    index.html           this infographic's own page (its own URL)
    hot_days_30.png       combined figure, shown on the page
    panels/*.png          the six individual panels, download-only
    assets/cc-by.png       its own copy of the badge (self-contained page)
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
3. Copy `docs/hot_days_1976/index.html` as a starting point for
   `docs/<name>/index.html` (update the image/download filenames and the
   `<title>`) — this is what gives it its own URL,
   `.../ruao-infographics/<name>/`.
4. Add a `<a class="card" href="<name>/">` entry with a short description to
   the root `docs/index.html`.

The workflow (`.github/workflows/regenerate.yml`) automatically runs every
`.py` file it finds directly inside each `scripts/<name>/` folder (it skips
`scripts/common/`) — nothing needs to change there for the image generation;
only the two `index.html` edits above are manual.

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
