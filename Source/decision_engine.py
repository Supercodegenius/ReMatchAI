"""Decision Intelligence engine: instant write / don't-write economics for a reinsurance line."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt


@dataclass
class DealInputs:
    limit: float = 20_000_000.0          # 100% limit offered
    premium: float = 2_400_000.0         # 100% quoted premium
    expected_loss: float = 1_500_000.0   # 100% technical expected loss
    loss_cov: float = 2.5                # volatility (stdev / expected loss)
    commission_pct: float = 0.20         # ceding commission + brokerage
    expense_pct: float = 0.03            # internal expenses
    investment_yield: float = 0.03       # on premium, one-year float
    max_line: float = 0.50               # max share the market allows (0-1)
    min_line: float = 0.05               # smallest worthwhile line
    correlation: float = 0.35            # correlation to existing portfolio
    zone_limit_used: float = 60_000_000.0  # existing limit in the same zone
    zone_limit_appetite: float = 75_000_000.0
    data_quality_load: float = 0.0       # uplift to expected loss and volatility for weak cedant data


@dataclass
class PortfolioInputs:
    capital: float = 250_000_000.0         # allocated capital
    expected_profit: float = 32_500_000.0  # expected annual profit
    hurdle_roe: float = 0.12
    tail_multiple: float = 2.6             # capital = tail_multiple * stdev
    retro_rol: float = 0.09                # retro rate on line
    retro_capital_relief: float = 0.85     # capital relief per unit of retro ceded


# Indicative market-style starting points by buyer / treaty type; override with your own pricing and view of risk.
BUYER_PROFILES: dict[str, dict] = {
    "Property cat XL – regional insurer": dict(
        limit=25_000_000.0, premium=3_000_000.0, expected_loss=1_200_000.0, loss_cov=3.5,
        commission_pct=0.10, expense_pct=0.02, investment_yield=0.03, max_line=0.40, min_line=0.05,
        correlation=0.55, zone_limit_used=90_000_000.0, zone_limit_appetite=120_000_000.0, data_quality_load=0.05),
    "Property per-risk XL – commercial lines": dict(
        limit=10_000_000.0, premium=1_500_000.0, expected_loss=950_000.0, loss_cov=1.6,
        commission_pct=0.12, expense_pct=0.03, investment_yield=0.04, max_line=0.30, min_line=0.05,
        correlation=0.30, zone_limit_used=40_000_000.0, zone_limit_appetite=80_000_000.0, data_quality_load=0.08),
    "Casualty quota share – US liability": dict(
        limit=100_000_000.0, premium=50_000_000.0, expected_loss=33_000_000.0, loss_cov=0.30,
        commission_pct=0.30, expense_pct=0.02, investment_yield=0.09, max_line=0.20, min_line=0.025,
        correlation=0.40, zone_limit_used=150_000_000.0, zone_limit_appetite=400_000_000.0, data_quality_load=0.10),
    "Marine & energy XL – specialty": dict(
        limit=15_000_000.0, premium=1_800_000.0, expected_loss=1_000_000.0, loss_cov=2.2,
        commission_pct=0.15, expense_pct=0.03, investment_yield=0.04, max_line=0.35, min_line=0.05,
        correlation=0.25, zone_limit_used=30_000_000.0, zone_limit_appetite=60_000_000.0, data_quality_load=0.07),
}
_EXTRA = {
    "Property quota share – commercial": dict(limit=60_000_000.0, premium=30_000_000.0, expected_loss=19_500_000.0, loss_cov=0.35, commission_pct=0.30, expense_pct=0.02, investment_yield=0.04, max_line=0.20, min_line=0.025, correlation=0.45, zone_limit_used=120_000_000.0, zone_limit_appetite=300_000_000.0, data_quality_load=0.08),
    "Property surplus – large commercial": dict(limit=40_000_000.0, premium=6_000_000.0, expected_loss=3_600_000.0, loss_cov=1.2, commission_pct=0.25, expense_pct=0.03, investment_yield=0.04, max_line=0.25, min_line=0.05, correlation=0.35, zone_limit_used=80_000_000.0, zone_limit_appetite=150_000_000.0, data_quality_load=0.08),
    "Casualty XL – US liability": dict(limit=10_000_000.0, premium=1_600_000.0, expected_loss=1_100_000.0, loss_cov=2.0, commission_pct=0.15, expense_pct=0.03, investment_yield=0.09, max_line=0.30, min_line=0.05, correlation=0.35, zone_limit_used=50_000_000.0, zone_limit_appetite=100_000_000.0, data_quality_load=0.12),
    "Motor quota share – personal lines": dict(limit=80_000_000.0, premium=60_000_000.0, expected_loss=42_000_000.0, loss_cov=0.15, commission_pct=0.27, expense_pct=0.02, investment_yield=0.03, max_line=0.15, min_line=0.025, correlation=0.30, zone_limit_used=100_000_000.0, zone_limit_appetite=250_000_000.0, data_quality_load=0.05),
    "Motor XL – excess of loss": dict(limit=5_000_000.0, premium=900_000.0, expected_loss=600_000.0, loss_cov=1.8, commission_pct=0.10, expense_pct=0.03, investment_yield=0.06, max_line=0.35, min_line=0.05, correlation=0.25, zone_limit_used=25_000_000.0, zone_limit_appetite=60_000_000.0, data_quality_load=0.07),
    "Professional indemnity / D&O XL": dict(limit=10_000_000.0, premium=1_400_000.0, expected_loss=950_000.0, loss_cov=2.3, commission_pct=0.18, expense_pct=0.03, investment_yield=0.07, max_line=0.30, min_line=0.05, correlation=0.40, zone_limit_used=40_000_000.0, zone_limit_appetite=90_000_000.0, data_quality_load=0.10),
    "Cyber XL / aggregate": dict(limit=15_000_000.0, premium=2_700_000.0, expected_loss=1_500_000.0, loss_cov=3.0, commission_pct=0.20, expense_pct=0.03, investment_yield=0.04, max_line=0.25, min_line=0.05, correlation=0.60, zone_limit_used=45_000_000.0, zone_limit_appetite=70_000_000.0, data_quality_load=0.15),
    "Life / health quota share": dict(limit=50_000_000.0, premium=35_000_000.0, expected_loss=27_000_000.0, loss_cov=0.12, commission_pct=0.20, expense_pct=0.02, investment_yield=0.04, max_line=0.20, min_line=0.025, correlation=0.20, zone_limit_used=100_000_000.0, zone_limit_appetite=300_000_000.0, data_quality_load=0.04),
    "Agriculture / crop stop-loss": dict(limit=20_000_000.0, premium=4_000_000.0, expected_loss=2_600_000.0, loss_cov=1.5, commission_pct=0.15, expense_pct=0.03, investment_yield=0.03, max_line=0.30, min_line=0.05, correlation=0.50, zone_limit_used=50_000_000.0, zone_limit_appetite=100_000_000.0, data_quality_load=0.10),
    "Aviation / space XL": dict(limit=25_000_000.0, premium=2_500_000.0, expected_loss=1_500_000.0, loss_cov=2.8, commission_pct=0.15, expense_pct=0.03, investment_yield=0.04, max_line=0.25, min_line=0.05, correlation=0.20, zone_limit_used=40_000_000.0, zone_limit_appetite=80_000_000.0, data_quality_load=0.08),
    "Credit & surety XL": dict(limit=20_000_000.0, premium=2_400_000.0, expected_loss=1_400_000.0, loss_cov=2.6, commission_pct=0.20, expense_pct=0.03, investment_yield=0.05, max_line=0.25, min_line=0.05, correlation=0.55, zone_limit_used=60_000_000.0, zone_limit_appetite=100_000_000.0, data_quality_load=0.10),
    "Terrorism / political violence XL": dict(limit=20_000_000.0, premium=1_800_000.0, expected_loss=900_000.0, loss_cov=3.5, commission_pct=0.12, expense_pct=0.03, investment_yield=0.04, max_line=0.25, min_line=0.05, correlation=0.30, zone_limit_used=40_000_000.0, zone_limit_appetite=60_000_000.0, data_quality_load=0.10),
}
BUYER_PROFILES.update(_EXTRA)
DEFAULT_PROFILE = "Property cat XL – regional insurer"


def _evaluate(d: DealInputs, p: PortfolioInputs, share: float, premium: float | None = None) -> dict:
    prem = (d.premium if premium is None else premium) * share
    exp_loss = d.expected_loss * (1 + d.data_quality_load) * share
    acq_exp = (d.commission_pct + d.expense_pct) * prem
    invest = d.investment_yield * prem
    stdev = d.expected_loss * (1 + d.data_quality_load) * d.loss_cov * share
    standalone_cap = p.tail_multiple * stdev

    # Retro requirement driven by zone accumulation
    line_limit = d.limit * share
    excess = max(0.0, d.zone_limit_used + line_limit - d.zone_limit_appetite)
    retro_limit = min(line_limit, excess)
    retro_cost = retro_limit * p.retro_rol
    relief = p.retro_capital_relief * (retro_limit / line_limit) if line_limit > 0 else 0.0
    net_cap = standalone_cap * (1 - relief)

    # Diversified marginal capital against the existing portfolio
    cp = p.capital
    marginal_cap = sqrt(cp**2 + net_cap**2 + 2 * d.correlation * cp * net_cap) - cp if net_cap > 0 else 0.0

    profit = prem - exp_loss - acq_exp + invest - retro_cost
    econ_profit = profit - p.hurdle_roe * marginal_cap
    roe = profit / marginal_cap if marginal_cap > 0 else 0.0
    return dict(
        share=share, premium=prem, expected_loss=exp_loss, profit=profit,
        marginal_capital=marginal_cap, standalone_capital=standalone_cap,
        econ_profit=econ_profit, roe=roe, retro_limit=retro_limit,
        retro_cost=retro_cost, line_limit=line_limit,
    )


def curve(d: DealInputs, p: PortfolioInputs, steps: int = 100) -> list[dict]:
    return [_evaluate(d, p, d.max_line * i / steps) for i in range(1, steps + 1)]


def _optimal(d: DealInputs, p: PortfolioInputs, premium: float | None = None) -> dict:
    best = None
    for i in range(1, 201):
        r = _evaluate(d, p, d.max_line * i / 200, premium)
        if best is None or r["econ_profit"] > best["econ_profit"]:
            best = r
    return best


def _walk_away(d: DealInputs, p: PortfolioInputs) -> float:
    """Lowest 100% premium at which the best line still earns the hurdle ROE."""
    lo, hi = 0.0, d.premium * 5 + d.expected_loss * 5
    for _ in range(50):
        mid = (lo + hi) / 2
        if _optimal(d, p, mid)["econ_profit"] >= 0:
            hi = mid
        else:
            lo = mid
    return hi


def template_narrative(rec: dict) -> str:
    verdict = "write" if rec["writable"] else "not write"
    text = (
        f"Recommendation: {verdict} this risk"
        + (f" at a {rec['optimal_line']:.1%} line ({rec['optimal_line_limit']:,.0f} limit)" if rec["writable"] else "")
        + f". Walk away above a 100% premium below {rec['walk_away_price']:,.0f}. "
    )
    if rec["writable"]:
        text += (
            f"It consumes {rec['capital_consumed']:,.0f} of capital ({rec['capital_pct_of_portfolio']:.2%} of the portfolio), "
            f"moving portfolio ROE from {rec['roe_before']:.1%} to {rec['roe_after']:.1%} ({rec['roe_impact_bps']:+.0f} bps). "
        )
        if rec["retro_required"] > 0:
            text += f"Buy {rec['retro_required']:,.0f} of retro (cost {rec['retro_cost']:,.0f}) to stay within zone appetite."
        else:
            text += "No retro is required."
    return text


def ai_narrative(rec: dict) -> tuple[str, bool]:
    """Return (narrative, used_llm). Falls back to the template when no key/API is available."""
    import os

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return template_narrative(rec), False
    try:
        from openai import OpenAI

        facts = {k: v for k, v in rec.items() if k != "inputs"}
        resp = OpenAI(api_key=key).chat.completions.create(
            model=os.environ.get("DECISION_LLM_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            messages=[
                {"role": "system", "content": (
                    "You are a reinsurance underwriting analyst. Explain the engine's recommendation to an "
                    "underwriter in under 150 words. Use only the figures provided; do not invent numbers or "
                    "change the decision.")},
                {"role": "user", "content": str(facts)},
            ],
        )
        return resp.choices[0].message.content.strip(), True
    except Exception:
        return template_narrative(rec), False


def recommend(d: DealInputs, p: PortfolioInputs) -> dict:
    opt = _optimal(d, p)
    walk = _walk_away(d, p)
    share = opt["share"]
    writable = opt["econ_profit"] > 0 and share >= d.min_line and opt["roe"] >= p.hurdle_roe

    if not writable:
        decision = "DON'T WRITE"
    elif share < d.max_line * 0.5:
        decision = "WRITE (REDUCED LINE)"
    else:
        decision = "WRITE"

    cp, pp = p.capital, p.expected_profit
    roe_before = pp / cp if cp else 0.0
    if writable:
        roe_after = (pp + opt["profit"]) / (cp + opt["marginal_capital"])
        used, cap_used = opt["marginal_capital"], opt["marginal_capital"]
        line_share = share
    else:
        roe_after, used, cap_used, line_share = roe_before, 0.0, 0.0, 0.0
    zone_after = d.zone_limit_used + (opt["line_limit"] if writable else 0.0) - (opt["retro_limit"] if writable else 0.0)

    reasons = []
    reasons.append(
        f"Deal ROE {opt['roe']:.1%} vs hurdle {p.hurdle_roe:.1%} at the optimal {share:.1%} line."
    )
    if d.premium < walk:
        reasons.append(f"Quoted premium is {1 - d.premium / walk:.1%} below the walk-away price.")
    else:
        reasons.append(f"Quoted premium clears the walk-away price by {d.premium / walk - 1:.1%}.")
    if opt["retro_limit"] > 0:
        reasons.append(f"Zone appetite is breached, so {opt['retro_limit']:,.0f} of retro is needed.")
    if d.correlation > 0.6:
        reasons.append("High correlation to the portfolio is eroding diversification benefit.")

    return dict(
        decision=decision, writable=writable,
        optimal_line=line_share, optimal_line_limit=opt["line_limit"] if writable else 0.0,
        walk_away_price=walk, walk_away_rol=walk / d.limit if d.limit else 0.0,
        capital_consumed=cap_used, capital_pct_of_portfolio=cap_used / cp if cp else 0.0,
        standalone_capital=opt["standalone_capital"] if writable else 0.0,
        diversification_benefit=(opt["standalone_capital"] - opt["marginal_capital"]) if writable else 0.0,
        retro_required=opt["retro_limit"] if writable else 0.0,
        retro_cost=opt["retro_cost"] if writable else 0.0,
        deal_roe=opt["roe"], deal_profit=opt["profit"] if writable else 0.0,
        roe_before=roe_before, roe_after=roe_after, roe_impact_bps=(roe_after - roe_before) * 10_000,
        zone_utilisation_before=d.zone_limit_used / d.zone_limit_appetite if d.zone_limit_appetite else 0.0,
        zone_utilisation_after=zone_after / d.zone_limit_appetite if d.zone_limit_appetite else 0.0,
        reasons=reasons, inputs=asdict(d),
    )
