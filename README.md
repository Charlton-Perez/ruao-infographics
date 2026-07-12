# RUAO Infographics

Automatically-updated infographics built from the [Reading University
Atmospheric Observatory](https://research.reading.ac.uk/meteorology/atmospheric-observatory/)
daily weather record — comparing 2026 against the iconic summer of 1976 on
heat, dryness and sunshine.

**View it live:** https://Charlton-Perez.github.io/ruao-infographics/

## How it works

- `scripts/hot_days_30.py` fetches the daily CSV directly from the
  [`ask_observatory`](https://github.com/Charlton-Perez/ask_observatory) repo
  (`public/ruao_data.csv`, raw file) — no copy of the data lives here.
- It regenerates the combined comparison (`docs/hot_days_30.png`) and six
  individual panels (`docs/panels/*.png`), then a GitHub Pages site
  (`docs/index.html`) displays them.
- A scheduled GitHub Action (`.github/workflows/regenerate.yml`) runs daily at
  12:20 UTC — 20 minutes after `ask_observatory`'s own data-fetch workflow —
  regenerates the figures, and commits them if anything changed. It can also
  be triggered manually from the Actions tab.

## Run locally

```bash
cd scripts
pip install -r requirements.txt
python hot_days_30.py
```

Output goes to `../docs/`. Set `RUAO_CSV_PATH=/path/to/ruao_data.csv` to use a
local CSV instead of fetching over the network (useful offline).

## License

Data collected by the University of Reading. Figures are provided as is, with
no warranty, for informational purposes during beta testing.
