import os
import sys

from dataclasses import replace

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from decision_engine import BUYER_PROFILES, DEFAULT_PROFILE, DealInputs, PortfolioInputs, ai_narrative, curve, recommend  # noqa: E402
import copilot_engine as cp  # noqa: E402
import simulator_engine as se  # noqa: E402
from cedant_engine import demo_history, score_cedants, template_csv, validate  # noqa: E402

PAGES = {
    "reinsights": "ReInsights",
    "simulator": "Simulator",
    "treaty": "Treaty Summary",
    "decision": "Line Size",
    "decision_ai": "Recommendation",
    "cedants": "Cedants",
}
page = st.query_params.get("page", "reinsights")
if page == "copilot":
    page = "reinsights"
if page not in PAGES:
    page = "reinsights"


def _go(target: str) -> None:
    st.query_params["page"] = target
    st.rerun()


# ---- Menu ----
st.markdown(
    "<style>.block-container{padding-top:1.5rem;max-width:1200px;margin:0 auto}"
    ".dec-card{border:1px solid #e3e6ee;border-radius:12px;padding:14px 16px;background:#fff}"
    ".dec-card h4{margin:0;color:#667;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}"
    ".dec-card p{margin:4px 0 0;font-size:1.5rem;font-weight:700;color:#14213d}"
    ".dec-badge{display:inline-block;padding:10px 22px;border-radius:999px;color:#fff;font-weight:800;font-size:1.6rem}"
    "</style>",
    unsafe_allow_html=True,
)
menu = st.columns([1.6, 1.2, 1.3, 1.5, 1.3, 1.5, 1.2])
st.markdown(
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&"
    "family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');"
    "html,body,.stApp,div[data-testid='stAppViewContainer'],div[data-testid='stMain'],section.main"
    "{background:#f3f4f6 !important;font-family:'Plus Jakarta Sans',sans-serif}"
    "div[data-testid='stHeader'],header[data-testid='stHeader'],div[data-testid='stToolbar'],"
    "div[data-testid='stDecoration'],#MainMenu,footer{display:none !important}"
    "h1,h2,h3,h4{font-family:'Manrope',sans-serif;color:#12131a}"
    "div[data-testid='stButton']>button,div[data-testid='stDownloadButton']>button,"
    "div[data-testid='stFormSubmitButton']>button"
    "{height:2.9rem;white-space:nowrap;padding:0 1rem;border-radius:.6rem;border:1px solid rgba(0,0,0,.05);"
    "background:linear-gradient(180deg,#0f62ff,#084dce);color:#fff;font-weight:700;letter-spacing:.01em;"
    "box-shadow:0 8px 16px rgba(15,98,255,.28)}"
    "div[data-testid='stButton']>button p,div[data-testid='stDownloadButton']>button p,"
    "div[data-testid='stFormSubmitButton']>button p{color:#fff;font-weight:700}"
    "div[data-testid='stButton']>button:hover,div[data-testid='stDownloadButton']>button:hover,"
    "div[data-testid='stFormSubmitButton']>button:hover{background:linear-gradient(180deg,#2a74ff,#0a58e0);"
    "border-color:rgba(0,0,0,.05);color:#fff}"
    "div[data-testid='stButton']>button[kind='primary']{box-shadow:0 0 0 3px rgba(15,98,255,.25),"
    "0 8px 16px rgba(15,98,255,.28)}"
    "</style>",
    unsafe_allow_html=True,
)
if menu[0].button("Back To Landing", use_container_width=True):
    st.query_params.clear()
    st.rerun()
for col, (key, label) in zip(menu[1:], PAGES.items()):
    if col.button(label, use_container_width=True, type="primary" if key == page else "secondary"):
        _go(key)

if page == "treaty":
    import runpy
    runpy.run_path(os.path.join(os.path.dirname(__file__), "treatyUI.py"), run_name="__main__")
    st.stop()

if page == "simulator":
    import runpy
    runpy.run_path(os.path.join(os.path.dirname(__file__), "simulatorUI.py"), run_name="__main__")
    st.stop()

# ---- Shared inputs (persist across the two pages via session_state) ----
d0, p0 = DealInputs(), PortfolioInputs()

