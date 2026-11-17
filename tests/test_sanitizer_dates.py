from datetime import date

import pandas as pd

from Source.sanitizer_dates import apply_inception_expiry_rules


def test_format_dates_and_align_expiry_is_one_day_before_next_year_anniversary():
    source = pd.DataFrame(
        {
            "Inception": ["29/02/2024", "15/03/2023", "01/01/2025"],
            "Expiry": ["28/02/2025", "15/03/2024", "31/12/2025"],
        }
    )

    result, changed, invalid_inception, invalid_expiry = apply_inception_expiry_rules(
        source,
        "Inception",
        "Expiry",
        format_dates=True,
        align_expiry=True,
    )

    assert result["Inception"].tolist() == ["29-Feb-24", "15-Mar-23", "01-Jan-25"]
    assert result["Expiry"].tolist() == ["28-Feb-25", "14-Mar-24", "31-Dec-25"]
    assert changed.tolist() == [True, True, True]
    assert invalid_inception == 0
    assert invalid_expiry == 0


def test_align_expiry_keeps_already_correct_values_and_reports_unparseable_inception():
    source = pd.DataFrame(
        {
            "Inception": [date(2024, 1, 31), "not a date"],
            "Expiry": [date(2025, 1, 30), "31/12/2025"],
        }
    )

    result, changed, invalid_inception, invalid_expiry = apply_inception_expiry_rules(
        source,
        "Inception",
        "Expiry",
        format_dates=False,
        align_expiry=True,
    )

    assert result.loc[0, "Expiry"] == date(2025, 1, 30)
    assert result.loc[1, "Inception"] == "not a date"
    assert result.loc[1, "Expiry"] == "31/12/2025"
    assert changed.tolist() == [False, False]
    assert invalid_inception == 1
    assert invalid_expiry == 0


def test_format_dates_without_expiry_column_formats_inception_only():
    source = pd.DataFrame({"Inception": ["31/12/2025", "invalid"]})

    result, changed, invalid_inception, invalid_expiry = apply_inception_expiry_rules(
        source,
        "Inception",
        None,
        format_dates=True,
        align_expiry=False,
    )

    assert result["Inception"].tolist() == ["31-Dec-25", "invalid"]
    assert changed.tolist() == [True, False]
    assert invalid_inception == 1
    assert invalid_expiry == 0
