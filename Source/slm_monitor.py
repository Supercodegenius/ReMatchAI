"""
SLM Model Lifecycle Monitor
---------------------------
Tracks inference telemetry, measures quality from real feedback, and detects
average score drift between a short recent window and a longer baseline.

All writes are best-effort and will never propagate exceptions to callers.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Telemetry DB schema
# ---------------------------------------------------------------------------

_TELEMETRY_DDL = """
CREATE TABLE IF NOT EXISTS slm_telemetry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT    NOT NULL,
    ts              TEXT    NOT NULL,
    method          TEXT    NOT NULL,
    source_count    INTEGER NOT NULL,
    matched_count   INTEGER NOT NULL,
    avg_score       REAL    NOT NULL,
    feedback_hits   INTEGER NOT NULL,
    stage_fast      INTEGER NOT NULL,
    stage_exact     INTEGER NOT NULL,
    stage_deep      INTEGER NOT NULL,
    stage_feedback  INTEGER NOT NULL,
    inference_ms    REAL    NOT NULL,
    model_version   TEXT    NOT NULL
)
"""

# ---------------------------------------------------------------------------
# Model version
# ---------------------------------------------------------------------------


def get_model_version(model_dir: str | None = None) -> str:
    """Return a short version string derived from the model's config.json."""
    candidates: list[Path] = []
    if model_dir:
        candidates.append(Path(model_dir) / "config.json")
    script_dir = Path(__file__).resolve().parent
    candidates += [
        script_dir / "outputs" / "biencoder" / "config.json",
        script_dir.parent / "outputs" / "biencoder" / "config.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as fh:
                    cfg = json.load(fh)
                arch = cfg.get("architectures", ["unknown"])[0]
                hidden = cfg.get("hidden_size", "?")
                layers = cfg.get("num_hidden_layers", "?")
                max_pos = cfg.get("max_position_embeddings", "?")
                return f"{arch} h={hidden} layers={layers} max_pos={max_pos}"
            except Exception:
                return "unknown"
    return "unknown"


# ---------------------------------------------------------------------------
# Telemetry writer
# ---------------------------------------------------------------------------


def log_inference_run(db_path: str, metrics: dict[str, Any]) -> None:
    """Append one telemetry row to the SQLite DB. Never raises."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(_TELEMETRY_DDL)
            conn.execute(
                """
                INSERT INTO slm_telemetry
                  (run_id, ts, method, source_count, matched_count, avg_score,
                   feedback_hits, stage_fast, stage_exact, stage_deep,
                   stage_feedback, inference_ms, model_version)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(metrics.get("run_id", "")),
                    str(metrics.get("ts", datetime.now(timezone.utc).isoformat())),
                    str(metrics.get("method", "")),
                    int(metrics.get("source_count", 0)),
                    int(metrics.get("matched_count", 0)),
                    float(metrics.get("avg_score", 0.0)),
                    int(metrics.get("feedback_hits", 0)),
                    int(metrics.get("stage_fast", 0)),
                    int(metrics.get("stage_exact", 0)),
                    int(metrics.get("stage_deep", 0)),
                    int(metrics.get("stage_feedback", 0)),
                    float(metrics.get("inference_ms", 0.0)),
                    str(metrics.get("model_version", "unknown")),
                ),
            )
            conn.commit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Quality metrics from feedback
# ---------------------------------------------------------------------------


def compute_quality_metrics(feedback_db_path: str) -> dict[str, Any]:
    """
    Compute precision and rejection rate from the match_feedback table.
    Returns: total_labelled, approved, rejected, precision (0-1 or None).
    """
    try:
        with sqlite3.connect(feedback_db_path) as conn:
            rows = conn.execute(
                "SELECT is_correct, COUNT(*) FROM match_feedback GROUP BY is_correct"
            ).fetchall()
    except Exception:
        return {"total_labelled": 0, "approved": 0, "rejected": 0, "precision": None}

    total = sum(cnt for _, cnt in rows)
    approved = sum(cnt for correct, cnt in rows if correct == 1)
    rejected = total - approved
    precision = round(approved / total, 4) if total > 0 else None
    return {
        "total_labelled": total,
        "approved": approved,
        "rejected": rejected,
        "precision": precision,
    }


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


