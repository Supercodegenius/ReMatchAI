# Build with AI: AI-Powered Name Matching
# Bulk Name Matching Business Logic
# Developed By Ambuj Kumar

import os
import pandas as pd
from io import BytesIO
from collections import defaultdict
from typing import Optional


def read_source_file(path: str) -> pd.DataFrame:
    """Read a CSV or XLSX file from a local path."""
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def read_source_columns(path: str) -> list[str]:
    """Read only column headers from a CSV/XLSX file."""
    if path.lower().endswith(".csv"):
        return pd.read_csv(path, nrows=0).columns.tolist()
    return pd.read_excel(path, nrows=0).columns.tolist()


def list_source_files(folder: str) -> list[str]:
    """Return sorted list of CSV/XLSX filenames in a folder (excludes temp files)."""
    if not os.path.isdir(folder):
        return []
    return sorted(
        f
        for f in os.listdir(folder)
        if f.lower().endswith((".csv", ".xlsx")) and not f.startswith("~$")
    )


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Serialise a DataFrame to an in-memory XLSX byte string."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return buf.getvalue()


def build_target_location_lookup(
    target_df: pd.DataFrame,
    tgt_name_col: str,
    tgt_loc_col: Optional[str],
) -> dict[str, str]:
    """Build target name -> location map once and reuse across bulk files."""
    if not tgt_loc_col or tgt_loc_col not in target_df.columns:
        return {}
    return (
        target_df.dropna(subset=[tgt_name_col])
        .drop_duplicates(subset=[tgt_name_col])
        .set_index(tgt_name_col)[tgt_loc_col]
        .to_dict()
    )


