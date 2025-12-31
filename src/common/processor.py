from __future__ import annotations
from pathlib import Path
import pandas as pd

from common.fx import ECBExchangeService, usd_to_eur
from model_100.utils.dictionary import (
    DIVIDEND_ACTIONS,
    TAX_ACTIONS,
    GAIN_LOSS_COLUMNS,
)
from .schwab import SchwabParser


class TaxReportEngine:
    """Engine to calculate tax reports for Spanish residents with foreign investments."""

    def __init__(self, year: int, out_dir: str | Path, refresh_fx: bool = False):
        self.year = year
        self.out_dir = Path(out_dir)
        self.refresh_fx = refresh_fx
        self.fx_service = ECBExchangeService()
        self.rates = self.fx_service.get_rates_for_year(year, refresh=refresh_fx)

    def process_dividends(self, transactions_csv: str) -> pd.DataFrame:
        """Processes dividend and tax transactions, converting to EUR."""
        tx = SchwabParser.load_transactions(transactions_csv)

        # Filter by year
        start_date = pd.to_datetime(f"{self.year}-01-01")
        end_date = pd.to_datetime(f"{self.year}-12-31")
        tx = tx[tx["date"].between(start_date, end_date)].copy()

        # Apply FX
        tx["usd_per_eur"] = tx["date"].map(self.rates)
        tx["amount_eur"] = usd_to_eur(tx["Amount"], tx["usd_per_eur"])

        # Group by symbol
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

        dividend_summary = pd.concat([div, tax], axis=1).fillna(0.0)
        dividend_summary["dividend_net_eur"] = (
            dividend_summary["dividend_gross_eur"] + dividend_summary["foreign_tax_eur"]
        )
        return dividend_summary

    def process_realized_gains(self, realized_csv: str) -> pd.Series:
        """Processes realized gains/losses, converting to EUR."""
        rg = SchwabParser.load_realized(realized_csv)

        # Filter by year
        start_date = pd.to_datetime(f"{self.year}-01-01")
        end_date = pd.to_datetime(f"{self.year}-12-31")
        rg = rg[rg["closed_date"].between(start_date, end_date)].copy()

        # Apply FX
        rg["usd_per_eur"] = rg["closed_date"].map(self.rates)

        # Identify gainloss column
        gl_col = next((c for c in GAIN_LOSS_COLUMNS if c in rg.columns), None)
        if not gl_col:
            raise ValueError(
                f"No gain/loss column found. Available: {rg.columns.tolist()}"
            )

        rg["gainloss_eur"] = usd_to_eur(rg[gl_col], rg["usd_per_eur"])
        return (
            rg.groupby("Symbol")["gainloss_eur"].sum().rename("realized_gainloss_eur")
        )

    def process_positions(self, positions_csv: str) -> pd.DataFrame:
        """Processes positions, converting to EUR."""
        pos = SchwabParser.load_positions(positions_csv)

        usd_per_eur = self.fx_service.get_usd_per_eur_on_dec31(
            self.year, refresh=self.refresh_fx
        )

        pos["value_eur"] = usd_to_eur(pos["Market Value"], usd_per_eur)

        return pos

    def generate_report_720(self, positions_csv: str) -> str:
        """Generates the final report for the 720."""
        self.out_dir.mkdir(parents=True, exist_ok=True)

        positions_df = self.process_positions(positions_csv)

        # Filter out invalid tickers (e.g. "Account Total", "Cash & Cash Investments")
        # Assuming valid tickers are short (<= 5 chars)
        positions_df = positions_df[positions_df["Ticker"].astype(str).str.len() <= 5]

        posiciones_symbol = positions_df[
            ["Ticker", "Description", "Qty", "value_eur"]
        ].sort_values("Ticker")

        modelo_path = self.out_dir / f"modelo_720_{self.year}.csv"
        posiciones_symbol.round(2).to_csv(modelo_path, index=False)

        return str(modelo_path)

    def generate_reports(
        self, transactions_csv: str, realized_csv: str
    ) -> tuple[str, str]:
        """Main method to orchestrate report generation."""
        self.out_dir.mkdir(parents=True, exist_ok=True)

        dividend_by_symbol = self.process_dividends(transactions_csv)
        gl_by_symbol = self.process_realized_gains(realized_csv)

        # Totals
        resumen_anual = pd.DataFrame(
            [
                {
                    "year": self.year,
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

        # Detailed breakdown
        desglose_symbol = (
            dividend_by_symbol.join(gl_by_symbol, how="outer")
            .fillna(0.0)
            .reset_index()
            .rename(columns={"Symbol": "symbol"})
            .sort_values("symbol")
        )

        # Paths
        res_path = self.out_dir / f"resumen_anual_{self.year}.csv"
        des_path = self.out_dir / f"desglose_symbol_{self.year}.csv"

        # Round and save
        resumen_anual.round(2).to_csv(res_path, index=False)
        desglose_symbol.round(2).to_csv(des_path, index=False)

        return str(res_path), str(des_path)
