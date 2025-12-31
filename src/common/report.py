from __future__ import annotations
from common.processor import TaxReportEngine


def build_reports(
    transactions_csv: str,
    realized_csv: str,
    year: int,
    out_dir: str,
    refresh_fx: bool = False,
):
    """Wrapper function to maintain backward compatibility."""
    engine = TaxReportEngine(year=year, out_dir=out_dir, refresh_fx=refresh_fx)
    return engine.generate_reports(transactions_csv, realized_csv)

def generate_report_720(
    positions_csv: str,
    year: int,
    out_dir: str,
    refresh_fx: bool = False,
):
    engine = TaxReportEngine(year=year, out_dir=out_dir, refresh_fx=refresh_fx)
    return engine.generate_report_720(positions_csv)