# session key -> DealInputs field, so a buyer preset can fill every deal input at once
_KEYS = dict(
    limit="limit", premium="premium", exp_loss="expected_loss", cov="loss_cov", comm="commission_pct",
    expense="expense_pct", yld="investment_yield", max_line="max_line", min_line="min_line",
    corr="correlation", zone_used="zone_limit_used", zone_app="zone_limit_appetite",
    dq="data_quality_load",
)


def _apply_profile() -> None:
    prof_vals = BUYER_PROFILES[st.session_state["buyer_profile"]]
    for key, field in _KEYS.items():
        st.session_state[key] = prof_vals[field]
    st.session_state["lr"] = round(100 * prof_vals["expected_loss"] / prof_vals["premium"], 1)


if "buyer_profile" not in st.session_state:
    st.session_state["buyer_profile"] = DEFAULT_PROFILE
    _apply_profile()
for _k, _v in dict(cap=p0.capital, prof=p0.expected_profit, hurdle=p0.hurdle_roe, rol=p0.retro_rol,
                   tail=p0.tail_multiple).items():
    st.session_state.setdefault(_k, _v)


_pend = st.session_state.pop("_pending", None)
if _pend:
    if "buyer_profile" in _pend:
        st.session_state["buyer_profile"] = _pend["buyer_profile"]
        _apply_profile()
    for _k in ("limit", "premium", "lr", "max_line"):
        if _k in _pend:
            st.session_state[_k] = _pend[_k]
    if "rol_pct" in _pend:
        st.session_state["premium"] = st.session_state["limit"] * _pend["rol_pct"] / 100.0


def _num(container, label, key, _default=None, **kw):
    return container.number_input(label, key=key, **kw)


box = st.expander("Submission details", expanded=page != "reinsights")
box.markdown("##### 1. Describe the submission")
box.selectbox(
    "Treaty / buyer type", list(BUYER_PROFILES), key="buyer_profile", on_change=_apply_profile,
    help="Pre-fills sensible market assumptions, so you only enter what you know from the submission.",
)
e1, e2, e3, e4 = box.columns(4)
limit = _num(e1, "Limit (100%)", "limit", step=1_000_000.0, min_value=1.0, format="%.0f")
premium = _num(e2, "Premium (100%)", "premium", step=50_000.0, min_value=1.0, format="%.0f")
lr_pct = _num(e3, "Expected loss ratio %", "lr", step=1.0, min_value=1.0, max_value=300.0, format="%.1f",
              help="Your technical expected loss as % of premium.")
max_line = _num(e4, "Max line offered", "max_line", step=0.05, min_value=0.01, max_value=1.0, format="%.2f",
                help="Largest share of the treaty you could be given (1.00 = 100%).")
exp_loss = max(1.0, premium * lr_pct / 100.0)
st.session_state["exp_loss"] = exp_loss
box.caption(f"Rate on line {premium / limit:.1%}  |  Expected loss {exp_loss:,.0f}")

with st.expander("Fine-tune assumptions (optional - pre-filled from the treaty type)"):
    c1, c2, c3 = st.columns(3)
    cov = _num(c1, "Loss volatility (CoV)", "cov", step=0.1, min_value=0.1)
    comm = _num(c1, "Commission + brokerage", "comm", step=0.01, min_value=0.0, max_value=0.9)
    expense = _num(c1, "Internal expenses", "expense", step=0.005, min_value=0.0, max_value=0.5)
    yld = _num(c1, "Investment yield", "yld", step=0.01, min_value=0.0, max_value=0.5)
    dq = _num(c1, "Data-quality loading", "dq", step=0.01, min_value=0.0, max_value=0.5)
    min_line = _num(c2, "Min worthwhile line", "min_line", step=0.005, min_value=0.0, max_value=1.0)
    corr = _num(c2, "Correlation to portfolio", "corr", step=0.05, min_value=-0.5, max_value=1.0)
    zone_used = _num(c2, "Zone limit used", "zone_used", step=1_000_000.0, min_value=0.0)
    zone_app = _num(c2, "Zone limit appetite", "zone_app", step=1_000_000.0, min_value=1.0)
    cap = _num(c3, "Portfolio capital", "cap", step=5_000_000.0, min_value=1.0)
    prof = _num(c3, "Portfolio expected profit", "prof", step=1_000_000.0)
    hurdle = _num(c3, "Hurdle ROE", "hurdle", step=0.01, min_value=0.0, max_value=1.0)
    rol = _num(c3, "Retro rate on line", "rol", step=0.01, min_value=0.0, max_value=1.0)
    tail = _num(c3, "Tail multiple (x stdev)", "tail", step=0.1, min_value=0.5)
