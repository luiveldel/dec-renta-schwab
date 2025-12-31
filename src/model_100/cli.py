from __future__ import annotations

from pathlib import Path
import typer

from common.io import resolve_inputs
from common.report import build_reports

app = typer.Typer(
    add_completion=False,
    help="Generador de informes de renta para bolsa extranjera (Schwab)."
)


@app.command("run")
def run(
    data_dir: Path = typer.Option(
        Path("data"),
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Carpeta con los CSV de Schwab.",
    ),
    out_dir: Path = typer.Option(Path("out"), help="Carpeta de salida."),
    year: int | None = typer.Option(
        None, help="Año fiscal (si no se indica, se infiere del filename)."
    ),
    refresh_fx: bool = typer.Option(
        False, "--refresh-fx", help="Forzar re-descarga del FX del BCE."
    ),
    pattern_transactions: str = typer.Option(
        "Individual_*_Transactions_*.csv",
        help="Patrón del CSV de transacciones/dividendos.",
    ),
    pattern_realized: str = typer.Option(
        "*_GainLoss_Realized_Details_*.csv",
        help="Patrón del CSV de plusvalías realizadas.",
    ),
):
    inputs = resolve_inputs(
        data_dir=str(data_dir),
        pattern_transactions=pattern_transactions,
        pattern_realized=pattern_realized,
        year=year,
    )

    resumen_path, desglose_path = build_reports(
        transactions_csv=str(inputs.transactions_csv),
        realized_csv=str(inputs.realized_csv),
        year=inputs.year,
        out_dir=str(out_dir),
        refresh_fx=refresh_fx,
    )

    typer.echo(resumen_path)
    typer.echo(desglose_path)
