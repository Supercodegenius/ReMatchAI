"""Treaty Impact Simulator: before/after effect of a limit and rate change on the whole book."""
from __future__ import annotations

import re
from math import sqrt

import pandas as pd

ZONE_APPETITE = {  # limit appetite by peak zone
    "US Gulf / Southeast": 120e6, "US Northeast": 90e6, "Europe": 110e6, "Asia-Pacific": 100e6,
    "Global marine": 90e6, "Global aviation": 70e6,
}
LINE_DEFAULT = {  # rate on line, expected loss ratio, volatility (stdev / EL), commission, zone
    "Casualty": dict(rol=0.16, lr=0.72, cov=2.0, comm=0.15, zone="US Northeast"),
    "Property": dict(rol=0.12, lr=0.45, cov=3.0, comm=0.12, zone="US Gulf / Southeast"),
    "Aviation": dict(rol=0.10, lr=0.60, cov=2.8, comm=0.15, zone="Global aviation"),
    "Marine": dict(rol=0.12, lr=0.58, cov=2.0, comm=0.20, zone="Global marine"),
}
ECON = dict(expense=0.03, yld=0.04, tail=2.6, hurdle=0.12, own_funds_factor=1.8)
RHO_SAME_LINE, RHO_OTHER = 0.5, 0.15


def demo_portfolio() -> pd.DataFrame:
    rows = [
        ("Atlas Mutual", "Property", "US Gulf / Southeast", 60e6, 7.2e6, 0.12),
        ("Atlas Mutual", "Casualty", "US Northeast", 30e6, 4.8e6, 0.15),
        ("Borealis Re Cedant", "Casualty", "US Northeast", 40e6, 6.4e6, 0.15),
        ("Borealis Re Cedant", "Marine", "Global marine", 25e6, 3.0e6, 0.20),
        ("Cobalt Specialty", "Aviation", "Global aviation", 30e6, 3.0e6, 0.15),
        ("Cobalt Specialty", "Marine", "Global marine", 20e6, 2.4e6, 0.20),
        ("Delta General", "Property", "Europe", 50e6, 6.0e6, 0.12),
        ("Delta General", "Property", "US Gulf / Southeast", 45e6, 5.4e6, 0.12),
        ("Everest Regional", "Marine", "Global marine", 15e6, 1.8e6, 0.20),
        ("XYZ Insurance", "Marine", "Global marine", 30e6, 3.6e6, 0.20),
        ("XYZ Insurance", "Property", "Asia-Pacific", 40e6, 4.8e6, 0.12),
        ("Greenfield Re", "Casualty", "Europe", 35e6, 5.6e6, 0.15),
        ("Harbor Specialty", "Aviation", "Global aviation", 25e6, 2.5e6, 0.15),
        ("Ionic Mutual", "Property", "Asia-Pacific", 55e6, 6.6e6, 0.12),
    ]
    d = pd.DataFrame(rows, columns=["cedant", "line", "zone", "limit", "premium", "commission_pct"])
    d["lr"] = d["line"].map(lambda ln: LINE_DEFAULT[ln]["lr"])
    d["cov"] = d["line"].map(lambda ln: LINE_DEFAULT[ln]["cov"])
    return d


PORTFOLIO_COLUMNS = ["cedant", "line", "zone", "limit", "premium", "commission_pct", "lr", "cov"]
FRIENDLY_COLUMNS = {"lr": "expected_loss_ratio", "cov": "loss_volatility_cov"}


def portfolio_template_csv() -> str:
    return demo_portfolio()[PORTFOLIO_COLUMNS].rename(columns=FRIENDLY_COLUMNS).to_csv(index=False)