deal = DealInputs(
    limit=limit, premium=premium, expected_loss=exp_loss, loss_cov=cov, commission_pct=comm,
    expense_pct=expense, investment_yield=yld, data_quality_load=dq,
    max_line=max_line, min_line=min_line, correlation=corr,
    zone_limit_used=zone_used, zone_limit_appetite=zone_app,
)
port = PortfolioInputs(capital=cap, expected_profit=prof, hurdle_roe=hurdle, retro_rol=rol, tail_multiple=tail)
rec = recommend(deal, port)


def card(col, title, value):
    col.markdown(f'<div class="dec-card"><h4>{title}</h4><p>{value}</p></div>', unsafe_allow_html=True)


def banner() -> None:
    color = "#1b9e5a" if rec["writable"] else "#c62828"
    gap = deal.premium / rec["walk_away_price"] - 1 if rec["walk_away_price"] else 0
    st.markdown(f'<span class="dec-badge" style="background:{color}">{rec["decision"]}</span>', unsafe_allow_html=True)
    if rec["writable"]:
        st.markdown(f"**Write {rec['optimal_line']:.1%} ({rec['optimal_line_limit']:,.0f}).** The quote is "
                    f"{abs(gap):.0%} {'above' if gap >= 0 else 'below'} your walk-away price of "
                    f"{rec['walk_away_price']:,.0f}.")
    else:
        st.markdown(f"**The quote is {abs(gap):.0%} below your walk-away price of {rec['walk_away_price']:,.0f}.** "
                    "Push for more rate or walk away.")


if page == "reinsights":
    st.title("Re Copilot")
    st.caption("Describe a submission in plain words. I will recommend write or not, line size, price, capital, retro and ROE.")
    hist = st.session_state.setdefault("copilot_chat", [{"role": "assistant", "content": cp.HELP}])
    for m in hist:
        st.chat_message(m["role"]).markdown(m["content"])
    msg = st.chat_input("e.g. Cyber XL, limit 15m, premium 2.7m, loss ratio 55%")
    if msg:
        book = st.session_state.get("sim_portfolio", se.demo_portfolio())
        sim_req = se.parse_change(msg, book)
        if sim_req:
            sc = st.session_state.get("cedant_scores")
            if sc is None or "line" not in sc.columns:
                sc = score_cedants(demo_history())
            hit = sc[(sc["cedant"].str.lower().str.contains(sim_req["cedant"] or "\0", regex=False)) & (sc["line"] == sim_req["line"])]
            res = se.simulate(book, sim_req["cedant"], sim_req["line"], sim_req["limit_delta"],
                              sim_req["rate_change"], blended_lr=float(hit["blended_loss_ratio"].iloc[0]) if len(hit) else None)
            hist.append({"role": "user", "content": msg})
            hist.append({"role": "assistant", "content": se.summary(res, sim_req)})
            st.rerun()
        upd = cp.parse(msg, list(BUYER_PROFILES))
        vals = {"limit": limit, "premium": premium, "lr": lr_pct, "max_line": max_line}
        new_deal = deal
        if "buyer_profile" in upd and upd["buyer_profile"] != st.session_state["buyer_profile"]:
            bp = BUYER_PROFILES[upd["buyer_profile"]]
            vals = {"limit": bp["limit"], "premium": bp["premium"],
                    "lr": round(100 * bp["expected_loss"] / bp["premium"], 1), "max_line": bp["max_line"]}
            new_deal = replace(deal, loss_cov=bp["loss_cov"], commission_pct=bp["commission_pct"],
                               expense_pct=bp["expense_pct"], investment_yield=bp["investment_yield"],
                               min_line=bp["min_line"], correlation=bp["correlation"],
                               zone_limit_used=bp["zone_limit_used"], zone_limit_appetite=bp["zone_limit_appetite"],
                               data_quality_load=bp["data_quality_load"])
        vals.update({k: v for k, v in upd.items() if k in vals})
        if "rol_pct" in upd:
            vals["premium"] = vals["limit"] * upd["rol_pct"] / 100.0
        new_deal = replace(new_deal, limit=vals["limit"], premium=vals["premium"], max_line=vals["max_line"],
                           expected_loss=max(1.0, vals["premium"] * vals["lr"] / 100.0))
        new_rec = recommend(new_deal, port)
        changed = [f"{k} {v}" for k, v in {"treaty": upd.get("buyer_profile"),
                   "limit": f"{vals['limit']:,.0f}" if "limit" in upd else None,
                   "premium": f"{vals['premium']:,.0f}" if ("premium" in upd or "rol_pct" in upd) else None,
                   "loss ratio": f"{vals['lr']:.1f}%" if "lr" in upd else None,
                   "max line": f"{vals['max_line']:.0%}" if "max_line" in upd else None}.items() if v]
        hist.append({"role": "user", "content": msg})
        hist.append({"role": "assistant", "content": cp.answer(new_rec, new_deal, port, msg, changed)})
        st.session_state["_pending"] = upd
        st.rerun()
    if len(hist) > 1:
        st.divider()
        banner()