def build_output_dataframe(
    source_df: pd.DataFrame,
    match_df: pd.DataFrame,
    src_name_col: str,
    src_loc_col: Optional[str],
    target_df: pd.DataFrame,
    tgt_name_col: str,
    tgt_loc_col: Optional[str],
    target_loc_lookup: Optional[dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Merge match results back into the source DataFrame:
    - Insert 'Matched Name' directly after src_name_col.
    - Insert 'Matched Location' directly after src_loc_col (when provided).
    - Append all remaining score columns from match_df at the end.
    """
    out = source_df.copy()

    # Build location lookup from reference file
    loc_lookup: dict[str, str] = target_loc_lookup or build_target_location_lookup(
        target_df,
        tgt_name_col,
        tgt_loc_col,
    )

    matched_names = match_df["matched_name"].tolist()

    # Insert 'Matched Name' after the source name column
    cols = out.columns.tolist()
    name_pos = cols.index(src_name_col) + 1
    out.insert(name_pos, "Matched Name", matched_names)

    # Insert 'Matched Location' after the source location column
    if src_loc_col and src_loc_col in out.columns:
        matched_locs = [loc_lookup.get(str(mn), "") for mn in matched_names]
        cols = out.columns.tolist()
        loc_pos = cols.index(src_loc_col) + 1
        out.insert(loc_pos, "Matched Location", matched_locs)

    # Append score columns at the end (exclude columns already in source)
    score_cols = [
        c
        for c in match_df.columns
        if c not in ("source_name", "matched_name") and c not in out.columns
    ]
    for col in score_cols:
        out[col] = match_df[col].values

    return out


def process_single_file(
    source_path: str,
    target_df: pd.DataFrame,
    src_name_col: str,
    src_loc_col: Optional[str],
    tgt_name_col: str,
    tgt_loc_col: Optional[str],
    method: str = "fuzzy",
    fuzzy_threshold: int = 75,
    lev_max_distance: int = 2,
    lev_engine: str = "auto",
    location_threshold: int = 85,
    target_names: Optional[list[str]] = None,
    target_loc_lookup: Optional[dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Load a single source file, run name matching against target_df,
    and return the enriched output DataFrame.
    """
    from Source.namematching import (
        load_match_feedback,
        match_names,
        normalize_name,
        fuzzy_score,
    )

    try:
        from rapidfuzz import fuzz as rf_fuzz
        from rapidfuzz import process as rf_process
    except Exception:
        rf_fuzz = None
        rf_process = None

    source_df = read_source_file(source_path)

    if src_name_col not in source_df.columns:
        raise ValueError(
            f"Column '{src_name_col}' not found in '{os.path.basename(source_path)}'. "
            f"Available columns: {list(source_df.columns)}"
        )

    src_names = source_df[src_name_col].fillna("").astype(str).str.strip().tolist()
    if target_names is None:
        tgt_names = target_df[tgt_name_col].fillna("").astype(str).str.strip().tolist()
    else:
        tgt_names = target_names

    feedback_db_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "outputs",
        "match_feedback.db",
    )
    feedback = load_match_feedback(feedback_db_path)

    use_location_staging = (
        bool(src_loc_col)
        and bool(tgt_loc_col)
        and src_loc_col in source_df.columns
        and tgt_loc_col in target_df.columns
    )

    if use_location_staging:
        src_locs = source_df[src_loc_col].fillna("").astype(str).str.strip().tolist()
        tgt_locs = target_df[tgt_loc_col].fillna("").astype(str).str.strip().tolist()
        tgt_locs_norm = [normalize_name(v) for v in tgt_locs]

        all_tgt_indices = list(range(len(tgt_names)))
        tgt_loc_to_indices: dict[str, list[int]] = defaultdict(list)
        for idx, loc in enumerate(tgt_locs_norm):
            tgt_loc_to_indices[loc].append(idx)
        unique_tgt_locs = list(tgt_loc_to_indices.keys())

        src_loc_to_rows: dict[str, list[int]] = defaultdict(list)
        src_locs_norm = [normalize_name(v) for v in src_locs]
        for row_idx, loc in enumerate(src_locs_norm):
            src_loc_to_rows[loc].append(row_idx)

        row_payloads: list[dict] = [{} for _ in src_names]
        for src_loc_norm, row_indices in src_loc_to_rows.items():
            if src_loc_norm:
                matched_tgt_indices: list[int] = []
                if rf_process is not None and rf_fuzz is not None:
                    hits = rf_process.extract(
                        src_loc_norm,
                        unique_tgt_locs,
                        scorer=rf_fuzz.ratio,
                        processor=None,
                        score_cutoff=location_threshold,
                        limit=None,
                    )
                    for _, _, hit_pos in hits:
                        matched_tgt_indices.extend(
                            tgt_loc_to_indices[unique_tgt_locs[int(hit_pos)]]
                        )
                else:
                    matched_tgt_indices = [
                        j
                        for j, tgt_loc_norm in enumerate(tgt_locs_norm)
                        if tgt_loc_norm and fuzzy_score(src_loc_norm, tgt_loc_norm) >= location_threshold
                    ]
                candidate_tgt_indices = (
                    matched_tgt_indices if matched_tgt_indices else all_tgt_indices
                )
            else:
                candidate_tgt_indices = all_tgt_indices

            group_src = [src_names[i] for i in row_indices]
            group_tgt = [tgt_names[j] for j in candidate_tgt_indices]
            sub_df = match_names(
                group_src,
                group_tgt,
                method=method,
                fuzzy_threshold=fuzzy_threshold,
                lev_max_distance=lev_max_distance,
                lev_engine=lev_engine,
                feedback=feedback,
            )

            for sub_pos, src_row_idx in enumerate(row_indices):
                row_payloads[src_row_idx] = sub_df.iloc[sub_pos].to_dict()

        match_df = pd.DataFrame(row_payloads)
    else:
        match_df = match_names(
            src_names,
            tgt_names,
            method=method,
            fuzzy_threshold=fuzzy_threshold,
            lev_max_distance=lev_max_distance,
            lev_engine=lev_engine,
            feedback=feedback,
        )

    return build_output_dataframe(
        source_df,
        match_df,
        src_name_col,
        src_loc_col,
        target_df,
        tgt_name_col,
        tgt_loc_col,
        target_loc_lookup=target_loc_lookup,
    )
