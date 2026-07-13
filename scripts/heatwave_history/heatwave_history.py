"""
A century of heatwaves at the Reading University Atmospheric Observatory.

A calendar heatmap: year on the x-axis, day of the extended summer (1 May at the
bottom, 30 Sep at the top) on the y-axis. Every day that falls within a heatwave
gets a square, coloured by that day's maximum temperature in 2 °C blocks from
yellow (28-30) to dark red (36 °C+). Non-heatwave days are left blank, so the
rare, clustered, and increasingly frequent heatwaves stand out on their own.

Heatwave = the UK Met Office definition for SE England / Reading: daily maximum
temperature ≥ 28 °C for at least three consecutive days.

Run:  python heatwave_history.py
Output: ../../docs/heatwave_history/heatwave_history.png
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
from matplotlib.patches import Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = [
    "Avenir Next", "Mukta", "Helvetica Neue", "Arial", "Liberation Sans", "DejaVu Sans",
]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
from data_utils import load_daily, coverage

# ── Parameters ────────────────────────────────────────────────────────────────
HW_THRESHOLD = 28.0       # Met Office SE England heatwave threshold (°C, daily max)
HW_MIN_DAYS = 3           # ... for at least this many consecutive days
SEASON_START = (5, 1)     # 1 May  → day 1 (bottom of the y-axis)
SEASON_END = (9, 30)      # 30 Sep → top
SEASON_DAYS = 153         # May 31 + Jun 30 + Jul 31 + Aug 31 + Sep 30

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT = REPO_ROOT / "docs" / "heatwave_history" / "heatwave_history.png"
ASSETS = Path(__file__).resolve().parent / "assets"
OBS_URL = "https://research.reading.ac.uk/meteorology/atmospheric-observatory/"
CORNER_LOGO = "rdg_device.png"
CORNER_PX = 56

# ── Palette ───────────────────────────────────────────────────────────────────
INK, BG, SUB, MUTE, SPINE, GRID = "#2b2118", "#faf7f2", "#6a5c4c", "#9a8c7a", "#c9bfae", "#e3dccf"
# 2 °C temperature blocks, yellow → dark red
BLOCKS = [
    (28, 30, "#ffd93d"),
    (30, 32, "#fcb130"),
    (32, 34, "#f57e29"),
    (34, 36, "#dd3c22"),
    (36, 999, "#8f1a0c"),
]
BLOCK_LABELS = ["28–30", "30–32", "32–34", "34–36", "36 °C+"]
# Bar chart of per-year counts: a muted brick red, deliberately OFF the
# yellow→dark-red temperature ramp so it can't be mistaken for a heat block.
BAR_COLOR = "#9c3f36"


def block_color(tx):
    for lo, hi, c in BLOCKS:
        if lo <= tx < hi:
            return c
    return BLOCKS[-1][2]


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


def build():
    df = load_daily()
    df["Tx"] = pd.to_numeric(df["Tx"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    # ── Identify heatwave days ────────────────────────────────────────────────
    # Runs of consecutive calendar days with Tx >= threshold; a run of >= min
    # days is a heatwave, and every day in it is a heatwave day. Gaps in the
    # record break a run.
    hot = df["Tx"] >= HW_THRESHOLD
    breaks = (df["date"].diff().dt.days != 1) | (hot != hot.shift())
    grp = breaks.cumsum()
    run_len = df.groupby(grp)["date"].transform("size")
    df["hwday"] = hot & (run_len >= HW_MIN_DAYS)

    hw = df[df["hwday"]].copy()
    hw["doy"] = (hw["date"] - pd.to_datetime(
        dict(year=hw["date"].dt.year, month=SEASON_START[0], day=SEASON_START[1]))).dt.days + 1
    hw = hw[(hw["doy"] >= 1) & (hw["doy"] <= SEASON_DAYS)]

    year_min = int(df["date"].dt.year.min())
    year_max = int(df["date"].dt.year.max())

    n_years = year_max - year_min + 1
    # Heatwave days per year — for the bar chart underneath the calendar.
    per_year = hw.groupby(hw["date"].dt.year).size().reindex(
        range(year_min, year_max + 1), fill_value=0)
    decades = [y for y in range(year_min - year_min % 10, year_max + 1, 10) if y >= year_min]

    # ── Figure: calendar heatmap (top) + per-year day-count bars (bottom) ──────
    fig = plt.figure(figsize=(13, 12.5), dpi=130)
    fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(2, 1, height_ratios=[3.3, 1.0], hspace=0.06,
                          left=0.075, right=0.935, top=0.845, bottom=0.085)
    ax = fig.add_subplot(gs[0])                 # calendar
    axb = fig.add_subplot(gs[1], sharex=ax)     # per-year bars
    ax.set_facecolor(BG); axb.set_facecolor(BG)

    # ── Calendar heatmap ──────────────────────────────────────────────────────
    # Faint season canvas so the (mostly empty) grid still reads as a calendar.
    ax.add_patch(Rectangle((year_min - 0.5, 0.5), n_years, SEASON_DAYS,
                           facecolor="#f1ece3", edgecolor="none", zorder=0))
    px, py = 0.12, 0.10   # small gaps so consecutive days read as distinct cells
    for _, r in hw.iterrows():
        yr, d = int(r["date"].year), int(r["doy"])
        ax.add_patch(Rectangle((yr - 0.5 + px / 2, d - 0.5 + py / 2), 1 - px, 1 - py,
                               facecolor=block_color(r["Tx"]), edgecolor="none", zorder=3))

    month_days = {1: "1 May", 32: "1 Jun", 62: "1 Jul", 93: "1 Aug", 124: "1 Sep", 153: "30 Sep"}
    for d in (32, 62, 93, 124):
        ax.axhline(d - 0.5, color=GRID, linewidth=0.8, zorder=1)
    for y in decades:
        ax.axvline(y - 0.5, color=GRID, linewidth=0.8, zorder=1)
    ax.set_yticks(list(month_days.keys()))
    ax.set_yticklabels(list(month_days.values()), fontsize=10, color=SUB)
    ax.set_xlim(year_min - 0.5, year_max + 0.5)
    ax.set_ylim(0.5, SEASON_DAYS + 0.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(axis="y", colors=SUB, length=0)
    ax.tick_params(axis="x", labelbottom=False, length=0)  # bars below carry the year axis

    # ── Per-year bar chart (shares the year axis) ─────────────────────────────
    axb.bar(per_year.index, per_year.values, width=0.8, color=BAR_COLOR,
            edgecolor="none", zorder=3)
    for y in decades:
        axb.axvline(y - 0.5, color=GRID, linewidth=0.8, zorder=1)
    axb.set_ylim(0, max(int(per_year.max() * 1.15) + 1, 4))
    axb.set_ylabel("heatwave days\nper year", fontsize=9.5, color=SUB)
    axb.set_xticks(decades)
    axb.set_xticklabels([str(y) for y in decades], fontsize=10, color=SUB)
    axb.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    axb.set_axisbelow(True)
    for s in ("top", "right", "left"):
        axb.spines[s].set_visible(False)
    axb.spines["bottom"].set_color(SPINE)
    axb.tick_params(colors=SUB, length=0)

    # ── Header (aligned to the plot's left/right margins) ─────────────────────
    head = fig.add_axes([0.075, 0.905, 0.86, 0.085]); head.axis("off")
    head.set_xlim(0, 1); head.set_ylim(0, 1)
    head.text(0.0, 0.55, "A century of heatwaves at Reading", fontsize=23,
              fontweight="bold", color=INK)
    head.text(0.0, 0.05,
              "Every heatwave day since records began — Met Office definition: daily maximum ≥ 28 °C for 3+ consecutive days",
              fontsize=12, color=SUB)
    place_corner_logo(head)

    # ── Legend (temperature blocks) — clear of the plot ───────────────────────
    leg = fig.add_axes([0.075, 0.862, 0.86, 0.03]); leg.axis("off")
    leg.set_xlim(0, 1); leg.set_ylim(0, 1)
    leg.text(0.0, 0.5, "Daily maximum (°C):", va="center", fontsize=10.5,
             color=SUB, fontweight="bold")
    x = 0.16
    for (lo, hi, c), label in zip(BLOCKS, BLOCK_LABELS):
        leg.add_patch(Rectangle((x, 0.15), 0.022, 0.7, facecolor=c, edgecolor=BG, linewidth=0.5))
        leg.text(x + 0.03, 0.5, label, va="center", fontsize=10, color=INK)
        x += 0.115

    # ── Footer ────────────────────────────────────────────────────────────────
    fig.text(0.075, 0.038,
             f"Data collected by the University of Reading  ·  {OBS_URL}",
             fontsize=9.5, color=SUB)
    fig.text(0.075, 0.020,
             f"Generated {date.today():%d %b %Y}  ·  Daily record {coverage(df)}  ·  "
             f"{year_max} shown to date. Each cell = one heatwave day.",
             fontsize=8.5, color=MUTE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG)
    plt.close(fig)

    print(f"Wrote {OUT}")
    print(f"  Heatwave days plotted: {len(hw)}  ({year_min}–{year_max})")
    by_decade = (hw["date"].dt.year // 10 * 10).value_counts().sort_index()
    print(f"  Busiest decade: {int(by_decade.idxmax())}s with {int(by_decade.max())} heatwave days")
    if not (ASSETS / CORNER_LOGO).exists():
        print(f"  (logo not found: {CORNER_LOGO} — drop it in assets/ to include it)")


if __name__ == "__main__":
    build()
