from __future__ import annotations
from pathlib import Path
import pandas as pd

from renta_bolsa.utils.fx import load_fx_calendar, usd_to_eur
from renta_bolsa.utils.dictionary import (
    DIVIDEND_ACTIONS,
    TAX_ACTIONS,
    GAIN_LOSS_COLUMNS,
)
from .schwab import load_transactions, load_realized


def build_reports(
    transactions_csv: str,
    realized_csv: str,
    year: int,
    out_dir: str,
    refresh_fx: bool = False,
):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    fx = load_fx_calendar(year, refresh=refresh_fx)

    # --- Dividendos / impuestos ---
    tx = load_transactions(transactions_csv)
    tx = tx[
        tx["date"].between(
            pd.to_datetime(f"{year}-01-01"), pd.to_datetime(f"{year}-12-31")
        )
    ].copy()
    tx["usd_per_eur"] = tx["date"].map(fx)
    tx["amount_eur"] = usd_to_eur(tx["Amount"], tx["usd_per_eur"])

    div = (
        tx[tx["Action"].isin(DIVIDEND_ACTIONS)]
        .groupby("Symbol", dropna=False)["amount_eur"]
        .sum()
        .rename("dividend_gross_eur")
    )
    tax = (
        tx[tx["Action"].isin(TAX_ACTIONS)]
        .groupby("Symbol", dropna=False)["amount_eur"]
        .sum()
        .rename("foreign_tax_eur")
    )

    dividend_by_symbol = pd.concat([div, tax], axis=1).fillna(0.0)
    dividend_by_symbol["dividend_net_eur"] = (
        dividend_by_symbol["dividend_gross_eur"] + dividend_by_symbol["foreign_tax_eur"]
    )

    # --- Realized gain/loss ---
    rg = load_realized(realized_csv)
    rg = rg[
        rg["closed_date"].between(
            pd.to_datetime(f"{year}-01-01"), pd.to_datetime(f"{year}-12-31")
        )
    ].copy()
    rg["usd_per_eur"] = rg["closed_date"].map(fx)

    # Find the gain/loss column - try multiple names (prioritize simple Gain/Loss)
    gl_col = None
    for col_name in GAIN_LOSS_COLUMNS:
        if col_name in rg.columns:
            gl_col = col_name
            break

    if gl_col is None:
        raise ValueError(
            f"No gain/loss column found. Available columns: {rg.columns.tolist()}"
        )

    rg["gainloss_eur"] = usd_to_eur(rg[gl_col], rg["usd_per_eur"])

    gl_by_symbol = (
        rg.groupby("Symbol")["gainloss_eur"].sum().rename("realized_gainloss_eur")
    )

    # --- Totales anuales ---
    resumen_anual = pd.DataFrame(
        [
            {
                "year": year,
                "Dividendos_brutos_EUR": float(
                    dividend_by_symbol["dividend_gross_eur"].sum()
                ),
                "Impuestos_origen_EUR": float(
                    dividend_by_symbol["foreign_tax_eur"].sum()
                ),
                "Dividendos_netos_EUR": float(
                    dividend_by_symbol["dividend_net_eur"].sum()
                ),
                "Ganancia_perdida_realizada_EUR": float(gl_by_symbol.sum()),
            }
        ]
    )

    # --- Desglose por símbolo ---
    desglose_symbol = (
        dividend_by_symbol.join(gl_by_symbol, how="outer")
        .fillna(0.0)
        .reset_index()
        .rename(columns={"Symbol": "symbol"})
        .sort_values("symbol")
    )

    resumen_path = out / f"resumen_anual_{year}.csv"
    desglose_path = out / f"desglose_symbol_{year}.csv"

    # Round numeric columns to 2 decimals
    resumen_anual_rounded = resumen_anual.copy()
    for col in resumen_anual_rounded.columns:
        if col != "year":
            resumen_anual_rounded[col] = resumen_anual_rounded[col].round(2)

    desglose_symbol_rounded = desglose_symbol.copy()
    for col in desglose_symbol_rounded.columns:
        if col != "symbol":
            desglose_symbol_rounded[col] = desglose_symbol_rounded[col].round(2)

    resumen_anual_rounded.to_csv(resumen_path, index=False)
    desglose_symbol_rounded.to_csv(desglose_path, index=False)

    return str(resumen_path), str(desglose_path)
