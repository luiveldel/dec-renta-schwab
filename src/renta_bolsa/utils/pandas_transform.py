from typing import List
import pandas as pd


def remove_dollar_comma(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove dollar signs and commas from all string columns in the dataframe.
    """
    return df.astype(str).replace({"\$": "", ",": ""}, regex=True)


def convert_to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts all string columns in the dataframe to numeric.
    If conversion fails, NaN is assigned.
    """
    return df.apply(pd.to_numeric, errors="coerce")


def fill_na(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fills NaN values in the dataframe with empty strings.
    """
    return df.fillna("").astype(str)


def get_columns(df: pd.DataFrame) -> List[str]:
    """
    Returns columns as a list of strings.
    """
    return [c.strip() for c in df.columns]


def convert_to_datetime(
    df: pd.DataFrame, date_format: str = "%m/%d/%Y"
) -> pd.DataFrame:
    """
    Converts all string columns in the dataframe to datetime.
    If conversion fails, NaT is assigned.
    """
    return df.apply(lambda x: pd.to_datetime(x, format=date_format, errors="coerce"))
