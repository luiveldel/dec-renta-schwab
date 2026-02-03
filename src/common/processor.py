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

    def _normalize_country_code(self, country: str) -> str:
        if not country:
            return ""
        value = str(country).strip()
        if len(value) == 2:
            return value.upper()
        mapping = {
            "United States": "US",
            "United States of America": "US",
            "USA": "US",
        }
        return mapping.get(value, "")

    def _fetch_yfinance_metadata(self, tickers: list[str]) -> pd.DataFrame:
        try:
            import yfinance as yf
        except Exception:
            return pd.DataFrame(
                columns=[
                    "Ticker",
                    "ISIN",
                    "Domicilio Fiscal",
                    "Poblacion",
                    "Pais Dom Fiscal",
                ]
            )

        rows = []
        for ticker in tickers:
            ticker_obj = yf.Ticker(ticker)
            isin = ""
            info = {}
            try:
                if hasattr(ticker_obj, "get_isin"):
                    isin = ticker_obj.get_isin() or ""
            except Exception:
                isin = ""

            if not isin:
                try:
                    info = ticker_obj.get_info()
                except Exception:
                    info = {}
                isin = info.get("isin", "") or ""

            if not isin:
                try:
                    info = ticker_obj.info
                except Exception:
                    info = info or {}
                isin = info.get("isin", "") or ""

            address1 = info.get("address1", "") or ""
            address2 = info.get("address2", "") or ""
            city = info.get("city", "") or ""
            state = info.get("state", "") or ""
            zip_code = info.get("zip", "") or ""
            country = info.get("country", "") or ""
            domicilio_parts = [p for p in [address1, address2] if p]
            domicilio = ", ".join(domicilio_parts)
            for part in [city, state, zip_code, country]:
                if part:
                    domicilio = f"{domicilio}, {part}" if domicilio else part

            rows.append(
                {
                    "Ticker": ticker,
                    "ISIN": isin,
                    "Domicilio Fiscal": domicilio,
                    "Poblacion": city,
                    "Pais Dom Fiscal": self._normalize_country_code(country),
                }
            )

        return pd.DataFrame(rows)

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

        repo_root = Path(__file__).resolve().parents[2]
        metadata_path = repo_root / "data" / "ticker_metadata.csv"
        metadata_df = pd.DataFrame(
            columns=["Ticker", "ISIN", "Domicilio Fiscal", "Poblacion", "Pais Dom Fiscal"]
        )
        if metadata_path.exists():
            metadata_df = pd.read_csv(metadata_path)
            metadata_df.columns = [c.strip() for c in metadata_df.columns]
            rename_map = {}
            for col in metadata_df.columns:
                col_key = col.strip().lower()
                if col_key == "ticker":
                    rename_map[col] = "Ticker"
                elif col_key == "isin":
                    rename_map[col] = "ISIN"
                elif col_key == "domicilio fiscal" or col_key == "domicilio_fiscal":
                    rename_map[col] = "Domicilio Fiscal"
                elif col_key == "poblacion":
                    rename_map[col] = "Poblacion"
                elif col_key in {"pais dom fiscal", "pais_dom_fiscal", "pais dom. fiscal"}:
                    rename_map[col] = "Pais Dom Fiscal"
            if rename_map:
                metadata_df = metadata_df.rename(columns=rename_map)

        for col in ["Ticker", "ISIN", "Domicilio Fiscal", "Poblacion", "Pais Dom Fiscal"]:
            if col not in metadata_df.columns:
                metadata_df[col] = ""
        metadata_df = metadata_df[
            ["Ticker", "ISIN", "Domicilio Fiscal", "Poblacion", "Pais Dom Fiscal"]
        ]
        metadata_df = metadata_df.fillna("").astype(str)
        metadata_df["ISIN"] = (
            metadata_df["ISIN"].replace({"-": "", "N/A": "", "NA": ""}).astype(str)
        )

        required_cols = ["ISIN", "Domicilio Fiscal", "Poblacion", "Pais Dom Fiscal"]
        missing_tickers = []
        for ticker in posiciones_symbol["Ticker"].astype(str).tolist():
            row = metadata_df[metadata_df["Ticker"] == ticker]
            if row.empty or any(row[col].iloc[0].strip() == "" for col in required_cols):
                missing_tickers.append(ticker)

        fetch_targets = sorted(set(missing_tickers))
        if fetch_targets:
            fetched_df = self._fetch_yfinance_metadata(fetch_targets)
            if not fetched_df.empty:
                fetched_df = fetched_df.fillna("").astype(str)
                metadata_df = metadata_df.set_index("Ticker")
                fetched_df = fetched_df.set_index("Ticker")
                for col in required_cols:
                    if col in fetched_df.columns:
                        metadata_df[col] = metadata_df[col].mask(
                            metadata_df[col].str.strip() == "", fetched_df[col]
                        )
                for ticker in fetched_df.index:
                    if ticker not in metadata_df.index:
                        metadata_df.loc[ticker] = fetched_df.loc[ticker]
                metadata_df = metadata_df.reset_index()

        metadata_df["ISIN"] = (
            metadata_df["ISIN"].replace({"-": "", "N/A": "", "NA": ""}).astype(str)
        )
        metadata_df.to_csv(metadata_path, index=False)

        enriched = posiciones_symbol.merge(metadata_df, on="Ticker", how="left")
        enriched = enriched.fillna("")

        pais_dom_fiscal = enriched["Pais Dom Fiscal"].replace("", "US").fillna("US")

        modelo_720 = pd.DataFrame(
            {
                "Clave de condicion del declarante": 1,
                "Clave de tipo de bien o derecho": "V",
                "Subclave de bien o derecho": 1,
                "Identificacion de valores": enriched["ISIN"],
                "Descripcion": enriched["Description"],
                "Codigo de pais (custodio)": "US",
                "Origen del bien o derecho": "A",
                "Numero de valores": enriched["Qty"],
                "Valoracion uno": enriched["value_eur"],
                "Porcentaje de participacion": 100,
                "Domicilio fiscal": enriched["Domicilio Fiscal"],
                "Poblacion": enriched["Poblacion"],
                "Pais, dom. fiscal": pais_dom_fiscal,
                "Fecha Venta (si procede)": "",
            }
        )

        modelo_path = self.out_dir / f"modelo_720_{self.year}.csv"
        modelo_720.round(2).to_csv(modelo_path, index=False)

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
