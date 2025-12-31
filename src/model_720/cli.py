from __future__ import annotations

from pathlib import Path
import typer

from common.io import resolve_positions_inputs
from common.report import generate_report_720

app = typer.Typer(
    add_completion=False,
    help="Asistente para preparar el Modelo 720 (bienes/valores en el extranjero).",
)

@app.command("run")
def run(
    data_dir: Path = typer.Option(
        Path("data"),
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Carpeta con el fichero de entrada (posiciones).",
    ),
    out_dir: Path = typer.Option(Path("out"), help="Carpeta de salida."),
    year: int | None = typer.Option(None, help="Año fiscal (si no se indica, se infiere del filename)."),
    refresh_fx: bool = typer.Option(False, "--refresh-fx", help="Forzar re-descarga del FX del BCE."),
    pattern_positions: str = typer.Option(
        "Individual-Positions*.csv",
        help="Patrón del CSV de posiciones a 31/12 (ej: Schwab Positions export).",
    ),
):
    """
    Genera un borrador (CSV) para valores/acciones del Modelo 720, valorando a 31/12.
    """
    inputs = resolve_positions_inputs(
        data_dir=str(data_dir),
        pattern_positions=pattern_positions,
        year=year,
    )

    positions_path = generate_report_720(
        positions_csv=str(inputs.positions_csv),
        year=inputs.year,
        out_dir=str(out_dir),
        refresh_fx=refresh_fx,
    )

    typer.echo(positions_path)
