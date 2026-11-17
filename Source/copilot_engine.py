"""Reinsurance Copilot: turns a free-text submission or question into deal inputs and a plain-English answer."""
import re

_STOP = {"xl", "xol", "of", "and", "lines", "line", "share", "loss", "regional", "insurer", "large", "personal",
         "us", "excess", "specialty", "stop", "aggregate", "health", "xs"}
_SYNONYMS = {"qs": "quota", "catastrophe": "cat", "natcat": "cat", "d&o": "d&o", "do": "d&o", "pi": "indemnity",
             "per": "per-risk", "terror": "terrorism", "political": "terrorism", "surplus": "surplus",
             "energy": "marine", "auto": "motor", "cargo": "marine", "space": "aviation", "crop": "agriculture"}
_MULT = {"k": 1e3, "m": 1e6, "mm": 1e6, "mn": 1e6, "b": 1e9, "bn": 1e9}
_AMT = r"(\d+(?:[.,]\d+)*)\s*(k|mm|mn|m|bn|b)?\b"


def _amount(num: str, suffix: str | None) -> float:
    return float(num.replace(",", "")) * _MULT.get((suffix or "").lower(), 1.0)


def _find(text: str, labels: str, pct: bool = False):
    pat = rf"(?:{labels})\s*(?:of|is|at|=|:)?\s*\$?€?£?\s*" + (r"(\d+(?:\.\d+)?)\s*%" if pct else _AMT)
    m = re.search(pat, text)
    if not m:
        return None
    return float(m.group(1)) if pct else _amount(m.group(1), m.group(2))


def match_profile(text: str, profiles: list[str]) -> str | None:
    words = set(re.findall(r"[a-z&\-]+", text.lower()))
    words |= {_SYNONYMS[w] for w in words if w in _SYNONYMS}
    best, best_score = None, 0
    for name in profiles:
        toks = {w for w in re.findall(r"[a-z&\-]+", name.lower()) if len(w) > 1 and w not in _STOP}
        score = len(toks & words)
        if score > best_score:
            best, best_score = name, score
    return best


def parse(text: str, profiles: list[str]) -> dict:
    """Return session-state updates: buyer_profile, limit, premium, lr (%), max_line (fraction), plus rol."""
    t = text.lower()
    out: dict = {}
    prof = match_profile(t, profiles)
    if prof:
        out["buyer_profile"] = prof
    lim = _find(t, r"limit|lim|layer")
    if lim is None:
        m = re.search(_AMT + r"\s*(?:xs|x/s|excess)", t)
        lim = _amount(m.group(1), m.group(2)) if m else None
    if lim:
        out["limit"] = lim
    prem = _find(t, r"premium|prem|quote|quoted|price|priced at|gnpi")
    if prem:
        out["premium"] = prem
    rol = _find(t, r"rol|rate on line", pct=True)
    if rol:
        out["rol_pct"] = rol
    lr = _find(t, r"elr|expected loss ratio|loss ratio|expected lr|lr|expected loss", pct=True)
    if lr:
        out["lr"] = lr
    ml = _find(t, r"max(?:imum)? line|max share|offered|written line|line size|line", pct=True)
    if ml:
        out["max_line"] = ml / 100.0
    return out


def answer(rec: dict, deal, port, question: str, changed: list[str]) -> str:
    q = question.lower()
    gap = deal.premium / rec["walk_away_price"] - 1 if rec["walk_away_price"] else 0
    head = ("**" + rec["decision"] + "**")
    if changed:
        head += "  \nUsing: " + ", ".join(changed)
    if any(w in q for w in ("walk", "price", "rate", "minimum")) and not _wants_all(q):
        body = (f"Walk-away price is **{rec['walk_away_price']:,.0f}** for 100% "
                f"({rec['walk_away_rol']:.2%} rate on line). The quote of {deal.premium:,.0f} is "
                f"{abs(gap):.0%} {'above' if gap >= 0 else 'below'} it.")
    elif "retro" in q:
        body = (f"Retro needed: **{rec['retro_required']:,.0f}** of limit, costing about "
                f"{rec['retro_cost']:,.0f}. Zone use goes {rec['zone_utilisation_before']:.0%} to "
                f"{rec['zone_utilisation_after']:.0%}.")
    elif "capital" in q:
        body = (f"Capital used: **{rec['capital_consumed']:,.0f}** "
                f"({rec['capital_pct_of_portfolio']:.2%} of portfolio capital), with "
                f"{rec['diversification_benefit']:,.0f} diversification benefit.")
    elif "roe" in q or "portfolio" in q:
        body = (f"Portfolio ROE moves **{rec['roe_before']:.1%} to {rec['roe_after']:.1%}** "
                f"({rec['roe_impact_bps']:+.0f} bps). Deal ROE is {rec['deal_roe']:.1%} against a "
                f"{port.hurdle_roe:.1%} hurdle.")
    elif "why" in q or "reason" in q or "explain" in q:
        body = "\n".join(f"- {r}" for r in rec["reasons"])
    else:
        if rec["writable"]:
            body = (f"Write **{rec['optimal_line']:.1%}** ({rec['optimal_line_limit']:,.0f}). Walk-away price "
                    f"**{rec['walk_away_price']:,.0f}** (quote is {abs(gap):.0%} "
                    f"{'above' if gap >= 0 else 'below'}). Uses {rec['capital_consumed']:,.0f} capital, portfolio "
                    f"ROE {rec['roe_before']:.1%} to {rec['roe_after']:.1%}, retro needed "
                    f"{rec['retro_required']:,.0f}.")
        else:
            body = (f"The quote is {abs(gap):.0%} below the walk-away price of "
                    f"**{rec['walk_away_price']:,.0f}**. Push for more rate or decline.")
        body += "\n\n" + "\n".join(f"- {r}" for r in rec["reasons"][:3])
    return f"{head}\n\n{body}"


def _wants_all(q: str) -> bool:
    return any(w in q for w in ("retro", "capital", "roe"))


HELP = ("Describe a submission, for example: *Casualty XL US liability, limit 10m, premium 1.6m, loss ratio 68%, "
        "max line 25%*. Then ask follow-ups such as *what is the walk-away price?*, *how much retro?*, "
        "*what if premium is 2m?*")
