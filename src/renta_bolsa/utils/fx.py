from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import requests

from .pandas_transform import convert_to_numeric

ECB_BASE = "https://data-api.ecb.europa.eu/service/data"

@dataclass(frozen=True)
class FxConfig:
    cache_dir: Path = Path(".cache/renta_bolsa")

def _fetch_ecb_usd_per_eur(start: str, end: str) -> pd.DataFrame:
    # Serie diaria USD/EUR: EXR/D.USD.EUR.SP00.A
    url = f"{ECB_BASE}/EXR/D.USD.EUR.SP00.A"
    r = requests.get(url, params={"startPeriod": start, "endPeriod": end, "format": "csvdata"}, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(pd.io.common.StringIO(r.text))
    df = df.rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "usd_per_eur"})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["usd_per_eur"] = convert_to_numeric(df[["usd_per_eur"]])["usd_per_eur"]

    return df[["date", "usd_per_eur"]].dropna()

def load_fx_calendar(year: int, cfg: FxConfig = FxConfig(), refresh: bool = False) -> pd.Series:
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cfg.cache_dir / f"fx_usd_per_eur_{year}.csv"

    if cache_path.exists() and not refresh:
        fx_raw = pd.read_csv(cache_path)
        fx_raw["date"] = pd.to_datetime(fx_raw["date"]).dt.date
    else:
        start, end = f"{year}-01-01", f"{year}-12-31"
        fx_raw = _fetch_ecb_usd_per_eur(start, end)
        fx_raw.to_csv(cache_path, index=False)

    # Calendario diario con forward-fill (último día hábil anterior)
    start, end = f"{year}-01-01", f"{year}-12-31"
    idx = pd.date_range(start=start, end=end, freq="D").date
    s = fx_raw.set_index("date")["usd_per_eur"].reindex(idx).ffill()
    
    return s  # date -> usd_per_eur

def usd_to_eur(amount_usd: pd.Series, usd_per_eur: pd.Series) -> pd.Series:
    return amount_usd / usd_per_eur
