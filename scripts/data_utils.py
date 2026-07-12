"""
Shared data-loading helpers for the RUAO infographic scripts.

Fetches the SAME daily CSV the ask_observatory web app serves, straight from
that repo on GitHub (raw file), so this repo never needs its own copy of the
data and always sees whatever the daily update workflow over there has landed.
"""

from pathlib import Path
import io
import urllib.request
import pandas as pd

RAW_CSV_URL = (
    "https://raw.githubusercontent.com/Charlton-Perez/ask_observatory/"
    "main/public/ruao_data.csv"
)

# Local fallback (e.g. for offline dev): set RUAO_CSV_PATH to a local file to
# skip the network fetch entirely.
import os
LOCAL_CSV_PATH = os.environ.get("RUAO_CSV_PATH")

_MISSING = {"x", "tr", ""}


def _fetch_csv_text() -> str:
    if LOCAL_CSV_PATH:
        return Path(LOCAL_CSV_PATH).read_text()
    with urllib.request.urlopen(RAW_CSV_URL, timeout=60) as resp:
        return resp.read().decode("utf-8")


def load_daily() -> pd.DataFrame:
    """Return the daily record as a tidy DataFrame with a real `date` column.

    Numeric weather fields are coerced to floats; 'x'/'tr' become NaN.
    """
    text = _fetch_csv_text()
    df = pd.read_csv(io.StringIO(text), skipinitialspace=True, low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    for col in ("year", "month", "day"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["year", "month", "day"]).copy()
    df[["year", "month", "day"]] = df[["year", "month", "day"]].astype(int)

    df["date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=df["day"]), errors="coerce"
    )
    df = df.dropna(subset=["date"])

    for col in ("Tx", "Tn", "RR", "sss"):
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.strip().replace(list(_MISSING), pd.NA),
                errors="coerce",
            )

    return df.sort_values("date").reset_index(drop=True)


def coverage(df: pd.DataFrame) -> str:
    """Human-readable coverage string for figure footers."""
    return f"{df['date'].min():%d %b %Y} to {df['date'].max():%d %b %Y}"
