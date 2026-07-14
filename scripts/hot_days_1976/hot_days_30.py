"""
Infographic: the hot & dry summer story at the Reading University Atmospheric
Observatory, with 1976 as the benchmark. 2x2 layout.

           HOT (30 C)                         DRY (rain)
  top:  30 C+ days per decade        avg dry days per summer, per decade
  bot:  years ranked, one square     driest summers ranked, one square
        = one 30 C+ day              = one rain day (fewest = driest)

Both columns carry the same two ideas: a per-decade climate signal on top and
a per-year ranking below, with 1976 highlighted and the current (partial) year
shown in grey.

Run:  python hot_days_30.py
Output: ../../docs/hot_days_1976/hot_days_30.png (+ panels/*.png), served by GitHub Pages.

This is one infographic among possibly several in this repo — see scripts/common/
for the shared data loader and scripts/<name>/ for each infographic's own folder.
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
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# Corporate typeface: the University of Reading uses Effra (a humanist geometric
# sans, commercial). We approximate its feel with the closest available font,
# falling back to whatever the runner has — Arial is the university's own
# declared fallback, DejaVu Sans ships with every matplotlib install (incl. CI).
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = [
    "Avenir Next", "Mukta", "Helvetica Neue", "Arial", "Liberation Sans", "DejaVu Sans",
]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
from data_utils import load_daily, coverage

# ── Analysis parameters ───────────────────────────────────────────────────────
HOT_THRESHOLD = 30.0
RAIN_DAY_MM = 1.0                 # a "rain day" is >= 1 mm; below that is a dry day
DRY_MONTHS = [6, 7, 8]            # meteorological summer — the window where 1976 leads
DRY_LABEL = "Jun–Aug"
DRY_WINDOW_DAYS = 92
MAX_MISSING = 12                  # ranking: exclude summers missing more than this
MIN_VALID_DECADE = 60             # decade signal: min valid summer days to include a year
SUN_BRIGHT_H = 12.0               # a "very sunny day": >= 12 h of bright sunshine
SUN_MONTHS = [6, 7, 8]            # meteorological summer (sunshine recorded since 1956)
TOP_N_HOT = 14
TOP_N_DRY = 13
TOP_N_SUN = 13
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT = REPO_ROOT / "docs" / "hot_days_1976" / "hot_days_30.png"
PRORATA_OUT = REPO_ROOT / "docs" / "hot_days_1976" / "pro_rata_summer.png"
ASSETS = Path(__file__).resolve().parent / "assets"
OBS_URL = "https://research.reading.ac.uk/meteorology/atmospheric-observatory/"

# ── Palette ───────────────────────────────────────────────────────────────────
INK      = "#2b2118"
BG       = "#faf7f2"
GRID     = "#e3dccf"
MUTE     = "#9a8c7a"
SUB      = "#6a5c4c"
SPINE    = "#c9bfae"
RECORD   = "#c1361a"   # 1976 benchmark in the HOT panels — red
DRY_REC  = "#6b4a2e"   # 1976 benchmark in the DRY panels — dark brown (parched earth)
CURRENT  = "#8a8f96"   # the current, partial year — neutral grey
HOT_BAR  = "#e8834a"
HOT_HI   = "#c1361a"
HOT_SQ   = "#f0a868"
DRY_BAR  = "#5b8fb0"
DRY_HI   = "#2f6d8f"
DRY_SQ   = "#5b8fb0"
SUN_BAR  = "#f0d68a"   # pale gold — other years / decade bars
SUN_HI   = "#c8890a"   # amber — sunniest decade / column header
SUN_SQ   = "#f0d68a"
SUN_REC_FILL = "#ffcf1a"  # 1976 squares/chip in the SUNNY panel — bright yellow (pops)
SUN_REC  = "#9a6a00"   # 1976 line/label/tick — dark amber (readable on cream)


# Expected logo file (drop into assets/):
# rdg_device.png is rasterised from "Rdg Device Outline.eps" (transparent, high-res) via:
#   gs -dSAFER -dBATCH -dNOPAUSE -dEPSCrop -sDEVICE=pngalpha -r1200 \
#      -sOutputFile=rdg_device.png "Rdg Device Outline.eps"
CORNER_LOGO = "rdg_device.png"           # University of Reading logo — top-right of the header
CORNER_PX = 66                           # rendered height of the corner logo, in px


def _load_rgba(path, key_white=False, thresh=0.90):
    """Read an image as float RGBA. If key_white, make near-white pixels transparent
    (for black-on-white line art with no alpha channel)."""
    raw = mpimg.imread(path)
    img = raw.astype(float)
    if np.issubdtype(raw.dtype, np.integer):
        img /= 255.0
    if img.ndim == 2:                       # greyscale → RGB
        img = np.dstack([img, img, img])
    if img.shape[2] == 3:                   # add opaque alpha
        img = np.dstack([img, np.ones(img.shape[:2])])
    if key_white:
        white = (img[..., 0] > thresh) & (img[..., 1] > thresh) & (img[..., 2] > thresh)
        img[white, 3] = 0.0
    return img


def place_corner_logo(head_ax):
    """The named University of Reading centenary lockup, top-right of the header."""
    lp = ASSETS / CORNER_LOGO
    if not lp.exists():
        return
    try:
        img = _load_rgba(lp)
    except Exception:
        return
    zoom = CORNER_PX / img.shape[0]
    head_ax.add_artist(AnnotationBbox(
        OffsetImage(img, zoom=zoom), (1.0, 0.5), xycoords="axes fraction",
        box_alignment=(1, 0.5), frameon=False))


def style_axes(ax):
    ax.set_facecolor(BG)
    ax.grid(axis="y", color=GRID, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(colors=SUB, labelsize=10)


def decade_bars(ax, series, title, ylabel, base_c, hi_c):
    decades = list(series.index)
    values = [round(float(v), 1) for v in series.values]
    hi = decades[int(values.index(max(values)))]
    colors = [hi_c if d == hi else base_c for d in decades]
    bars = ax.bar([f"{d}s" for d in decades], values, color=colors, width=0.78, zorder=3)
    for b, v in zip(bars, values):
        if v > 0:
            txt = f"{v:.0f}"
            ax.text(b.get_x() + b.get_width() / 2, v + max(values) * 0.02, txt,
                    ha="center", va="bottom", fontsize=12, fontweight="bold", color=INK)
    # Headroom above the tallest bar so the value labels don't crowd the title.
    ax.set_ylim(0, max(values) * 1.12)
    ax.set_title(title, loc="left", fontsize=17, fontweight="bold", color=INK, pad=26)
    ax.set_ylabel(ylabel, fontsize=12.5, color=SUB)
    style_axes(ax)
    return hi


def square_rank(ax, order, title, ylabel, sq_color, record_year, current_year,
                record_count, record_label, legend, annotate=None, rec_c=RECORD, rec_fill=None):
    """order: list of (year, count). Draw stacked unit squares per year.
    rec_fill lets the record year's squares differ from its label/line colour rec_c
    (e.g. bright-yellow fill with a dark, readable label)."""
    if rec_fill is None:
        rec_fill = rec_c
    years = [y for y, _ in order]
    counts = [c for _, c in order]
    gap, w = 0.16, 0.72
    for xi, (yr, cnt) in enumerate(order):
        fc = rec_fill if yr == record_year else (CURRENT if yr == current_year else sq_color)
        for j in range(cnt):
            ax.add_patch(Rectangle((xi - w / 2, j + gap / 2), w, 1 - gap,
                                   facecolor=fc, edgecolor=BG, linewidth=0.7, zorder=3))
        ax.text(xi, cnt + 0.4, str(cnt), ha="center", va="bottom", fontsize=12, fontweight="bold",
                color=rec_c if yr == record_year else (CURRENT if yr == current_year else INK))
    ymax = max(counts) + 4
    ax.axhline(record_count, color=rec_c, linestyle=(0, (5, 4)), linewidth=1.3, zorder=2)
    ax.text(len(years) - 0.55, record_count, record_label, ha="right", va="center",
            fontsize=12.5, fontweight="bold", color=rec_c, zorder=6,
            bbox=dict(facecolor=BG, edgecolor="none", pad=1.5, alpha=0.9))
    ax.set_xlim(-0.7, len(years) - 0.3)
    ax.set_ylim(0, ymax)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha="right", fontsize=12, color=SUB)
    for lbl, yr in zip(ax.get_xticklabels(), years):
        if yr == record_year: lbl.set_color(rec_c); lbl.set_fontweight("bold")
        elif yr == current_year: lbl.set_color(CURRENT); lbl.set_fontweight("bold")
    ax.set_title(title, loc="left", fontsize=17, fontweight="bold", color=INK, pad=13)
    ax.set_ylabel(ylabel, fontsize=12.5, color=SUB)
    style_axes(ax)
    # legend chips along the top — when the current year has become the record
    # holder, its coloured "record" chip already stands for it, so drop the grey
    # "so far" chip rather than list the same year twice.
    if record_year == current_year:
        legend = [(c, lbl) for c, lbl in legend if c != CURRENT]
    step = len(years) / 3.2
    for i, (c, label) in enumerate(legend):
        ax.add_patch(Rectangle((0.05 + i * step, ymax - 1.4), 0.45, 0.7,
                               facecolor=c, edgecolor=BG, zorder=5))
        ax.text(0.62 + i * step, ymax - 1.05, label, va="center", fontsize=11, color=INK)
    if annotate:
        annotate(ax, years, counts, ymax)


def build():
    df = load_daily()
    df["RR"] = pd.to_numeric(df["RR"], errors="coerce")
    df["sss"] = pd.to_numeric(df["sss"], errors="coerce")
    start_year = int(df["year"].min())
    current_year = int(df["year"].max())
    open_decade = start_year // 10 * 10

    # ── HOT: decade totals + year ranking ─────────────────────────────────────
    hot = df[df["Tx"] >= HOT_THRESHOLD].copy()
    hot_by_year = hot.groupby("year").size()
    hot_record_year = int(hot_by_year.idxmax())
    hot_record = int(hot_by_year.max())
    hot_current = int(hot_by_year.get(current_year, 0))

    hot["decade"] = (hot["year"] // 10) * 10
    hot_dec = hot.groupby("decade").size().reindex(
        range(open_decade, current_year // 10 * 10 + 10, 10), fill_value=0)
    if start_year % 10 != 0:
        hot_dec = hot_dec[hot_dec.index > open_decade]

    hot_top = hot_by_year.sort_values(ascending=False).head(TOP_N_HOT)
    if current_year not in hot_top.index and hot_current > 0:
        hot_top = pd.concat([hot_top.iloc[:-1], hot_by_year.loc[[current_year]]])
    hot_order = list(hot_top.sort_values(ascending=False).items())
    hot_order = [(int(y), int(c)) for y, c in hot_order]

    # ── DRY: per-decade avg dry days + driest-summer ranking ──────────────────
    summer = df[df["month"].isin(DRY_MONTHS)]
    sg = summer.groupby("year").agg(
        rain=("RR", lambda s: int((s >= RAIN_DAY_MM).sum())),
        valid=("RR", "count"))
    # Decade signal: scale observed dry days to a full 92-day season for fairness.
    dec_src = sg[sg["valid"] >= MIN_VALID_DECADE].copy()
    dec_src["dry92"] = (dec_src["valid"] - dec_src["rain"]) / dec_src["valid"] * DRY_WINDOW_DAYS
    dec_src["decade"] = (dec_src.index // 10) * 10
    dry_dec = dec_src.groupby("decade")["dry92"].mean()
    if start_year % 10 != 0:
        dry_dec = dry_dec[dry_dec.index > open_decade]

    # Ranking: driest complete summers by fewest rain days, + current partial year.
    complete = sg[sg["valid"] >= DRY_WINDOW_DAYS - MAX_MISSING]
    driest = complete.sort_values("rain").head(TOP_N_DRY)
    dry_record_year = int(driest.index[0])
    dry_record = int(driest["rain"].iloc[0])
    cur_summer = df[(df["year"] == current_year) & (df["month"].isin(DRY_MONTHS))]
    cur_rain = int((cur_summer["RR"] >= RAIN_DAY_MM).sum())
    dry_order = [(int(y), int(c)) for y, c in driest["rain"].items()] + [(current_year, cur_rain)]
    dry_order.sort(key=lambda t: t[1])

    # ── SUNNY: per-decade summer sunshine + sunniest-summer ranking ───────────
    # Sunshine (sss) has been recorded since 1956 — a shorter record than temp/rain.
    sun = df[df["month"].isin(SUN_MONTHS)]
    ssg = sun.groupby("year").agg(
        bright=("sss", lambda s: int((s >= SUN_BRIGHT_H).sum())),
        total=("sss", "sum"), valid=("sss", "count"))
    sun_start = int(ssg[ssg["valid"] >= MIN_VALID_DECADE].index.min())
    # Decade signal: mean summer sunshine hours, scaled to a full 92-day season.
    sun_src = ssg[ssg["valid"] >= MIN_VALID_DECADE].copy()
    sun_src["h92"] = sun_src["total"] / sun_src["valid"] * DRY_WINDOW_DAYS
    sun_src["decade"] = (sun_src.index // 10) * 10
    sun_dec = sun_src.groupby("decade")["h92"].mean()
    if sun_start % 10 != 0:                       # drop the incomplete opening decade (1950s)
        sun_dec = sun_dec[sun_dec.index > sun_start // 10 * 10]
    # Match the HOT/DRY decade axis: same decades, empty bars before sunshine began.
    sun_dec = sun_dec.reindex(hot_dec.index, fill_value=0)

    # Ranking: sunniest complete summers by most very-sunny days, + current partial year.
    sun_complete = ssg[ssg["valid"] >= DRY_WINDOW_DAYS - MAX_MISSING]
    sun_ranked = sun_complete["bright"].sort_values(ascending=False).head(TOP_N_SUN)
    cur_bright = int((cur_summer["sss"] >= SUN_BRIGHT_H).sum())
    if current_year not in sun_ranked.index:
        sun_ranked = pd.concat([sun_ranked.iloc[:-1], pd.Series({current_year: cur_bright})])
    sun_order = [(int(y), int(c)) for y, c in sun_ranked.sort_values(ascending=False).items()]
    sun_record_year, sun_record = sun_order[0]

    # ── Pro-rata projections: 2026's rate-so-far scaled up to a full 92-day
    #    summer, for a second pair of figures ("what if this pace continued").
    #    Kept fully separate from the actual to-date rankings above.
    days_dry_so_far = int(cur_summer["RR"].notna().sum())
    proj_rain = round(cur_rain / days_dry_so_far * DRY_WINDOW_DAYS) if days_dry_so_far else cur_rain
    dry_order_proj = [(y, c) for y, c in dry_order if y != current_year] + [(current_year, proj_rain)]
    dry_order_proj.sort(key=lambda t: t[1])

    days_sun_so_far = int(cur_summer["sss"].notna().sum())
    proj_bright = round(cur_bright / days_sun_so_far * DRY_WINDOW_DAYS) if days_sun_so_far else cur_bright
    sun_order_proj = [(y, c) for y, c in sun_order if y != current_year] + [(current_year, proj_bright)]
    sun_order_proj.sort(key=lambda t: t[1], reverse=True)

    driest_decade = int(dry_dec.idxmax())
    sunny_decade  = int(sun_dec.idxmax())

    # ── Current-year annotations for each ranking ─────────────────────────────
    # Each places its label in the empty region beside/above the current-year
    # column and lifts clear of neighbouring bars, so nothing overlaps as the
    # 2026 tallies grow through the season.
    def _side_max(counts, lo, hi):
        return max(counts[max(0, lo):hi], default=0)

    def hot_annot(ax, years, counts, ymax):
        if current_year in years and hot_current < hot_record:
            xi = years.index(current_year); need = hot_record - hot_current + 1
            xr = xi + 0.32   # vertical gap arrow, just right of the grey bar
            ax.add_patch(FancyArrowPatch((xr, hot_current + 0.3), (xr, hot_record - 0.8),
                         arrowstyle="-|>", mutation_scale=14, color=CURRENT, linewidth=1.5, zorder=4))
            mid = (hot_current + hot_record) / 2
            # Descending ranking → the right side is the empty, lower side; fall
            # back to the left only if the current year is near the right edge.
            if xi <= len(counts) - 3:
                tx, ha, clear = xr + 0.3, "left", _side_max(counts, xi + 1, xi + 5)
            else:
                tx, ha, clear = xr - 0.5, "right", _side_max(counts, xi - 4, xi)
            ty = min(max(mid, clear + 2.0), hot_record - 0.5)
            ax.text(tx, ty, f"{need} more\nto break ’76", ha=ha, va="center",
                    fontsize=12, color="#5a5f66", fontweight="bold")

    def dry_annot(ax, years, counts, ymax):
        if current_year in years and cur_rain > dry_record:
            xi = years.index(current_year)
            clear = _side_max(counts, xi + 1, xi + 4)          # rising columns to the right
            ty = min(max(cur_rain + 5.0, clear + 2.0), ymax - 1.5)
            # aim at the top of the 2026 column itself (not the neighbour), clear of its count label
            ax.annotate("already wetter\nthan ’76", xy=(xi + 0.05, cur_rain - 0.6), xytext=(xi + 0.95, ty),
                        ha="left", va="center", fontsize=12, color="#5a5f66", fontweight="bold",
                        arrowprops=dict(arrowstyle="-|>", color=CURRENT, lw=1.4))

    def sun_annot(ax, years, counts, ymax):
        if current_year in years:
            xi = years.index(current_year)
            # 2026 is the lowest/right-most column; lift the label clear of the
            # tall neighbours on its left and anchor it near the right edge.
            clear = _side_max(counts, xi - 4, xi)
            ty = min(max(cur_bright + (ymax - cur_bright) * 0.45, clear + 2.0), ymax - 2.0)
            ax.annotate("far short\nof ’76", xy=(xi, cur_bright + 0.3), xytext=(xi + 0.4, ty),
                        ha="right", va="center", fontsize=12, color="#5a5f66", fontweight="bold",
                        arrowprops=dict(arrowstyle="-|>", color=CURRENT, lw=1.4))

    # Both projection annotations cap their label below ymax-2.6 — clear of the
    # legend row (which occupies roughly [ymax-1.7, ymax-0.7]) — since the
    # projected value sits much higher than the "so far" count and can otherwise
    # land right in the legend's vertical band.
    def dry_annot_proj(ax, years, counts, ymax):
        # The projected value is usually the wettest of all (so pushed to the far
        # right of the ranking) — label to its LEFT, never to the right, so it
        # can't overflow the axes into the neighbouring subplot.
        if current_year in years and proj_rain > dry_record:
            xi = years.index(current_year)
            clear = _side_max(counts, max(0, xi - 4), xi)
            ty = min(max(proj_rain + 3.0, clear + 2.0), ymax - 2.6)
            ax.annotate("still wetter\nthan ’76", xy=(xi - 0.05, proj_rain - 0.6), xytext=(xi - 0.95, ty),
                        ha="right", va="center", fontsize=12, color="#5a5f66", fontweight="bold",
                        arrowprops=dict(arrowstyle="-|>", color=CURRENT, lw=1.4))

    def sun_annot_proj(ax, years, counts, ymax):
        if current_year in years:
            xi = years.index(current_year)
            # The 1976-record dashed line spans the full panel width at y=sun_record,
            # so the label must sit clearly above it (and below the legend row at
            # ymax-1.4), not at some offset from the bar that might land on the line.
            safe_lo, safe_hi = sun_record + 0.6, ymax - 1.9
            ty = (safe_lo + safe_hi) / 2 if safe_hi > safe_lo else ymax - 3.5
            ax.annotate("still short of ’76", xy=(xi, proj_bright + 1.3), xytext=(xi + 0.8, ty),
                        ha="right", va="center", fontsize=11.5, color="#5a5f66", fontweight="bold",
                        arrowprops=dict(arrowstyle="-|>", color=CURRENT, lw=1.4))

    # ── The six panels, each a draw(ax) closure so they can go into the combined
    #    figure OR be rendered on their own ──────────────────────────────────────
    def draw_hot_rank(ax):
        square_rank(ax, hot_order, "Years ranked by 30°C+ days", "each square = one 30°C+ day",
                    HOT_SQ, hot_record_year, current_year, hot_record,
                    f"{hot_record_year} record: {hot_record}",
                    [(RECORD, f"{hot_record_year} ({hot_record})"),
                     (CURRENT, f"{current_year} so far ({hot_current})"),
                     (HOT_SQ, "other years")], annotate=hot_annot)

    def draw_dry_rank(ax):
        square_rank(ax, dry_order, f"Driest summers ranked by fewest rain days ({DRY_LABEL})",
                    f"each square = one rain day (≥ {RAIN_DAY_MM:g} mm)",
                    DRY_SQ, dry_record_year, current_year, dry_record,
                    f"{dry_record_year} record: {dry_record}",
                    [(DRY_REC, f"{dry_record_year} ({dry_record})"),
                     (CURRENT, f"{current_year} so far ({cur_rain})"),
                     (DRY_SQ, "other years")], annotate=dry_annot, rec_c=DRY_REC)

    def draw_sun_rank(ax):
        square_rank(ax, sun_order, f"Sunniest summers ranked by very sunny days ({DRY_LABEL})",
                    f"each square = one day ≥ {SUN_BRIGHT_H:g} h of sunshine",
                    SUN_SQ, sun_record_year, current_year, sun_record,
                    f"{sun_record_year} record: {sun_record}",
                    [(SUN_REC_FILL, f"{sun_record_year} ({sun_record})"),
                     (CURRENT, f"{current_year} so far ({cur_bright})"),
                     (SUN_SQ, "other years")], annotate=sun_annot, rec_c=SUN_REC, rec_fill=SUN_REC_FILL)

    def draw_dry_rank_proj(ax):
        square_rank(ax, dry_order_proj, f"Driest summers ranked by fewest rain days ({DRY_LABEL})",
                    f"each square = one rain day (≥ {RAIN_DAY_MM:g} mm)",
                    DRY_SQ, dry_record_year, current_year, dry_record,
                    f"{dry_record_year} record: {dry_record}",
                    [(DRY_REC, f"{dry_record_year} ({dry_record})"),
                     (CURRENT, f"{current_year} projected ({proj_rain})"),
                     (DRY_SQ, "other years")], annotate=dry_annot_proj, rec_c=DRY_REC)

    def draw_sun_rank_proj(ax):
        square_rank(ax, sun_order_proj, f"Sunniest summers ranked by very sunny days ({DRY_LABEL})",
                    f"each square = one day ≥ {SUN_BRIGHT_H:g} h of sunshine",
                    SUN_SQ, sun_record_year, current_year, sun_record,
                    f"{sun_record_year} record: {sun_record}",
                    [(SUN_REC_FILL, f"{sun_record_year} ({sun_record})"),
                     (CURRENT, f"{current_year} projected ({proj_bright})"),
                     (SUN_SQ, "other years")], annotate=sun_annot_proj, rec_c=SUN_REC, rec_fill=SUN_REC_FILL)

    def draw_hot_dec(ax):
        decade_bars(ax, hot_dec, "30°C+ days per decade", "days per decade", HOT_BAR, HOT_HI)
        ax.text(0, -0.16, f"Incomplete {open_decade}s omitted; the {current_year // 10 * 10}s still in progress.",
                transform=ax.transAxes, fontsize=11, color=MUTE, va="top")

    def draw_dry_dec(ax):
        decade_bars(ax, dry_dec, f"Average dry days per summer, per decade ({DRY_LABEL})",
                    "dry days per summer", DRY_BAR, DRY_HI)
        ax.text(0, -0.16,
                f"Dry day = < {RAIN_DAY_MM:g} mm; scaled to a {DRY_WINDOW_DAYS}-day summer. Driest decade: the {driest_decade}s.",
                transform=ax.transAxes, fontsize=11, color=MUTE, va="top")

    def draw_sun_dec(ax):
        decade_bars(ax, sun_dec, f"Average summer sunshine hours, per decade ({DRY_LABEL})",
                    "sunshine hours per summer", SUN_BAR, SUN_HI)
        ax.text(0, -0.16,
                f"Bright sunshine, scaled to a {DRY_WINDOW_DAYS}-day summer; recorded since {sun_start}. "
                f"Sunniest decade: the {sunny_decade}s.",
                transform=ax.transAxes, fontsize=11, color=MUTE, va="top")

    # Ordered: rankings (top row) then decades (bottom row). label/col drive the
    # HOT/DRY/SUNNY header on the combined figure only.
    RANKINGS = [("hot_ranking", "HOT", HOT_HI, draw_hot_rank),
                ("dry_ranking", "DRY", DRY_HI, draw_dry_rank),
                ("sunny_ranking", "SUNNY", SUN_HI, draw_sun_rank)]
    DECADES  = [("hot_decade", "HOT", HOT_HI, draw_hot_dec),
                ("dry_decade", "DRY", DRY_HI, draw_dry_dec),
                ("sunny_decade", "SUNNY", SUN_HI, draw_sun_dec)]

    # ── Combined six-panel figure ─────────────────────────────────────────────
    fig = plt.figure(figsize=(24, 13.5), dpi=120)
    fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(3, 3, height_ratios=[0.7, 4.2, 2.3], hspace=0.62, wspace=0.14,
                          left=0.045, right=0.975, top=0.965, bottom=0.12)

    head = fig.add_subplot(gs[0, :]); head.axis("off")
    head.text(0, 0.74, "2026 vs 1976 — a hot, dry, sunny summer?", fontsize=33, fontweight="bold", color=INK)
    head.text(0, 0.30,
              "Reading University Atmospheric Observatory — the summer of ’76 as the benchmark",
              fontsize=16, color=SUB)
    head.text(0, 0.00, f"Daily record {coverage(df)}  ·  sunshine recorded since {sun_start}",
              fontsize=12.5, color=MUTE)
    place_corner_logo(head)

    rank_axes = []
    for col, (key, label, colr, draw) in enumerate(RANKINGS):
        ax = fig.add_subplot(gs[1, col]); draw(ax); rank_axes.append((ax, label, colr))
    for col, (key, label, colr, draw) in enumerate(DECADES):
        draw(fig.add_subplot(gs[2, col]))

    # Column headers — HOT / DRY / SUNNY above their ranking columns
    for ax, label, colr in rank_axes:
        p = ax.get_position()
        cx = (p.x0 + p.x1) / 2
        fig.text(cx, p.y1 + 0.050, label, ha="center", va="bottom",
                 fontsize=23, fontweight="bold", color=colr, family="sans-serif")
        fig.add_artist(plt.Line2D([p.x0, p.x1], [p.y1 + 0.045, p.y1 + 0.045],
                                  color=colr, linewidth=2.2, alpha=0.5))

    foot = fig.text(0.06, 0.028,
                    f"Data collected by the University of Reading  ·  {OBS_URL}", fontsize=12, color=SUB)
    foot.set_url(OBS_URL)
    fig.text(0.06, 0.013,
             f"Generated {date.today():%d %b %Y}  ·  fewest rain days uses {DRY_LABEL}; {current_year} is a partial summer "
             f"(to {df['date'].max():%d %b}) so its rain-day count will still rise.",
             fontsize=11, color=MUTE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG)
    plt.close(fig)

    # ── Each panel on its own (no overall title; cropped tight) ────────────────
    pdir = OUT.parent / "panels"
    pdir.mkdir(parents=True, exist_ok=True)
    for key, label, colr, draw in RANKINGS + DECADES:
        size = (9, 5.2) if key.endswith("decade") else (9, 7.4)
        pf, pax = plt.subplots(figsize=size, dpi=130)
        pf.patch.set_facecolor(BG)
        draw(pax)
        pf.savefig(pdir / f"{key}.png", facecolor=BG, bbox_inches="tight", pad_inches=0.28)
        plt.close(pf)

    # ── Pro-rata figure: same two rankings, but 2026 scaled from its rate-so-far
    #    up to a full 92-day summer — "what if this pace continued all season".
    #    Kept as a separate figure/story from the to-date six-panel above.
    PRORATA = [("dry_ranking_prorata", DRY_HI, draw_dry_rank_proj),
               ("sunny_ranking_prorata", SUN_HI, draw_sun_rank_proj)]

    figp = plt.figure(figsize=(16, 8.4), dpi=120)
    figp.patch.set_facecolor(BG)
    gsp = figp.add_gridspec(2, 2, height_ratios=[0.85, 4.2], hspace=0.55, wspace=0.16,
                            left=0.06, right=0.965, top=0.90, bottom=0.14)
    headp = figp.add_subplot(gsp[0, :]); headp.axis("off")
    headp.text(0, 0.62, "Scaling 2026 up to a full summer", fontsize=25, fontweight="bold", color=INK)
    headp.text(0, 0.10,
               f"If 2026's Jun–Aug rate so far ({days_dry_so_far} days observed) held for the full "
               f"{DRY_WINDOW_DAYS}-day summer — same rankings, 2026 replaced with its projected pace",
               fontsize=13, color=SUB)

    for col, (key, colr, draw) in enumerate(PRORATA):
        ax = figp.add_subplot(gsp[1, col]); draw(ax)

    footp = figp.text(0.06, 0.038,
                      f"Data collected by the University of Reading  ·  {OBS_URL}", fontsize=11, color=SUB)
    footp.set_url(OBS_URL)
    figp.text(0.06, 0.018,
             f"Generated {date.today():%d %b %Y}  ·  projection = 2026's rate to {df['date'].max():%d %b} "
             f"scaled linearly to a {DRY_WINDOW_DAYS}-day summer; not a forecast.",
             fontsize=10.5, color=MUTE)

    PRORATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    figp.savefig(PRORATA_OUT, facecolor=BG)
    plt.close(figp)

    for key, colr, draw in PRORATA:
        pf, pax = plt.subplots(figsize=(9, 7.4), dpi=130)
        pf.patch.set_facecolor(BG)
        draw(pax)
        pf.savefig(pdir / f"{key}.png", facecolor=BG, bbox_inches="tight", pad_inches=0.28)
        plt.close(pf)

    print(f"Wrote {OUT}")
    print(f"  + 6 separate panels → {pdir.relative_to(OUT.parent.parent)}/")
    print(f"  Hot record : {hot_record_year} ({hot_record}); {current_year} so far {hot_current}")
    print(f"  Driest summer ({DRY_LABEL}): {dry_record_year} ({dry_record} rain days); "
          f"{current_year} so far {cur_rain} — {'already past' if cur_rain >= dry_record else 'below'} 1976")
    print(f"  Sunniest summer ({DRY_LABEL}): {sun_record_year} ({sun_record} days ≥{SUN_BRIGHT_H:g}h); "
          f"{current_year} so far {cur_bright}")
    if not (ASSETS / CORNER_LOGO).exists():
        print(f"  (logo not found: {CORNER_LOGO} — drop it in assets/ to include it)")


if __name__ == "__main__":
    build()
