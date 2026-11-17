from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd


_MONTH_ABBREVIATIONS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _parse_date(value: Any) -> date | None:
    if pd.isna(value):
        return None
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return pd.Timestamp(value).date()
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = pd.to_datetime(value.strip(), dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).date()


def _format_date(value: date) -> str:
    return f"{value.day:02d}-{_MONTH_ABBREVIATIONS[value.month - 1]}-{value.year % 100:02d}"


def _one_year_expiry(value: date) -> date:
    """Return the day before the same calendar date next year (e.g. 15-Mar-23 -> 14-Mar-24)."""
    try:
        next_year_same_day = value.replace(year=value.year + 1)
    except ValueError:
        # 29-Feb inception: next year's equivalent start is 01-Mar, so expiry is 28-Feb.
        next_year_same_day = date(value.year + 1, 3, 1)
    return next_year_same_day - timedelta(days=1)


def apply_inception_expiry_rules(
    source_df: pd.DataFrame,
    inception_column: str,
    expiry_column: str | None,
    *,
    format_dates: bool,
    align_expiry: bool,
) -> tuple[pd.DataFrame, pd.Series, int, int]:
    """Apply optional formatting and anniversary alignment to an inception/expiry pair."""
    result = source_df.copy()
    changed = pd.Series(False, index=source_df.index, dtype=bool)
    parsed_inception = source_df[inception_column].map(_parse_date)
    parsed_expiry = (
        source_df[expiry_column].map(_parse_date)
        if expiry_column is not None
        else None
    )
    invalid_inception_count = int(parsed_inception.isna().sum())
    invalid_expiry_count = (
        int(parsed_expiry.isna().sum())
        if parsed_expiry is not None
        else 0
    )

    inception_values = source_df[inception_column].copy()
    expiry_values = (
        source_df[expiry_column].copy()
        if expiry_column is not None
        else None
    )

    for index, inception_date in parsed_inception.items():
        if inception_date is not None:
            inception_value = _format_date(inception_date) if format_dates else inception_values.at[index]
            if format_dates and inception_values.at[index] != inception_value:
                changed.at[index] = True
                inception_values.at[index] = inception_value

            if align_expiry and expiry_column is not None:
                anniversary = _one_year_expiry(inception_date)
                expiry_value = _format_date(anniversary) if format_dates else anniversary
                if expiry_values is not None:
                    current_expiry = expiry_values.at[index]
                    expiry_date = parsed_expiry.at[index] if parsed_expiry is not None else None
                    if expiry_date != anniversary:
                        changed.at[index] = True
                        expiry_values.at[index] = expiry_value
                    elif format_dates and current_expiry != expiry_value:
                        changed.at[index] = True
                        expiry_values.at[index] = expiry_value

        if format_dates and expiry_column is not None and not align_expiry:
            expiry_date = parsed_expiry.at[index] if parsed_expiry is not None else None
            if expiry_date is not None:
                expiry_value = _format_date(expiry_date)
                if expiry_values is not None and expiry_values.at[index] != expiry_value:
                    changed.at[index] = True
                    expiry_values.at[index] = expiry_value

    result[inception_column] = inception_values
    if expiry_column is not None and expiry_values is not None:
        result[expiry_column] = expiry_values
    return result, changed, invalid_inception_count, invalid_expiry_count