def detect_drift(
    telemetry_db_path: str,
    *,
    window_days: int = 7,
    baseline_days: int = 30,
) -> dict[str, Any]:
    """
    Compare avg_score in the last `window_days` against the prior `baseline_days`.
    A drop of more than 5 points triggers drift_detected=True.

    Returns:
        drift_detected  bool
        recent_avg      float | None
        baseline_avg    float | None
        delta           float | None   (negative = degradation)
        recent_runs     int
        baseline_runs   int
        insufficient_data bool
    """
    try:
        with sqlite3.connect(telemetry_db_path) as conn:
            conn.execute(_TELEMETRY_DDL)
            now = datetime.now(timezone.utc)
            recent_cutoff = (now - timedelta(days=window_days)).isoformat()
            baseline_cutoff = (now - timedelta(days=baseline_days)).isoformat()

            r_avg, r_n = conn.execute(
                "SELECT AVG(avg_score), COUNT(*) FROM slm_telemetry WHERE ts >= ?",
                (recent_cutoff,),
            ).fetchone()
            b_avg, b_n = conn.execute(
                "SELECT AVG(avg_score), COUNT(*) FROM slm_telemetry "
                "WHERE ts >= ? AND ts < ?",
                (baseline_cutoff, recent_cutoff),
            ).fetchone()
    except Exception:
        return {
            "drift_detected": False,
            "recent_avg": None,
            "baseline_avg": None,
            "delta": None,
            "recent_runs": 0,
            "baseline_runs": 0,
            "insufficient_data": True,
        }

    r_n = r_n or 0
    b_n = b_n or 0
    insufficient = r_avg is None or b_avg is None or b_n < 3

    if insufficient:
        return {
            "drift_detected": False,
            "recent_avg": round(float(r_avg), 2) if r_avg is not None else None,
            "baseline_avg": round(float(b_avg), 2) if b_avg is not None else None,
            "delta": None,
            "recent_runs": r_n,
            "baseline_runs": b_n,
            "insufficient_data": True,
        }

    delta = float(r_avg) - float(b_avg)
    return {
        "drift_detected": delta < -5.0,
        "recent_avg": round(float(r_avg), 2),
        "baseline_avg": round(float(b_avg), 2),
        "delta": round(delta, 2),
        "recent_runs": r_n,
        "baseline_runs": b_n,
        "insufficient_data": False,
    }


# ---------------------------------------------------------------------------
# Combined health snapshot
# ---------------------------------------------------------------------------


def get_health_summary(
    feedback_db_path: str,
    telemetry_db_path: str,
) -> dict[str, Any]:
    """Return a combined health snapshot suitable for dashboard rendering."""
    quality = compute_quality_metrics(feedback_db_path)
    drift = detect_drift(telemetry_db_path)
    model_ver = get_model_version()

    alerts: list[str] = []
    if quality["precision"] is not None and quality["precision"] < 0.70:
        pct = int(round(quality["precision"] * 100))
        alerts.append(
            f"Low precision: only {pct}% of labelled pairs were approved. "
            "Review recent rejections in the feedback table."
        )
    if drift.get("drift_detected"):
        delta = abs(drift["delta"])
        alerts.append(
            f"Score drift detected: avg match score dropped {delta:.1f} pts "
            f"(recent {drift['recent_avg']} vs baseline {drift['baseline_avg']}). "
            "Consider reviewing false-positive feedback or retraining."
        )

    return {
        "model_version": model_ver,
        "quality": quality,
        "drift": drift,
        "alerts": alerts,
        "healthy": len(alerts) == 0,
    }


# ---------------------------------------------------------------------------
# Recent run history (for trend table in dashboard)
# ---------------------------------------------------------------------------


def get_recent_runs(
    telemetry_db_path: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return the most recent telemetry rows as a list of dicts."""
    try:
        with sqlite3.connect(telemetry_db_path) as conn:
            conn.execute(_TELEMETRY_DDL)
            rows = conn.execute(
                """
                SELECT ts, method, source_count, matched_count, avg_score,
                       feedback_hits, stage_fast, stage_exact, stage_deep,
                       stage_feedback, inference_ms, model_version
                FROM slm_telemetry
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        cols = [
            "ts", "method", "source_count", "matched_count", "avg_score",
            "feedback_hits", "stage_fast", "stage_exact", "stage_deep",
            "stage_feedback", "inference_ms", "model_version",
        ]
        return [dict(zip(cols, row)) for row in rows]
    except Exception:
        return []
