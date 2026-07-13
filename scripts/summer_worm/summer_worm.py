"""
"The worm" — 2026's summer progress against the hottest summers on record,
Reading University Atmospheric Observatory.

Cricket-worm style: for each benchmark summer, a running (cumulative) mean of
daily mean temperature (Tx+Tn)/2 from 1 June, day by day through to 31 August.
Early in the season the line is noisy; as more days accumulate it smooths out
and settles towards that summer's final seasonal mean. The current year is
overlaid, stopping at today, so you can see whether 2026 is tracking above or
below its rivals at the same point in the season.

Benchmark years: the five hottest summers on record by mean Jun–Aug daily
temperature (2025, 2018, 2022, 2006, 1947), plus 1976 added for its cultural
significance even though it ranks 6th on this particular measure.

Run:  python summer_worm.py
Output: ../../docs/summer_worm/summer_worm.png
"""

import sys
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = [
    "Avenir Next", "Mukta", "Helvetica Neue", "Arial", "Liberation Sans", "DejaVu Sans",
]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
from data_utils import load_daily, coverage

# ── Parameters ────────────────────────────────────────────────────────────────
SEASON_START = (6, 1)     # 1 June
SEASON_END = (8, 31)      # 31 August
BENCHMARK_YEARS = [2025, 2018, 2022, 2006, 1947, 1976]  # top 5 by mean JJA Tmean + 1976
HIGHLIGHT_YEAR = 1976     # added for cultural significance, not by rank
MAX_MISSING = 10          # exclude a benchmark year if it's missing more than this many days

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT = REPO_ROOT / "docs" / "summer_worm" / "summer_worm.png"
ASSETS = Path(__file__).resolve().parent / "assets"
OBS_URL = "https://research.reading.ac.uk/meteorology/atmospheric-observatory/"
CORNER_LOGO = "rdg_device.png"
CORNER_PX = 52

# ── Palette ───────────────────────────────────────────────────────────────────
INK, BG, SUB, MUTE, SPINE, GRID = "#2b2118", "#faf7f2", "#6a5c4c", "#9a8c7a", "#c9bfae", "#e3dccf"
CURRENT_COLOR = "#1a1a1a"          # 2026 — bold, near-black, stands out from the warm palette
HIGHLIGHT_COLOR = "#c1361a"        # 1976 — the cultural benchmark, distinct red
# The other five (2025, 2018, 2022, 2006, 1947), light → dark by rank (hottest = darkest)
FIVE_PALETTE = ["#f4c430", "#e8a23a", "#e8834a", "#b5651d", "#7a4a1e"]


def _load_rgba(path):
    raw = mpimg.imread(path)
    img = raw.astype(float)
    if np.issubdtype(raw.dtype, np.integer):
        img /= 255.0
    if img.ndim == 2:
        img = np.dstack([img, img, img])
    if img.shape[2] == 3:
        img = np.dstack([img, np.ones(img.shape[:2])])
    return img


def place_corner_logo(ax):
    lp = ASSETS / CORNER_LOGO
    if not lp.exists():
        return
    try:
        img = _load_rgba(lp)
    except Exception:
        return
    zoom = CORNER_PX / img.shape[0]
    ax.add_artist(AnnotationBbox(
        OffsetImage(img, zoom=zoom), (1.0, 0.5), xycoords="axes fraction",
        box_alignment=(1, 0.5), frameon=False))


def season_dates(year):
    start = pd.Timestamp(year=year, month=SEASON_START[0], day=SEASON_START[1])
    end = pd.Timestamp(year=year, month=SEASON_END[0], day=SEASON_END[1])
    return pd.date_range(start, end, freq="D")


def running_mean_series(df, year):
    """Cumulative mean of Tmean for 1 Jun-31 Aug of `year`, aligned to a full
    92-day calendar index (missing days become NaN; expanding().mean() skips
    them when computing each day's running average, but note it still emits
    a carried-forward value even on days with no input of their own — see
    `has_data` below for the mask of days actually observed).
    Returns (day_of_summer array, cum_mean array, has_data boolean array)."""
    idx = season_dates(year)
    sub = df[(df["date"] >= idx[0]) & (df["date"] <= idx[-1])].set_index("date")["Tmean"]
    sub = sub.reindex(idx)
    cum = sub.expanding().mean()
    return np.arange(1, len(idx) + 1), cum.values, sub.notna().values