def load_portfolio(df: pd.DataFrame) -> tuple[pd.DataFrame | None, str]:
    """Validate an uploaded book. lr, cov, commission_pct and zone are optional (defaults by class)."""
    d = df.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    d = d.rename(columns={v: k for k, v in FRIENDLY_COLUMNS.items()})
    missing = [c for c in ("cedant", "line", "limit", "premium") if c not in d.columns]
    if missing:
        return None, "Missing required column(s): " + ", ".join(missing)
    d["line"] = d["line"].astype(str).str.strip().str.title()
    bad = sorted(set(d["line"]) - set(LINE_DEFAULT))
    if bad:
        return None, "Unknown class(es): " + ", ".join(bad) + ". Use Casualty, Property, Aviation or Marine."
    for c in ("limit", "premium"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["limit", "premium"])
    d = d[(d["limit"] > 0) & (d["premium"] > 0)]
    if d.empty:
        return None, "No valid rows (limit and premium must be positive numbers)."
    defaults = {"zone": "zone", "commission_pct": "comm", "lr": "lr", "cov": "cov"}
    for col, key in defaults.items():
        if col not in d.columns:
            d[col] = None
        d[col] = [v if pd.notna(v) and v != "" else LINE_DEFAULT[ln][key] for v, ln in zip(d[col], d["line"])]
        if col != "zone":
            d[col] = pd.to_numeric(d[col], errors="coerce").fillna(0.0)
    return d[PORTFOLIO_COLUMNS].reset_index(drop=True), f"Loaded {len(d)} treaties."


def _metrics(p: pd.DataFrame) -> dict:
    el = p["premium"] * p["lr"]
    sd = el * p["cov"]
    profit = (p["premium"] * (1 - p["commission_pct"] - ECON["expense"] + ECON["yld"]) - el).sum()
    lines = p["line"].to_numpy()
    s = sd.to_numpy()
    var = 0.0
    for i in range(len(s)):
        for j in range(len(s)):
            rho = 1.0 if i == j else (RHO_SAME_LINE if lines[i] == lines[j] else RHO_OTHER)
            var += rho * s[i] * s[j]
    stdev = sqrt(var)
    capital = ECON["tail"] * stdev
    zones = p.groupby("zone")["limit"].sum()
    util = {z: float(v) / ZONE_APPETITE.get(z, 100e6) for z, v in zones.items()}
    peak = max(util, key=util.get)
    return dict(limit=float(p["limit"].sum()), premium=float(p["premium"].sum()), expected_loss=float(el.sum()),
                profit=float(profit), capital=capital, roe=profit / capital if capital else 0.0, stdev=stdev,
                loss_1_in_100=float(el.sum()) + 2.33 * stdev, zone_util=util, peak_zone=peak,
                peak_util=util[peak])


def simulate(port: pd.DataFrame, cedant: str, line: str, limit_delta: float, rate_change: float,
             blended_lr: float | None = None, zone: str | None = None) -> dict:
    """rate_change is relative (-0.05 = 5% lower rate on line). Returns before/after metrics and the changed treaty."""
    base = port.copy()
    mask = (base["cedant"].str.lower().str.contains(cedant.lower(), regex=False)) & (base["line"] == line) \
        if cedant else (base["line"] == line)
    if zone:
        mask &= base["zone"] == zone
    d = LINE_DEFAULT[line]
    if mask.any():
        idx = base.index[mask][0] if mask.sum() == 1 else base.loc[mask, "limit"].idxmax()
        row = base.loc[idx]
        old_rol = row["premium"] / row["limit"]
        new_limit = max(0.0, row["limit"] + limit_delta)
        new_prem = new_limit * old_rol * (1 + rate_change)
        # expected loss per unit limit stays at the old technical level (or the cedant's blended record)
        el_per_limit = (blended_lr if blended_lr is not None else row["lr"]) * old_rol
        after = base.copy()
        after.loc[idx, ["limit", "premium"]] = [new_limit, new_prem]
        after.loc[idx, "lr"] = el_per_limit * new_limit / new_prem if new_prem else 0.0
        treaty = dict(cedant=row["cedant"], line=line, zone=row["zone"], new=False)
    else:
        new_limit = max(0.0, limit_delta)
        new_prem = new_limit * d["rol"] * (1 + rate_change)
        el_per_limit = (blended_lr if blended_lr is not None else d["lr"]) * d["rol"]
        name = cedant.strip() or "New cedant"
        new_row = dict(cedant=name, line=line, zone=zone or d["zone"], limit=new_limit, premium=new_prem,
                       commission_pct=d["comm"], lr=el_per_limit * new_limit / new_prem if new_prem else 0.0, cov=d["cov"])
        after = pd.concat([base, pd.DataFrame([new_row])], ignore_index=True)
        treaty = dict(cedant=name, line=line, zone=new_row["zone"], new=True)
    b, a = _metrics(base), _metrics(after)
    own_funds = b["capital"] * ECON["own_funds_factor"]  # fixed available capital, sized at 180% cover today
    b["solvency_ratio"], a["solvency_ratio"] = own_funds / b["capital"], own_funds / a["capital"]
    dcap = a["capital"] - b["capital"]
    return dict(before=b, after=a, treaty=treaty, marginal_roe=(a["profit"] - b["profit"]) / dcap if dcap > 1 else float("nan"),
                hurdle=ECON["hurdle"])