elif page == "decision":
    st.title("Re Copilot")
    st.caption("Line size: how much to write and where to stop.")
    banner()
    rows = pd.DataFrame(curve(deal, port))
    rows["Line %"] = rows["share"] * 100
    k = st.columns(3)
    card(k[0], "Optimal line", f"{rec['optimal_line']:.1%}")
    card(k[1], "Walk-away price", f"{rec['walk_away_price']:,.0f}")
    card(k[2], "Deal ROE vs hurdle", f"{rec['deal_roe']:.1%} vs {port.hurdle_roe:.1%}")
    st.subheader("How much to write")
    st.caption("Economic profit after the cost of capital. The peak is the best line size.")
    st.line_chart(rows.set_index("Line %")[["econ_profit"]], height=260)
    with st.expander("Capital and ROE detail"):
        g1, g2 = st.columns(2)
        g1.line_chart(rows.set_index("Line %")[["marginal_capital", "standalone_capital"]])
        g2.line_chart(rows.set_index("Line %")[["roe"]])
    if st.button("See full recommendation", type="primary"):
        _go("decision_ai")
elif page == "decision_ai":
    st.title("Re Copilot")
    st.caption("Recommendation: write or not, at what size and price.")
    banner()
    st.write("")
    r1 = st.columns(3)
    card(r1[0], "Capital it will use", f"{rec['capital_consumed']:,.0f}")
    card(r1[1], "Portfolio ROE", f"{rec['roe_before']:.1%} → {rec['roe_after']:.1%}")
    card(r1[2], "Retro needed", f"{rec['retro_required']:,.0f}")
    st.markdown("**Why**")
    for r in rec["reasons"][:3]:
        st.markdown(f"- {r}")
    text, used_llm = ai_narrative(rec) if os.environ.get("OPENAI_API_KEY") else (None, False)
    if text:
        st.info(text)
    with st.expander("All figures"):
        r2 = st.columns(3)
        card(r2[0], "Line limit", f"{rec['optimal_line_limit']:,.0f}")
        card(r2[1], "Walk-away rate on line", f"{rec['walk_away_rol']:.2%}")
        card(r2[2], "Deal expected profit", f"{rec['deal_profit']:,.0f}")
        st.write("")
        r3 = st.columns(3)
        card(r3[0], "ROE impact", f"{rec['roe_impact_bps']:+.0f} bps")
        card(r3[1], "% of portfolio capital", f"{rec['capital_pct_of_portfolio']:.2%}")
        card(r3[2], "Diversification benefit", f"{rec['diversification_benefit']:,.0f}")
        st.write("")
        r4 = st.columns(3)
        card(r4[0], "Retro cost", f"{rec['retro_cost']:,.0f}")
        card(r4[1], "Zone use", f"{rec['zone_utilisation_before']:.0%} → {rec['zone_utilisation_after']:.0%}")
    if st.button("Back to line-size view"):
        _go("decision")