def build():
    df = load_daily()
    df["Tx"] = pd.to_numeric(df["Tx"], errors="coerce")
    df["Tn"] = pd.to_numeric(df["Tn"], errors="coerce")
    df["Tmean"] = (df["Tx"] + df["Tn"]) / 2
    current_year = int(df["year"].max())
    last_date = df["date"].max()

    # ── Benchmark traces ───────────────────────────────────────────────────────
    benchmarks = []
    for yr in BENCHMARK_YEARS:
        days, cum, has_data = running_mean_series(df, yr)
        if has_data.sum() < len(days) - MAX_MISSING:
            continue
        benchmarks.append((yr, days, cum))

    # Rank the non-highlight years by final cumulative mean (hottest first) to
    # assign the light→dark palette; the highlight year keeps its own colour.
    others = [b for b in benchmarks if b[0] != HIGHLIGHT_YEAR]
    others.sort(key=lambda b: b[2][-1], reverse=True)
    colors = {}
    for (yr, _, _), c in zip(others, FIVE_PALETTE):
        colors[yr] = c
    if HIGHLIGHT_YEAR in [b[0] for b in benchmarks]:
        colors[HIGHLIGHT_YEAR] = HIGHLIGHT_COLOR

    # ── Current year trace (truncated to the last day actually observed —
    # expanding().mean() would otherwise carry the line flat into future days) ──
    cur_days, cur_cum, cur_has_data = running_mean_series(df, current_year)
    if cur_has_data.any():
        last_i = np.where(cur_has_data)[0].max()
        cur_days, cur_cum = cur_days[: last_i + 1], cur_cum[: last_i + 1]
    else:
        cur_days, cur_cum = cur_days[:0], cur_cum[:0]

    # ── Figure ──────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(13, 9), dpi=130)
    fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(1, 1, left=0.08, right=0.87, top=0.82, bottom=0.13)
    ax = fig.add_subplot(gs[0, 0])
    ax.set_facecolor(BG)

    for yr, days, cum in benchmarks:
        if yr == HIGHLIGHT_YEAR:
            continue
        ax.plot(days, cum, color=colors[yr], linewidth=1.8, alpha=0.9, zorder=3)

    if HIGHLIGHT_YEAR in colors:
        hy = next(b for b in benchmarks if b[0] == HIGHLIGHT_YEAR)
        ax.plot(hy[1], hy[2], color=colors[HIGHLIGHT_YEAR], linewidth=2.2,
                linestyle=(0, (6, 3)), alpha=0.95, zorder=4)

    # End-of-line labels, decluttered: the six benchmarks all finish within a
    # narrow band (~18-19°C), so plain labels at their exact final value
    # overlap. Sort by final value and enforce a minimum vertical gap between
    # adjacent labels, with a short leader line back to the line's real endpoint
    # whenever a label has to be nudged away from it.
    MIN_GAP = 0.55
    entries = sorted(
        ((yr, days[-1], cum[-1], colors[yr]) for yr, days, cum in benchmarks),
        key=lambda e: e[2], reverse=True,
    )
    label_ys, prev = [], None
    for _, _, yend, _ in entries:
        y = yend if prev is None else min(yend, prev - MIN_GAP)
        label_ys.append(y)
        prev = y
    for (yr, xend, yend, color), ylabel in zip(entries, label_ys):
        lx = xend + 1.2
        if abs(ylabel - yend) > 0.03:
            ax.plot([xend + 0.3, lx - 0.4], [yend, ylabel], color=color, linewidth=0.8,
                    alpha=0.55, zorder=2)
        ax.text(lx, ylabel, f"{yr}  {yend:.1f}°C", va="center", fontsize=11.5,
                color=color, fontweight="bold")

    if len(cur_days):
        ax.plot(cur_days, cur_cum, color=CURRENT_COLOR, linewidth=3.0, zorder=6,
                solid_capstyle="round")
        ax.scatter([cur_days[-1]], [cur_cum[-1]], color=CURRENT_COLOR, s=45, zorder=7)
        ax.annotate(
            f"{current_year} so far\n{cur_cum[-1]:.1f}°C (to {last_date:%d %b})",
            xy=(cur_days[-1], cur_cum[-1]), xytext=(cur_days[-1] + 2, cur_cum[-1] + 1.1),
            fontsize=12, fontweight="bold", color=CURRENT_COLOR, va="center",
            arrowprops=dict(arrowstyle="-|>", color=CURRENT_COLOR, lw=1.3))

    # Month tick marks on the day-of-summer axis (Jun/Jul/Aug each start 30/31 days apart)
    month_starts = [1, 31, 61, 92]
    month_labels = ["1 Jun", "1 Jul", "1 Aug", "31 Aug"]
    ax.set_xticks(month_starts)
    ax.set_xticklabels(month_labels, fontsize=12.5, color=SUB)
    ax.set_xlim(1, 92 + 13)   # extra room on the right for end-of-line labels
    ax.set_ylabel("running average daily temperature (°C)", fontsize=12.5, color=SUB)
    ax.grid(axis="y", color=GRID, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(axis="y", colors=SUB)

    # ── Header ───────────────────────────────────────────────────────────────
    head_ax = fig.add_axes([0.0, 0.84, 1.0, 0.16]); head_ax.axis("off")
    head_ax.set_xlim(0, 1); head_ax.set_ylim(0, 1)
    head_ax.text(0.06, 0.58, f"How does {current_year} compare to the hottest summers on record?",
                 fontsize=22, fontweight="bold", color=INK)
    head_ax.text(0.06, 0.14,
                 "Running average of daily mean temperature (Tx+Tn)/2, 1 June to today — like a cricket run-rate worm",
                 fontsize=13.5, color=SUB)
    place_corner_logo(head_ax)

    # ── Footer ───────────────────────────────────────────────────────────────
    fig.text(0.08, 0.045,
             f"Data collected by the University of Reading  ·  {OBS_URL}",
             fontsize=11, color=SUB)
    fig.text(0.08, 0.025,
             f"Generated {date.today():%d %b %Y}  ·  Daily record {coverage(df)}  ·  "
             f"Benchmark summers: top 5 by mean Jun–Aug temperature, plus 1976.",
             fontsize=10.5, color=MUTE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG)
    plt.close(fig)

    print(f"Wrote {OUT}")
    print(f"  Benchmarks used: {[b[0] for b in benchmarks]}")
    if len(cur_days):
        print(f"  {current_year} so far: {cur_cum[-1]:.2f}°C through day {cur_days[-1]} (to {last_date:%d %b})")
    if not (ASSETS / CORNER_LOGO).exists():
        print(f"  (logo not found: {CORNER_LOGO} — drop it in assets/ to include it)")


if __name__ == "__main__":
    build()