def parse_change(text: str, port: pd.DataFrame) -> dict | None:
    """Parse e.g. '+25m limit, -5% rate, cedant XYZ, class Marine'. Needs a line and a limit or rate change."""
    t = text.lower().replace(":", " ").replace("\n", ", ")
    line = next((ln for ln in LINE_DEFAULT if ln.lower() in t), None)
    if line is None:
        return None
    lim = re.search(r"([+-]?)\s*\$?(\d+(?:\.\d+)?)\s*(k|m|mm|mn|bn|b)?\s*(?:of\s+)?limit|limit\s*([+-]?)\s*\$?(\d+(?:\.\d+)?)\s*(k|m|mm|mn|bn|b)?", t)
    delta = None
    if lim:
        sign = lim.group(1) or lim.group(4) or "+"
        num, suf = (lim.group(2), lim.group(3)) if lim.group(2) else (lim.group(5), lim.group(6))
        delta = float(num) * {"k": 1e3, "m": 1e6, "mm": 1e6, "mn": 1e6, "b": 1e9, "bn": 1e9}.get(suf or "", 1.0)
        delta = -delta if sign == "-" else delta
    rate = re.search(r"rate\s*(?:change)?\s*([+-]?\s*\d+(?:\.\d+)?)\s*%|([+-]\s*\d+(?:\.\d+)?)\s*%\s*rate", t)
    rc = None
    if rate:
        rc = float((rate.group(1) or rate.group(2)).replace(" ", "")) / 100.0
    if delta is None and rc is None:
        return None
    ced = re.search(r"cedant\s*[:=]?\s*([a-z0-9&.\- ]+?)(?:,|;|\bclass\b|\bline\b|\blimit\b|\brate\b|$)", t)
    cedant = ced.group(1).strip() if ced else ""
    return dict(cedant=cedant, line=line, limit_delta=delta or 0.0, rate_change=rc or 0.0)


def summary(res: dict, req: dict) -> str:
    b, a, t = res["before"], res["after"], res["treaty"]
    verdict = "improves" if a["roe"] > b["roe"] else "dilutes"
    mroe = res["marginal_roe"]
    mtxt = f"{mroe:.1%} marginal ROE on the added capital" if mroe == mroe else "no added capital"
    ok = "above" if mroe == mroe and mroe >= res["hurdle"] else "below"
    return (
        f"**{t['cedant']} - {t['line']}**: limit {req['limit_delta']:+,.0f}, rate {req['rate_change']:+.0%}"
        f"{' (new treaty)' if t['new'] else ''}.\n\n"
        f"- Portfolio ROE {b['roe']:.1%} -> **{a['roe']:.1%}**, so the change {verdict} returns "
        f"({mtxt}, {ok} the {res['hurdle']:.0%} hurdle).\n"
        f"- Capital consumption {b['capital']:,.0f} -> {a['capital']:,.0f} ({a['capital'] - b['capital']:+,.0f}).\n"
        f"- Earnings volatility {b['stdev']:,.0f} -> {a['stdev']:,.0f}; 1-in-100 loss {a['loss_1_in_100']:,.0f}.\n"
        f"- Solvency cover {b['solvency_ratio']:.0%} -> {a['solvency_ratio']:.0%} (own funds held constant).\n"
        f"- Peak zone {a['peak_zone']} at {a['peak_util']:.0%} of appetite (was {b['peak_zone']} {b['peak_util']:.0%}).\n"
        f"- Net portfolio: premium {a['premium'] - b['premium']:+,.0f}, expected profit {a['profit'] - b['profit']:+,.0f}, "
        f"limit {a['limit'] - b['limit']:+,.0f}.")
