from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

DATE_YYYY = re.compile(r"(20\d{2})")

@dataclass(frozen=True)
class DataInputs:
    transactions_csv: Path
    realized_csv: Path
    year: int

def infer_year_from_filename(path: Path) -> int:
    m = DATE_YYYY.search(path.name)
    if not m:
        raise ValueError(f"No encuentro el `year` en el filename: {path.name}")
    return int(m.group(1))

def pick_single(glob_results: list[Path], label: str) -> Path:
    if len(glob_results) == 0:
        raise FileNotFoundError(f"No encuentro fichero para {label}")
    if len(glob_results) > 1:
        # Si hay varios, coger el más reciente por nombre (suele contener timestamp)
        glob_results = sorted(glob_results, key=lambda p: p.name)
        return glob_results[-1]
    return glob_results[0]

def resolve_inputs(
    data_dir: str,
    pattern_transactions: str = "Individual_*_Transactions_*.csv",
    pattern_realized: str = "*_GainLoss_Realized_Details_*.csv",
    year: int | None = None
) -> DataInputs:
    d = Path(data_dir)
    tx = pick_single(list(d.glob(pattern_transactions)), "transactions (compras y ventas de acciones)")
    rg = pick_single(list(d.glob(pattern_realized)), "realized (dividendos)")

    y_tx = infer_year_from_filename(tx)
    y_rg = infer_year_from_filename(rg)

    inferred = y_tx
    if y_tx != y_rg:
        raise ValueError(f"Años distintos en filenames: tx={y_tx}, realized={y_rg}. Usa --year.")
    if year is not None:
        inferred = year

    return DataInputs(tx, rg, inferred)
