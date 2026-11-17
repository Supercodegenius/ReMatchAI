"""Cedant profitability: score each buyer from its own loss history."""

from __future__ import annotations

import pandas as pd

PRINCIPAL_LINES = ["Casualty", "Property", "Aviation", "Marine"]
# "line" is optional: when present, each cedant is scored separately per principal line.
REQUIRED_COLUMNS = ["cedant", "year", "premium", "paid_loss", "outstanding_loss", "commission_pct"]

TEMPLATE_COLUMNS = ["cedant", "line", "year", "premium", "paid_loss", "outstanding_loss", "commission_pct"]

# Indicative age-to-ultimate factors by development age (years since underwriting year); replace with your own triangles.
DEFAULT_LDF = {0: 1.35, 1: 1.15, 2: 1.06, 3: 1.02}


def demo_history() -> pd.DataFrame:
    rows = []
    # (cedant, line): (base premium, loss ratios 2021..2025, commission)
    spec = {
        ("Atlas Mutual", "Property"): (12_000_000, [0.52, 0.58, 0.49, 0.55, 0.50], 0.22),
        ("Atlas Mutual", "Casualty"): (7_000_000, [0.78, 0.84, 0.90, 0.88, 0.93], 0.27),
        ("Borealis Re Cedant", "Casualty"): (8_000_000, [0.71, 0.88, 0.95, 0.79, 0.90], 0.27),
        ("Borealis Re Cedant", "Marine"): (4_000_000, [0.55, 0.60, 0.52, 0.58, 0.54], 0.25),
        ("XYZ Insurance", "Marine"): (3_600_000, [0.48, 0.52, 0.61, 0.50, 0.55], 0.20),
        ("Cobalt Specialty", "Aviation"): (5_000_000, [0.40, 1.35, 0.35, 0.45, 0.38], 0.20),
        ("Cobalt Specialty", "Marine"): (3_000_000, [0.50, 0.55, 0.48, 0.52, 0.50], 0.24),
        ("Delta General", "Property"): (9_000_000, [0.63, 0.66, 0.61, 0.68, 0.64], 0.30),
        ("Everest Regional", "Marine"): (3_000_000, [0.60, 0.55], 0.25),
    }
    for (name, line), (prem, lrs, comm) in spec.items():
        latest = 2025
        for i, lr in enumerate(lrs):
            year = 2021 + i
            age = latest - year
            ldf = DEFAULT_LDF.get(age, 1.0)
            incurred = prem * lr / ldf
            paid_share = {0: 0.35, 1: 0.6, 2: 0.8, 3: 0.92}.get(age, 0.98)
            rows.append(dict(cedant=name, line=line, year=year, premium=prem * (1 + 0.04 * i),
                             paid_loss=incurred * paid_share, outstanding_loss=incurred * (1 - paid_share),
                             commission_pct=comm))
    return pd.DataFrame(rows, columns=TEMPLATE_COLUMNS)


def template_csv() -> str:
    """Header plus two example rows showing the expected layout."""
    example = pd.DataFrame([
        dict(cedant="Example Cedant A", line="Casualty", year=2024, premium=5_000_000, paid_loss=2_100_000,
             outstanding_loss=900_000, commission_pct=0.25),
        dict(cedant="Example Cedant A", line="Casualty", year=2025, premium=5_400_000, paid_loss=900_000,
             outstanding_loss=1_800_000, commission_pct=0.25),
    ], columns=TEMPLATE_COLUMNS)
    return example.to_csv(index=False)


def validate(df: pd.DataFrame) -> list[str]:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return [f"Missing columns: {', '.join(missing)}"] if missing else []


def score_cedants(
    df: pd.DataFrame,
    hurdle_roe: float = 0.12,
    expense_pct: float = 0.03,
    investment_yield: float = 0.04,
    capital_per_premium: float = 0.60,
    prior_loss_ratio: float = 0.65,
    credibility_k: float = 3.0,
    ldf: dict[int, float] | None = None,
) -> pd.DataFrame:
    ldf = ldf or DEFAULT_LDF
    d = df.copy()
    latest = int(d["year"].max())
    d["age"] = latest - d["year"].astype(int)
    d["ldf"] = d["age"].map(lambda a: ldf.get(int(a), 1.0))
    d["ultimate_loss"] = (d["paid_loss"] + d["outstanding_loss"]) * d["ldf"]
    d["loss_ratio"] = d["ultimate_loss"] / d["premium"]

    out = []
    has_line = "line" in d.columns
    keys = ["cedant", "line"] if has_line else ["cedant"]
    for key, g in d.groupby(keys):
        name, line = key if has_line else (key, None)
        prem = g["premium"].sum()
        ult = g["ultimate_loss"].sum()
        lr = ult / prem
        n = g["year"].nunique()
        vol = float(g["loss_ratio"].std(ddof=0)) if n > 1 else float("nan")
        z = n / (n + credibility_k)
        blended = z * lr + (1 - z) * prior_loss_ratio
        comm = float((g["commission_pct"] * g["premium"]).sum() / prem)
        margin = 1 - comm - expense_pct + investment_yield
        profit = prem * (margin - lr)
        capital = capital_per_premium * prem
        roe = profit / capital
        fwd_roe = (margin - blended) / capital_per_premium
        denom = margin - hurdle_roe * capital_per_premium
        rate_change = blended / denom - 1 if denom > 0 else float("inf")

        if fwd_roe >= hurdle_roe + 0.03:
            verdict = "Profitable – grow"
        elif fwd_roe >= hurdle_roe:
            verdict = "Keep – at hurdle"
        elif fwd_roe >= 0:
            verdict = "Reprice"
        else:
            verdict = "Reduce / exit"
        row = dict(cedant=name)
        if has_line:
            row["line"] = line
        out.append(dict(
            **row, years=n, premium=prem, ultimate_loss=ult, loss_ratio=lr,
            blended_loss_ratio=blended, credibility=z, loss_ratio_volatility=vol,
            combined_ratio=lr + comm + expense_pct, uw_profit=profit, roe=roe,
            forward_roe=fwd_roe, rate_change_needed=rate_change, verdict=verdict,
        ))
    return pd.DataFrame(out).sort_values("forward_roe", ascending=False).reset_index(drop=True)
