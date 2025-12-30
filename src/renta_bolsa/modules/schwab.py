from __future__ import annotations
import pandas as pd

from renta_bolsa.utils.dictionary import NUMERIC_COLUMNS
from renta_bolsa.utils.pandas_transform import (
    remove_dollar_comma,
    convert_to_numeric,
    convert_to_datetime,
    fill_na,
    get_columns,
)


def load_transactions(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = get_columns(df)

    df["date"] = convert_to_datetime(df[["Date"]])["Date"]
    df["Amount"] = remove_dollar_comma(df[["Amount"]])["Amount"]
    df["Amount"] = convert_to_numeric(df[["Amount"]])["Amount"]
    df["Symbol"] = fill_na(df[["Symbol"]])["Symbol"]
    df["Action"] = fill_na(df[["Action"]])["Action"]

    return df


def load_realized(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=1)
    df.columns = get_columns(df)
    df["closed_date"] = convert_to_datetime(df[["Closed Date"]])["Closed Date"]

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = remove_dollar_comma(df[[col]])[col]
            df[col] = convert_to_numeric(df[[col]])[col]

    df["Symbol"] = fill_na(df[["Symbol"]])["Symbol"]

    return df
