import pandas as pd

from Myrepo.name_matching import (
    ai_advanced_score,
    fuzzy_score,
    levenshtein_distance,
    match_names,
    normalize_name,
)


def test_normalize_name_basic():
    assert normalize_name(" John A. Smith ") == "john a smith"
    assert normalize_name("Ana-Maria Lopez") == "ana maria lopez"
    assert normalize_name("Pat O'Neil") == "pat o neil"
    assert normalize_name("  Li   Wei  ") == "li wei"


def test_normalize_name_legal_suffix_variants():
    assert normalize_name("ENI SPA") == "eni spa"
    assert normalize_name("ENI S.P.A.") == "eni spa"


def test_normalize_name_accent_variants():
    assert normalize_name("HYDRO QUEBEC") == "hydro quebec"
    assert normalize_name("HYDRO-QUÉBEC") == "hydro quebec"


def test_levenshtein_distance_known_values():
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("", "abc") == 3
    assert levenshtein_distance("abc", "") == 3
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("john smith", "john smith") == 0


def test_fuzzy_score_sanity():
    assert fuzzy_score("abc", "abc") == 100
    assert fuzzy_score("john smith", "john smith") == 100
    assert fuzzy_score("john smith", "jane doe") < 100


def _demo_source_target():
    source = [
        "John A. Smith",
        "Sara Connor",
        "Mohamed Ali",
        "Ana-Maria Lopez",
        "Chris P Bacon",
    ]
    target = [
        "john smith",
        "Sarah Connor",
        "Mohammad Ali",
        "Ana Maria Lopez",
        "Christopher Bacon",
    ]
    return source, target


def test_match_names_exact_normalized():
    source, target = _demo_source_target()
    df = match_names(source, target, method="exact")
    assert len(df) == len(source)
    assert set(["source_name", "matched_name", "score", "is_match"]).issubset(df.columns)

    ana_row = df.loc[df["source_name"] == "Ana-Maria Lopez"].iloc[0]
    assert bool(ana_row["is_match"]) is True
    assert ana_row["matched_name"] == "Ana Maria Lopez"
    assert ana_row["score"] == 100

    john_row = df.loc[df["source_name"] == "John A. Smith"].iloc[0]
    assert bool(john_row["is_match"]) is False
    assert john_row["matched_name"] == ""
    assert john_row["score"] == 0


def test_match_names_exact_matches_legal_suffix_variants():
    df = match_names(["ENI SPA"], ["ENI S.P.A."], method="exact")

    row = df.iloc[0]
    assert bool(row["is_match"]) is True
    assert row["matched_name"] == "ENI S.P.A."
    assert int(row["score"]) == 100


def test_match_names_exact_matches_accent_variants():
    df = match_names(["HYDRO QUEBEC"], ["HYDRO-QUÉBEC"], method="exact")

    row = df.iloc[0]
    assert bool(row["is_match"]) is True
    assert row["matched_name"] == "HYDRO-QUÉBEC"
    assert int(row["score"]) == 100


def test_match_names_fuzzy_best_match_thresholding():
    source, target = _demo_source_target()
    df = match_names(source, target, method="fuzzy", fuzzy_threshold=85)

    john_row = df.loc[df["source_name"] == "John A. Smith"].iloc[0]
    assert john_row["matched_name"] == "john smith"
    assert john_row["score"] >= 85
    assert bool(john_row["is_match"]) is True

    chris_row = df.loc[df["source_name"] == "Chris P Bacon"].iloc[0]
    assert chris_row["matched_name"] == "Christopher Bacon"
    assert 0 <= int(chris_row["score"]) <= 100


def test_match_names_levenshtein_best_match_distance_gate():
    source, target = _demo_source_target()
    df = match_names(source, target, method="levenshtein", lev_max_distance=2)
    assert "distance" in df.columns

    ana_row = df.loc[df["source_name"] == "Ana-Maria Lopez"].iloc[0]
    assert ana_row["matched_name"] == "Ana Maria Lopez"
    assert int(ana_row["distance"]) <= 2
    assert bool(ana_row["is_match"]) is True

    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(source)


def test_ai_advanced_score_sanity():
    assert ai_advanced_score("john smith", "john smith") == 100
    assert ai_advanced_score("john smith", "jane doe") < 80


def test_match_names_ai_advanced_best_match_thresholding():
    source, target = _demo_source_target()
    df = match_names(source, target, method="ai_advanced", fuzzy_threshold=80)

    assert len(df) == len(source)
    assert set(["score", "ai_fuzzy_score", "ai_jaro_winkler_score", "ai_token_score"]).issubset(df.columns)

    john_row = df.loc[df["source_name"] == "John A. Smith"].iloc[0]
    assert john_row["matched_name"] == "john smith"
    assert int(john_row["score"]) >= 80
    assert bool(john_row["is_match"]) is True
