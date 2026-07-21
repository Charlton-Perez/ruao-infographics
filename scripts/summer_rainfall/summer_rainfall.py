"""
Cumulative summer rainfall — the driest summers on record vs 2026,
Reading University Atmospheric Observatory.

For each benchmark summer, a running (cumulative) total of daily rainfall from
1 June, day by day through to 31 August. The current year is overlaid,
stopping at today, so you can read off — at the same point in the season —
whether 2026 is tracking wetter or drier than these historically dry summers.

Benchmark years: the five driest summers on record by total Jun-Aug rainfall,
ranked dynamically from the data each run, plus 1976 added for its cultural
significance even though it doesn't rank in the top 5 by this measure (drier
years here are more about the *value* of rainfall totals than 1976's fame,
which rests more on heat and sunshine — see the hot_days_1976 infographic).

Run:  python summer_rainfall.py
Output: ../../docs/summer_rainfall/summer_rainfall.png
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
SEASON_DAYS = 92
HIGHLIGHT_YEAR = 1976     # added for cultural significance, not by rank
TOP_N_DRY = 5             # how many driest-ranked summers to show alongside 1976
MAX_MISSING = 10          # exclude a summer from ranking/plotting if missing more than this many days

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT = REPO_ROOT / "docs" / "summer_rainfall" / "summer_rainfall.png"
ASSETS = Path(__file__).resolve().parent / "assets"
OBS_URL = "https://research.reading.ac.uk/meteorology/atmospheric-observatory/"
CORNER_LOGO = "rdg_device.png"
CORNER_PX = 52

# ── Palette — blue throughout, as this is a rainfall story ────────────────────
INK, BG, SUB, MUTE, SPINE, GRID = "#2b2118", "#faf7f2", "#6a5c4c", "#9a8c7a", "#c9bfae", "#e3dccf"
CURRENT_COLOR = "#00b8d4"          # 2026 — bright cyan-blue, pops over the darker family
HIGHLIGHT_COLOR = "#3060a8"        # 1976 — mid royal blue, dashed to separate it from the ranked five
# The five driest (excluding 1976), dark -> light by rank (driest = darkest ink).
# Used for the plotted LINES, which can afford to be pale against the grid.
FIVE_PALETTE = ["#08306b", "#2166ac", "#4393c3", "#75aed4", "#c6dbef"]
# End-of-line LABEL text needs real contrast against the cream background — the
# two lightest line colours above are illegible as text, so their labels use a
# darker floor tone instead (still blue, just not washed out).
FIVE_PALETTE_LABEL = ["#08306b", "#2166ac", "#4393c3", "#3d6f96", "#4a6a8a"]


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


def cumulative_rain_series(df, year):
    """Cumulative total rainfall for 1 Jun-31 Aug of `year`, aligned to a full
    92-day calendar index. Missing days are treated as 0 mm contribution (a
    day with no reading can't be shown as rain, and excluding it entirely
    would break the running total) — has_data marks which days were actually
    observed, so the current year's trace can be truncated at the real
    latest observation rather than plateau-ing on into unmeasured days.
    Returns (day_of_summer array, cumulative array, has_data boolean array)."""
    idx = season_dates(year)
    sub = df[(df["date"] >= idx[0]) & (df["date"] <= idx[-1])].set_index("date")["RR"]
    sub = sub.reindex(idx)
    has_data = sub.notna().values
    cum = sub.fillna(0).cumsum()
    return np.arange(1, len(idx) + 1), cum.values, has_data


def build():
    df = load_daily()
    df["RR"] = pd.to_numeric(df["RR"], errors="coerce")
    current_year = int(df["year"].max())
    last_date = df["date"].max()

    # ── Rank summers by total Jun-Aug rainfall, driest first ──────────────────
    summer = df[df["month"].isin([SEASON_START[0], 7, SEASON_END[0]])]
    sg = summer.groupby("year").agg(total=("RR", "sum"), valid=("RR", "count"))
    complete = sg[sg["valid"] >= SEASON_DAYS - MAX_MISSING].sort_values("total")

    dry_years = list(complete.head(TOP_N_DRY).index)
    if HIGHLIGHT_YEAR not in dry_years and HIGHLIGHT_YEAR in complete.index:
        dry_years.append(HIGHLIGHT_YEAR)

    # ── Benchmark traces ───────────────────────────────────────────────────────
    benchmarks = []
    for yr in dry_years:
        days, cum, has_data = cumulative_rain_series(df, int(yr))
        benchmarks.append((int(yr), days, cum))

    # Assign the dark->light palette by rank (driest = darkest); the highlight
    # year keeps its own colour regardless of where it falls.
    others = [b for b in benchmarks if b[0] != HIGHLIGHT_YEAR]
    others.sort(key=lambda b: b[2][-1])
    colors, label_colors = {}, {}
    for (yr, _, _), c, lc in zip(others, FIVE_PALETTE, FIVE_PALETTE_LABEL):
        colors[yr] = c
        label_colors[yr] = lc
    if HIGHLIGHT_YEAR in [b[0] for b in benchmarks]:
        colors[HIGHLIGHT_YEAR] = HIGHLIGHT_COLOR
        label_colors[HIGHLIGHT_YEAR] = HIGHLIGHT_COLOR

    # ── Current year trace (truncated to the last day actually observed) ─────
    cur_days, cur_cum, cur_has_data = cumulative_rain_series(df, current_year)
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

    # End-of-line labels, decluttered: several benchmarks can finish within a
    # narrow band, so plain labels at their exact final value overlap. Sort by
    # final value and enforce a minimum vertical gap between adjacent labels,
    # with a short leader line back to the real endpoint whenever a label has
    # to be nudged away from it.
    MIN_GAP = 3.5
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
        if abs(ylabel - yend) > 0.3:
            ax.plot([xend + 0.3, lx - 0.4], [yend, ylabel], color=color, linewidth=0.8,
                    alpha=0.55, zorder=2)
        # A label's value can coincidentally land right on a gridline (e.g. a
        # round-number total on a round-number tick) and look struck through —
        # a BG-coloured box behind the text masks whatever grid/line is there,
        # independent of which values happen to collide.
        ax.text(lx, ylabel, f"{yr}  {yend:.0f} mm", va="center", fontsize=11.5,
                color=label_colors[yr], fontweight="bold", zorder=5,
                bbox=dict(facecolor=BG, edgecolor="none", pad=2.0, alpha=0.92))

    if len(cur_days):
        ax.plot(cur_days, cur_cum, color=CURRENT_COLOR, linewidth=3.0, zorder=6,
                solid_capstyle="round")
        ax.scatter([cur_days[-1]], [cur_cum[-1]], color=CURRENT_COLOR, s=45, zorder=7)
        ax.annotate(
            f"{current_year} so far\n{cur_cum[-1]:.0f} mm (to {last_date:%d %b})",
            xy=(cur_days[-1], cur_cum[-1]), xytext=(cur_days[-1] + 2, cur_cum[-1] + 6),
            fontsize=12, fontweight="bold", color=CURRENT_COLOR, va="center",
            arrowprops=dict(arrowstyle="-|>", color=CURRENT_COLOR, lw=1.3))

    # Month tick marks on the day-of-summer axis (Jun/Jul/Aug each start 30/31 days apart)
    month_starts = [1, 31, 61, 92]
    month_labels = ["1 Jun", "1 Jul", "1 Aug", "31 Aug"]
    ax.set_xticks(month_starts)
    ax.set_xticklabels(month_labels, fontsize=12.5, color=SUB)
    ax.set_xlim(1, 92 + 13)   # extra room on the right for end-of-line labels
    ax.set_ylabel("cumulative rainfall (mm)", fontsize=12.5, color=SUB)
    ax.grid(axis="y", color=GRID, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(axis="y", colors=SUB)

    # ── Header ───────────────────────────────────────────────────────────────
    head_ax = fig.add_axes([0.0, 0.84, 1.0, 0.16]); head_ax.axis("off")
    head_ax.set_xlim(0, 1); head_ax.set_ylim(0, 1)
    head_ax.text(0.06, 0.58, f"The driest summers on record — how does {current_year} compare?",
                 fontsize=22, fontweight="bold", color=INK)
    head_ax.text(0.06, 0.14,
                 "Cumulative rainfall, 1 June to today, against the five driest Jun–Aug summers on record plus 1976",
                 fontsize=13.5, color=SUB)
    place_corner_logo(head_ax)

    # ── Footer ───────────────────────────────────────────────────────────────
    fig.text(0.08, 0.045,
             f"Data collected by the University of Reading  ·  {OBS_URL}",
             fontsize=11, color=SUB)
    fig.text(0.08, 0.025,
             f"Generated {date.today():%d %b %Y}  ·  Daily record {coverage(df)}  ·  "
             f"Benchmark: driest {TOP_N_DRY} Jun–Aug summers by rainfall, plus 1976. "
             f"Missing days counted as 0 mm.",
             fontsize=10.5, color=MUTE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG)
    plt.close(fig)

    print(f"Wrote {OUT}")
    print(f"  Benchmarks used: {[b[0] for b in benchmarks]}")
    if len(cur_days):
        print(f"  {current_year} so far: {cur_cum[-1]:.1f} mm through day {cur_days[-1]} (to {last_date:%d %b})")
    if not (ASSETS / CORNER_LOGO).exists():
        print(f"  (logo not found: {CORNER_LOGO} — drop it in assets/ to include it)")


if __name__ == "__main__":
    build()
