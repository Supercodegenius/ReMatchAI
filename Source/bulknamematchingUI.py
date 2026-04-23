# Build with AI: AI-Powered Name Matching
# Bulk Name Matching UI
# Developed By Ambuj Kumar

import os
import sys
import pandas as pd
import streamlit as st
from io import BytesIO

# Ensure workspace root is on sys.path for Source imports
_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(__file__))
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

from Source.bulknamematching import (
    list_source_files,
    read_source_file,
    to_excel_bytes,
    process_single_file,
)

# ── Constants ────────────────────────────────────────────────────────────────
METHOD_KEY_MAP = {
    "Exact Match": "exact",
    "Fuzzy Match": "fuzzy",
    "Soundex Match": "soundex",
    "Jaro-Winkler Distance Match": "jaro_winkler",
    "Levenshtein Match": "levenshtein",
    "AI Advance Match": "ai_advanced",
}

# ── Page header ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="
        padding: 0.85rem 1.05rem 0.8rem 1.05rem;
        border: 1px solid rgba(20,50,112,0.2);
        border-radius: 0.65rem;
        background: linear-gradient(135deg, #13347f, #1b4aa8 52%, #2558be);
        box-shadow: 0 14px 28px rgba(15,38,86,0.22);
        margin-bottom: 1.2rem;
    ">
      <h2 style="margin:0 0 0.2rem 0; font-size:1.35rem; color:#f7fbff;">
        📦 Bulk Name Matching
      </h2>
      <p style="margin:0; color:rgba(245,251,255,0.9); font-size:0.98rem;">
        Match every source file in a folder against a single reference file and
        download enriched output files — one per source.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 1. File Configuration ────────────────────────────────────────────────────
st.markdown("### 1 · File Configuration")
conf_c1, conf_c2 = st.columns(2, gap="large")
with conf_c1:
    source_folder: str = st.text_input(
        "Source Folder Path",
        placeholder="e.g. C:/data/source_files",
        help="Folder containing the CSV / XLSX source files to be matched.",
        key="bulk_source_folder",
    ).strip()
with conf_c2:
    output_folder: str = st.text_input(
        "Matched Output Folder",
        placeholder="e.g. C:/data/matched_files",
        help="Folder where the enriched output files will be saved. Created if it does not exist.",
        key="bulk_output_folder",
    ).strip()

target_file = st.file_uploader(
    "**Target (Reference) File**",
    type=["csv", "xlsx"],
    key="bulk_target_file",
    help="The reference list that source names will be matched against.",
)

# Load target DataFrame
target_df: pd.DataFrame | None = None
if target_file is not None:
    try:
        raw = BytesIO(target_file.getvalue())
        fn = target_file.name.lower()
        target_df = pd.read_csv(raw) if fn.endswith(".csv") else pd.read_excel(raw)
    except Exception as exc:
        st.error(f"Could not read target file: {exc}")

# ── Resolve source file list & preview first file for column selection ────────
source_files: list[str] = []
first_source_df: pd.DataFrame | None = None

if source_folder:
    if os.path.isdir(source_folder):
        source_files = list_source_files(source_folder)
        if source_files:
            try:
                first_source_df = read_source_file(
                    os.path.join(source_folder, source_files[0])
                )
            except Exception:
                first_source_df = None
    else:
        st.warning(f"Source folder not found: `{source_folder}`")

# ── 2. Choose Columns ────────────────────────────────────────────────────────
st.markdown("### 2 · Choose Columns")
st.caption(
    "Source columns are derived from the first file in the source folder. "
    "Columns must exist in every source file."
)

col_src, col_tgt = st.columns(2, gap="large")

src_name_col: str | None = None
src_loc_col: str | None = None
tgt_name_col: str | None = None
tgt_loc_col: str | None = None

with col_src:
    st.markdown("**Source File Columns**")
    if first_source_df is not None:
        src_cols = first_source_df.columns.tolist()
        # Smart default: prefer 'full_name', 'name', 'company_name', else first col
        _name_defaults = [c for c in ["full_name", "name", "company_name"] if c in src_cols]
        src_name_default = src_cols.index(_name_defaults[0]) if _name_defaults else 0
        src_name_col = st.selectbox(
            "Source name column",
            options=src_cols,
            index=src_name_default,
            key="bulk_src_name_col",
        )
        _loc_defaults = [c for c in ["location", "country", "city"] if c in src_cols]
        src_loc_options = ["(none)"] + [c for c in src_cols if c != src_name_col]
        src_loc_default = 0
        if _loc_defaults:
            _loc_in_opts = [c for c in _loc_defaults if c in src_loc_options]
            if _loc_in_opts:
                src_loc_default = src_loc_options.index(_loc_in_opts[0])
        src_loc_sel = st.selectbox(
            "Source location column (optional)",
            options=src_loc_options,
            index=src_loc_default,
            key="bulk_src_loc_col",
        )
        src_loc_col = None if src_loc_sel == "(none)" else src_loc_sel
    else:
        _src_name_txt = st.text_input(
            "Source name column",
            placeholder="e.g. full_name",
            key="bulk_src_name_col_txt",
        ).strip()
        src_name_col = _src_name_txt or None
        _src_loc_txt = st.text_input(
            "Source location column (optional)",
            placeholder="e.g. country",
            key="bulk_src_loc_col_txt",
        ).strip()
        src_loc_col = _src_loc_txt or None

with col_tgt:
    st.markdown("**Target (Reference) File Columns**")
    if target_df is not None:
        tgt_cols = target_df.columns.tolist()
        _tgt_name_defaults = [
            c for c in ["name_in_system", "name", "full_name", "company_name"] if c in tgt_cols
        ]
        tgt_name_default = (
            tgt_cols.index(_tgt_name_defaults[0]) if _tgt_name_defaults else 0
        )
        tgt_name_col = st.selectbox(
            "Target name column",
            options=tgt_cols,
            index=tgt_name_default,
            key="bulk_tgt_name_col",
        )
        _tgt_loc_defaults = [c for c in ["location", "country", "city"] if c in tgt_cols]
        tgt_loc_options = ["(none)"] + [c for c in tgt_cols if c != tgt_name_col]
        tgt_loc_default = 0
        if _tgt_loc_defaults:
            _tgt_loc_in_opts = [c for c in _tgt_loc_defaults if c in tgt_loc_options]
            if _tgt_loc_in_opts:
                tgt_loc_default = tgt_loc_options.index(_tgt_loc_in_opts[0])
        tgt_loc_sel = st.selectbox(
            "Target location column (optional)",
            options=tgt_loc_options,
            index=tgt_loc_default,
            key="bulk_tgt_loc_col",
        )
        tgt_loc_col = None if tgt_loc_sel == "(none)" else tgt_loc_sel
    else:
        _tgt_name_txt = st.text_input(
            "Target name column",
            placeholder="e.g. name_in_system",
            key="bulk_tgt_name_col_txt",
        ).strip()
        tgt_name_col = _tgt_name_txt or None
        _tgt_loc_txt = st.text_input(
            "Target location column (optional)",
            placeholder="e.g. country",
            key="bulk_tgt_loc_col_txt",
        ).strip()
        tgt_loc_col = _tgt_loc_txt or None

# ── 3. Matching Settings ─────────────────────────────────────────────────────
st.markdown("### 3 · Matching Settings")
ms_c1, ms_c2, ms_c3 = st.columns(3, gap="small")
with ms_c1:
    bulk_method_label = st.selectbox(
        "Method",
        list(METHOD_KEY_MAP.keys()),
        index=1,  # Fuzzy by default
        key="bulk_method",
    )
with ms_c2:
    bulk_threshold = st.slider("Fuzzy threshold", 0, 100, 75, 1, key="bulk_threshold")
with ms_c3:
    bulk_lev_distance = st.slider(
        "Levenshtein max distance", 0, 10, 2, 1, key="bulk_lev_distance"
    )

bulk_method_key = METHOD_KEY_MAP[bulk_method_label]

# ── 4. Source Files Table + Start Button ─────────────────────────────────────
st.markdown("### 4 · Source Files")

bulk_results: dict = st.session_state.get("bulk_results", {})

if not source_files:
    if source_folder:
        st.info("No CSV / XLSX files found in the source folder.")
    else:
        st.info("Enter a **Source Folder Path** above to list files.")
else:
    # Table header
    h1, h2, h3, h4 = st.columns([3, 3, 1.8, 1.8])
    h1.markdown("**Source Files**")
    h2.markdown("**Matched Files**")
    h3.markdown("**Match Status**")
    h4.markdown("**Link To Download**")
    st.divider()

    # Table rows
    for fname in source_files:
        r1, r2, r3, r4 = st.columns([3, 3, 1.8, 1.8])
        r1.write(fname)
        result = bulk_results.get(fname)
        if result:
            status = result.get("status", "")
            out_name = result.get("out_name", "—")
            r2.write(out_name)
            if status == "done":
                r3.success("✓ Matched")
                out_bytes = result.get("bytes")
                if out_bytes:
                    r4.download_button(
                        "⬇ Download",
                        data=out_bytes,
                        file_name=out_name,
                        mime=(
                            "application/vnd.openxmlformats-officedocument"
                            ".spreadsheetml.sheet"
                        ),
                        key=f"dl_{fname}",
                        use_container_width=True,
                    )
            elif status == "error":
                r3.error("✗ Error")
                r2.caption(result.get("error", "Unknown error"))
            else:
                r3.info("⏳ Pending")
        else:
            r2.write("—")
            r3.write("—")
            r4.write("—")

    st.markdown("")

    # Validation guard
    _can_run = bool(
        source_files
        and target_df is not None
        and src_name_col
        and tgt_name_col
    )
    _missing: list[str] = []
    if target_df is None:
        _missing.append("target file")
    if not src_name_col:
        _missing.append("source name column")
    if not tgt_name_col:
        _missing.append("target name column")

    if _missing:
        st.caption(f"⚠ Cannot start — missing: {', '.join(_missing)}.")

    start_btn = st.button(
        "▶  Start Bulk Processing",
        type="primary",
        use_container_width=True,
        disabled=not _can_run,
        key="bulk_start_btn",
    )

    if start_btn and _can_run:
        # Create output folder if specified
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)

        progress_bar = st.progress(0, text="Initialising…")
        new_results: dict = {}

        for i, fname in enumerate(source_files):
            progress_bar.progress(
                i / len(source_files),
                text=f"Processing {i + 1}/{len(source_files)}: {fname}",
            )
            src_path = os.path.join(source_folder, fname)
            stem = os.path.splitext(fname)[0]
            out_name = f"{stem}_matched.xlsx"

            try:
                out_df = process_single_file(
                    source_path=src_path,
                    target_df=target_df,
                    src_name_col=src_name_col,
                    src_loc_col=src_loc_col,
                    tgt_name_col=tgt_name_col,
                    tgt_loc_col=tgt_loc_col,
                    method=bulk_method_key,
                    fuzzy_threshold=int(bulk_threshold),
                    lev_max_distance=int(bulk_lev_distance),
                    lev_engine="auto",
                )

                out_bytes = to_excel_bytes(out_df)

                # Save to disk if output folder is set
                if output_folder and os.path.isdir(output_folder):
                    out_path = os.path.join(output_folder, out_name)
                    with open(out_path, "wb") as fh:
                        fh.write(out_bytes)

                new_results[fname] = {
                    "status": "done",
                    "out_name": out_name,
                    "bytes": out_bytes,
                }
            except Exception as exc:
                new_results[fname] = {
                    "status": "error",
                    "out_name": out_name,
                    "error": str(exc),
                }

        progress_bar.progress(1.0, text=f"Done — {len(source_files)} file(s) processed.")
        st.session_state["bulk_results"] = new_results
        st.rerun()

# ── Summary metrics (post-run) ────────────────────────────────────────────────
if bulk_results:
    done_count = sum(1 for r in bulk_results.values() if r.get("status") == "done")
    error_count = sum(1 for r in bulk_results.values() if r.get("status") == "error")
    sm_c1, sm_c2, sm_c3 = st.columns(3)
    sm_c1.metric("Files processed", len(bulk_results))
    sm_c2.metric("Matched successfully", done_count)
    sm_c3.metric("Errors", error_count)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="nm-footer">&copy; 2026 braincal.com. All rights reserved</div>',
    unsafe_allow_html=True,
)