else:
    st.title("Re Copilot")
    st.subheader("Cedant profitability")
    st.caption("Which buyers make money? Scored from each cedant's own premium, loss development and commission.")
    st.download_button("Download CSV template", template_csv(), file_name="cedant_history_template.csv",
                       mime="text/csv", help="One row per cedant per underwriting year. Amounts in a single currency; commission_pct as a fraction (0.25 = 25%).")
    up = st.file_uploader(
        "Cedant history CSV (columns: cedant, line, year, premium, paid_loss, outstanding_loss, commission_pct; line is optional)", type="csv")
    if up is not None:
        hist = pd.read_csv(up)
        errs = validate(hist)
        if errs:
            st.error("; ".join(errs))
            st.stop()
        st.success(f"Loaded {len(hist)} rows for {hist['cedant'].nunique()} cedants.")
    else:
        hist = demo_history()
        st.warning("Showing synthetic demo data. Upload your own cedant history to score real buyers.")

    a1, a2, a3 = st.columns(3)
    prior = a1.number_input("Market prior loss ratio", 0.3, 1.2, 0.65, 0.01,
                            help="Used to blend with each cedant's own record, weighted by years of data.")
    cpp = a2.number_input("Capital per unit premium", 0.1, 3.0, 0.60, 0.05)
    kcred = a3.number_input("Credibility constant K", 0.5, 10.0, 3.0, 0.5,
                            help="Years of data needed for the cedant's record to carry 50% weight.")
    scores = score_cedants(hist, hurdle_roe=hurdle, prior_loss_ratio=prior, capital_per_premium=cpp,
                           credibility_k=kcred, expense_pct=expense)
    if "line" in scores.columns:
        pick_line = st.radio("Principal line", ["All"] + sorted(scores["line"].unique()), horizontal=True)
        if pick_line != "All":
            scores = scores[scores["line"] == pick_line]
        scores = scores.sort_values(["cedant", "line"]).reset_index(drop=True)
        scores["label"] = scores["cedant"] + " - " + scores["line"]
    else:
        scores = scores.sort_values("cedant").reset_index(drop=True)
        scores["label"] = scores["cedant"]
    st.session_state["cedant_scores"] = scores

    icon = {"Profitable – grow": "🟢", "Keep – at hurdle": "🟡", "Reprice": "🟠", "Reduce / exit": "🔴"}
    show = scores.drop(columns=["label"]).copy()
    show.insert(show.columns.get_loc("cedant") + 1 + ("line" in show.columns), "verdict ", show["verdict"].map(lambda v: f"{icon[v]} {v}"))
    show = show.drop(columns=["verdict"])
    st.dataframe(
        show.style.format({
            "premium": "{:,.0f}", "ultimate_loss": "{:,.0f}", "uw_profit": "{:,.0f}",
            "loss_ratio": "{:.1%}", "blended_loss_ratio": "{:.1%}", "credibility": "{:.0%}",
            "loss_ratio_volatility": "{:.1%}", "combined_ratio": "{:.1%}", "roe": "{:.1%}",
            "forward_roe": "{:.1%}", "rate_change_needed": "{:+.1%}",
        }),
        use_container_width=True, hide_index=True,
    )
    st.bar_chart(scores.set_index("label")[["roe", "forward_roe"]])
    st.caption(
        "Loss ratios are developed to ultimate with indicative factors. Forward ROE uses a credibility-blended loss "
        "ratio, so thin-history cedants are pulled toward the market prior. 'Rate change needed' is the premium "
        "change to reach your hurdle ROE.")

    def _use_in_deal() -> None:
        row = st.session_state["cedant_scores"].set_index("label").loc[st.session_state["cedant_pick"]]
        st.session_state["lr"] = round(float(row["blended_loss_ratio"]) * 100, 1)
        st.session_state["comm"] = float(min(0.9, max(0.0, row["combined_ratio"] - row["loss_ratio"] - st.session_state["expense"])))

    st.selectbox("Cedant", list(scores["label"]), key="cedant_pick")
    st.button("Use this cedant's loss ratio and commission in the deal", on_click=_use_in_deal,
              help="Sets expected loss (blended loss ratio x premium) and commission on the deal inputs.")



