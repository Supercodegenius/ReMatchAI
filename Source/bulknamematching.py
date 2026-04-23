# Build with AI: AI-Powered Name Matching
# Bulk Name Matching Business Logic
# Developed By Ambuj Kumar

import os
import pandas as pd
from io import BytesIO
from typing import Optional


def read_source_file(path: str) -> pd.DataFrame:
    """Read a CSV or XLSX file from a local path."""
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


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


def build_output_dataframe(
    source_df: pd.DataFrame,
    match_df: pd.DataFrame,
    src_name_col: str,
    src_loc_col: Optional[str],
    target_df: pd.DataFrame,
    tgt_name_col: str,
    tgt_loc_col: Optional[str],
) -> pd.DataFrame:
    """
    Merge match results back into the source DataFrame:
    - Insert 'Matched Name' directly after src_name_col.
    - Insert 'Matched Location' directly after src_loc_col (when provided).
    - Append all remaining score columns from match_df at the end.
    """
    out = source_df.copy()

    # Build location lookup from reference file
    loc_lookup: dict[str, str] = {}
    if tgt_loc_col and tgt_loc_col in target_df.columns:
        loc_lookup = (
            target_df.dropna(subset=[tgt_name_col])
            .drop_duplicates(subset=[tgt_name_col])
            .set_index(tgt_name_col)[tgt_loc_col]
            .to_dict()
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
) -> pd.DataFrame:
    """
    Load a single source file, run name matching against target_df,
    and return the enriched output DataFrame.
    """
    from Source.namematching import match_names

    source_df = read_source_file(source_path)

    if src_name_col not in source_df.columns:
        raise ValueError(
            f"Column '{src_name_col}' not found in '{os.path.basename(source_path)}'. "
            f"Available columns: {list(source_df.columns)}"
        )

    src_names = source_df[src_name_col].fillna("").astype(str).str.strip().tolist()
    tgt_names = target_df[tgt_name_col].fillna("").astype(str).str.strip().tolist()

    match_df = match_names(
        src_names,
        tgt_names,
        method=method,
        fuzzy_threshold=fuzzy_threshold,
        lev_max_distance=lev_max_distance,
        lev_engine=lev_engine,
    )

    return build_output_dataframe(
        source_df,
        match_df,
        src_name_col,
        src_loc_col,
        target_df,
        tgt_name_col,
        tgt_loc_col,
    )
