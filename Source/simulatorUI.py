import streamlit as st

import importlib

import simulator_engine as se

se = importlib.reload(se)

from cedant_engine import demo_history, score_cedants

st.title("Re Copilot")
st.subheader("Treaty Impact Simulator")
st.caption("Change a limit and a rate on one cedant and class, and see the effect on the whole book.")

import pandas as pd

port = se.demo_portfolio()
with st.expander("Use your own book (upload)"):
    st.download_button("Download portfolio template", se.portfolio_template_csv(),
                       "portfolio_template.csv", "text/csv")
    up = st.file_uploader("Portfolio CSV", type="csv")
    if up is not None:
        loaded, msg = se.load_portfolio(pd.read_csv(up))
        if loaded is None:
            st.error(msg)
        else:
            st.success(msg)
            port = loaded
st.session_state["sim_portfolio"] = port
scores = st.session_state.get("cedant_scores")
if scores is None or "line" not in scores.columns:
    scores = score_cedants(demo_history())


def card(col, title, value, delta=""):
    col.markdown(f'<div class="dec-card"><h4>{title}</h4><p>{value}</p><small>{delta}</small></div>',
                 unsafe_allow_html=True)


c1, c2, c3, c4 = st.columns(4)
limit_delta = c1.number_input("Limit change ($m)", -200.0, 500.0, 25.0, 5.0) * 1e6
rate_pct = c2.number_input("Rate change (%)", -50.0, 50.0, -5.0, 1.0)
names = sorted(port["cedant"].unique())
cedant = c3.selectbox("Cedant", names + ["(new cedant)"],
                      index=names.index("XYZ Insurance") if "XYZ Insurance" in names else 0)
line = c4.selectbox("Class", list(se.LINE_DEFAULT), index=list(se.LINE_DEFAULT).index("Marine"))
new_name = ""
if cedant == "(new cedant)":
    new_name = st.text_input("New cedant name", "New cedant")

name = new_name if cedant == "(new cedant)" else cedant
hit = scores[(scores["cedant"].str.lower() == name.lower()) & (scores["line"] == line)]
blended = float(hit["blended_loss_ratio"].iloc[0]) if len(hit) else None
res = se.simulate(port, name, line, limit_delta, rate_pct / 100.0, blended_lr=blended)
b, a = res["before"], res["after"]
if blended is not None:
    st.caption(f"Using {name}'s blended {line.lower()} loss ratio of {blended:.0%} from the cedant scores.")
else:
    st.caption(f"No cedant history for {name} in {line.lower()}; using the {line.lower()} market loss ratio.")

verdict_ok = a["roe"] >= b["roe"] and a["peak_util"] <= 1.0
st.markdown(f"**{'Looks acceptable' if verdict_ok else 'Review before writing'}**: portfolio ROE "
            f"{b['roe']:.1%} to {a['roe']:.1%}, peak zone at {a['peak_util']:.0%} of appetite.")

r1 = st.columns(3)
card(r1[0], "Net portfolio impact", f"{a['profit'] - b['profit']:+,.0f}",
     f"expected profit; premium {a['premium'] - b['premium']:+,.0f}")
card(r1[1], "Peak zone movement", f"{a['peak_util']:.0%}", f"{a['peak_zone']} (was {b['peak_zone']} {b['peak_util']:.0%})")
card(r1[2], "Capital consumption", f"{a['capital'] - b['capital']:+,.0f}", f"total {a['capital']:,.0f}")
r2 = st.columns(3)
card(r2[0], "Expected ROE", f"{a['roe']:.1%}", f"was {b['roe']:.1%}; marginal {res['marginal_roe']:.1%}")
card(r2[1], "Earnings volatility", f"{a['stdev']:,.0f}", f"was {b['stdev']:,.0f}; 1-in-100 loss {a['loss_1_in_100']:,.0f}")
card(r2[2], "Solvency capital effect", f"{a['solvency_ratio']:.0%}", f"cover, was {b['solvency_ratio']:.0%}")

with st.expander("Zone utilisation before and after"):
    z =  pd.DataFrame({"before": b["zone_util"], "after": a["zone_util"]}).fillna(0)
    st.bar_chart(z)
with st.expander("Assumptions"):
    st.write("Demo portfolio of 14 treaties unless you upload your own; volatility = expected loss x class volatility; treaties in the same class "
             "correlate at 0.5, others at 0.15; capital = 2.6 x portfolio standard deviation; own funds held at "
             "180% of today's capital. Replace with your own book and parameters.")
st.dataframe(port.rename(columns={
    "cedant": "Cedant", "line": "Line of business", "zone": "Zone", "limit": "Limit", "premium": "Premium",
    "commission_pct": "Commission %", "lr": "Expected loss ratio", "cov": "Loss volatility (CoV)"}),
    use_container_width=True, hide_index=True)
