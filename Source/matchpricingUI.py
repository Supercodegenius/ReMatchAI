import os
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import streamlit as st
FAVICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "favicon.png.jpeg")
PRICING_DATA_DIR = Path(__file__).resolve().parent.parent / "outputs" / "pricing"
PRICING_USERS_FILE = PRICING_DATA_DIR / "users.json"
PRICING_USAGE_FILE = PRICING_DATA_DIR / "usage_history.csv"


def _ensure_pricing_storage() -> None:
  PRICING_DATA_DIR.mkdir(parents=True, exist_ok=True)
  if not PRICING_USERS_FILE.exists():
    PRICING_USERS_FILE.write_text("{}", encoding="utf-8")
  if not PRICING_USAGE_FILE.exists():
    with PRICING_USAGE_FILE.open("w", newline="", encoding="utf-8") as handle:
      writer = csv.DictWriter(
        handle,
        fieldnames=[
          "timestamp_utc",
          "email",
          "billing_cycle",
          "plan_name",
          "included_records",
          "usage_records",
          "overage_records",
          "base_subscription",
          "overage_cost",
          "estimated_total",
          "price_per_record",
        ],
      )
      writer.writeheader()


def _load_pricing_users() -> dict[str, dict[str, str]]:
  _ensure_pricing_storage()
  try:
    raw = json.loads(PRICING_USERS_FILE.read_text(encoding="utf-8"))
  except Exception:
    raw = {}
  if not isinstance(raw, dict):
    return {}
  return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _save_pricing_users(users: dict[str, dict[str, str]]) -> None:
  _ensure_pricing_storage()
  PRICING_USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _hash_password(password: str) -> str:
  return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _auth_or_register_user(email: str, password: str) -> tuple[bool, str]:
  users = _load_pricing_users()
  now_iso = datetime.now(timezone.utc).isoformat()
  password_hash = _hash_password(password)
  existing = users.get(email)

  if existing is None:
    users[email] = {
      "password_hash": password_hash,
      "created_at": now_iso,
      "last_login_at": now_iso,
    }
    _save_pricing_users(users)
    return True, "Account created and logged in."

  if str(existing.get("password_hash", "")) != password_hash:
    return False, "Invalid email or password."

  existing["last_login_at"] = now_iso
  users[email] = existing
  _save_pricing_users(users)
  return True, "Logged in successfully."


def _get_user_profile(email: str) -> dict[str, str]:
  users = _load_pricing_users()
  profile = users.get(email.strip().lower(), {})
  if not isinstance(profile, dict):
    return {}
  return {str(k): str(v) for k, v in profile.items()}


def _update_user_profile(email: str, updates: dict[str, str]) -> None:
  users = _load_pricing_users()
  key = email.strip().lower()
  existing = users.get(key, {})
  if not isinstance(existing, dict):
    existing = {}
  for update_key, update_value in updates.items():
    existing[str(update_key)] = str(update_value)
  users[key] = existing
  _save_pricing_users(users)


def _append_usage_snapshot(snapshot: dict[str, str]) -> None:
  _ensure_pricing_storage()
  with PRICING_USAGE_FILE.open("a", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
      handle,
      fieldnames=[
        "timestamp_utc",
        "email",
        "billing_cycle",
        "plan_name",
        "included_records",
        "usage_records",
        "overage_records",
        "base_subscription",
        "overage_cost",
        "estimated_total",
        "price_per_record",
      ],
    )
    writer.writerow(snapshot)


def _load_usage_snapshots(email: str, limit: int = 8) -> list[dict[str, str]]:
  _ensure_pricing_storage()
  rows: list[dict[str, str]] = []
  with PRICING_USAGE_FILE.open("r", newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
      if str(row.get("email", "")).strip().lower() == email.strip().lower():
        rows.append({k: str(v) for k, v in row.items()})
  return list(reversed(rows[-limit:]))


def _safe_set_page_config(**kwargs) -> None:
    try:
        st.set_page_config(**kwargs)
    except Exception:
        pass


_safe_set_page_config(
    page_title="Pricing | ReMatch",
    page_icon=FAVICON_PATH,
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    dedent(
        """
        <style>
          html,
          body {
            margin: 0;
          }

          .stApp {
            background:
              radial-gradient(55rem 30rem at 108% 92%, rgba(94, 157, 243, 0.14), transparent 62%),
              radial-gradient(40rem 24rem at -8% -8%, rgba(255, 255, 255, 0.72), transparent 60%),
              #f3f4f6;
          }

          /* Remove Streamlit's default top chrome / padding to eliminate the grey band. */
          div[data-testid="stHeader"],
          header[data-testid="stHeader"],
          div[data-testid="stToolbar"],
          div[data-testid="stDecoration"],
          #MainMenu,
          footer {
            display: none !important;
          }

          div[data-testid="stAppViewContainer"],
          section.main,
          div[data-testid="stAppViewContainer"] > .main,
          section[data-testid="stMain"],
          div[data-testid="stMain"] {
            margin-top: 0 !important;
            padding-top: 0 !important;
          }

          div[data-testid="stMainBlockContainer"],
          .block-container {
            max-width: 100% !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
          }

          div[data-testid="stElementContainer"] iframe {
            background: transparent !important;
          }
        </style>
        """
    ),
    unsafe_allow_html=True,
)

st.markdown(
    dedent(
        """
        <style>
          div[data-testid="stButton"] button[kind="primary"][data-testid="stBaseButton-primary"] {
            min-height: 2.9rem;
            padding: 0.3rem 1.15rem;
            border-radius: 0.65rem;
            border: 1px solid rgba(0, 0, 0, 0.04);
            background: linear-gradient(180deg, #0f62ff, #084dce);
            color: #ffffff;
            font-family: "Plus Jakarta Sans", sans-serif;
            font-size: 0.96rem;
            font-weight: 700;
            box-shadow: 0 8px 16px rgba(15, 98, 255, 0.22);
          }
        </style>
        """
    ),
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
      .pricing-native-title {
        text-align: center;
        margin: 0;
        font-family: "Plus Jakarta Sans", sans-serif;
        font-size: clamp(2.1rem, 4vw, 3rem);
        font-weight: 800;
        color: #12131a;
      }
      .wm-title-em { color: #0f62ff; }

      .pricing-native-subtitle {
        text-align: center;
        margin: 0.2rem 0 1rem;
        color: #383d46;
      }
      .pricing-native-card {
        border: 1px solid rgba(18, 19, 26, 0.1);
        border-radius: 0.95rem;
        background: #ffffff;
        min-height: 22rem;
        padding: 1.1rem 1.1rem 0.8rem;
        box-shadow: 0 6px 16px rgba(18, 19, 26, 0.06);
      }
      .pricing-native-card.popular {
        border: 2px solid rgba(15, 98, 255, 0.75);
      }
      .pricing-native-card h3 {
        margin: 0.2rem 0 0.25rem;
        font-family: "Plus Jakarta Sans", sans-serif;
        color: #1a1c23;
      }
      .pricing-native-card p {
        margin: 0 0 0.6rem;
        color: #6f7683;
        font-size: 0.9rem;
      }
      .pricing-native-card ul {
        margin: 0.8rem 0 0;
        padding-left: 1rem;
        color: #2d3139;
      }
      .pricing-native-card li {
        margin-bottom: 0.4rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<h1 class="pricing-native-title">Re<span class="wm-title-em">Match</span> Pricing</h1>', unsafe_allow_html=True)
st.markdown('<p class="pricing-native-subtitle">Easy to start, scalable later</p>', unsafe_allow_html=True)

payg_col, sub_col, ent_col = st.columns(3, gap="large")

with payg_col:
    st.markdown(
        """
        <div class="pricing-native-card">
          <h3>Pay As You Go</h3>
          <p>Test with your own data</p>
          <ul>
            <li>£0.5/search</li>
            <li>No integration required</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="margin-top:-0.55rem;"></div>', unsafe_allow_html=True)
    if st.button(
        "Get Started",
      type="primary",
        use_container_width=True,
        key="pricing_payg_card_get_started",
    ):
        st.query_params["page"] = "rematchpricing"
        st.query_params["pricing_flow"] = "payg"
        st.rerun()

with sub_col:
    st.markdown(
        """
        <div class="pricing-native-card popular">
          <h3>Subscription</h3>
          <p>For teams ready to scale</p>
          <ul>
            <li>Annual-usage based pricing</li>
            <li>Lower effective rate per search</li>
            <li>Agreed credit</li>
            <li>20% upfront discount</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="margin-top:-0.55rem;"></div>', unsafe_allow_html=True)
    st.button("Get Started", type="primary", use_container_width=True, key="pricing_subscription_get_started")

with ent_col:
    st.markdown(
        """
        <div class="pricing-native-card">
          <h3>Enterprise</h3>
          <p>Full platform integration</p>
          <ul>
            <li>API access</li>
            <li>Role-based access control</li>
            <li>Audit logs</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="margin-top:-0.55rem;"></div>', unsafe_allow_html=True)
    st.button("Get Started", type="primary", use_container_width=True, key="pricing_enterprise_get_started")

left_spacer, button_col, right_spacer = st.columns([4, 2, 4])
with button_col:
    if st.button("Back to Landing", type="primary", use_container_width=True, key="pricing_back_to_landing"):
        st.query_params["page"] = "landing"
        if "pricing_flow" in st.query_params:
            del st.query_params["pricing_flow"]
        st.rerun()

@st.dialog("Log In", width="small")
def _render_pricing_login_dialog() -> None:
  st.caption("Please log in to continue with subscription setup and usage pricing.")

  login_email = st.text_input("Work email", key="pricing_login_email_dialog")
  login_password = st.text_input("Password", type="password", key="pricing_login_password_dialog")
  login_col, cancel_col = st.columns(2, gap="small")

  with login_col:
    login_clicked = st.button(
      "Log In",
      type="primary",
      use_container_width=True,
      key="pricing_login_button_dialog",
    )
  with cancel_col:
    cancel_clicked = st.button(
      "Cancel",
      use_container_width=True,
      key="pricing_cancel_button_dialog",
    )

  if login_clicked:
    if login_email.strip() and login_password.strip():
      ok, message = _auth_or_register_user(login_email.strip().lower(), login_password)
      if ok:
        st.session_state["pricing_logged_in"] = True
        st.session_state["pricing_user_email"] = login_email.strip().lower()
        st.session_state["pricing_show_login_dialog"] = False
        st.success(message)
        st.rerun()
      else:
        st.error(message)
    else:
      st.warning("Enter both email and password to log in.")

  if cancel_clicked:
    st.session_state["pricing_show_login_dialog"] = False
    st.query_params["page"] = "rematchpricing"
    if "pricing_flow" in st.query_params:
      del st.query_params["pricing_flow"]
    st.rerun()

pricing_flow = str(st.query_params.get("pricing_flow", "")).strip().lower()

if pricing_flow == "payg":
    st.markdown("### Pay As You Go Onboarding")

    if "pricing_logged_in" not in st.session_state:
        st.session_state["pricing_logged_in"] = False

    if "pricing_show_login_dialog" not in st.session_state:
        st.session_state["pricing_show_login_dialog"] = False

    if not st.session_state["pricing_logged_in"]:
        if not st.session_state["pricing_show_login_dialog"]:
            st.session_state["pricing_show_login_dialog"] = True

        if st.session_state["pricing_show_login_dialog"]:
            _render_pricing_login_dialog()

        st.info("Log in to continue with subscription setup and usage pricing.")
    else:
        with st.container(border=True):
            user_email = str(st.session_state.get("pricing_user_email", "User"))
            st.success(f"Logged in as {user_email}")

            plan_catalog = {
                "Starter": {"included_records": 5000, "base_fee": 199.0, "overage_price_per_record": 0.04},
                "Growth": {"included_records": 25000, "base_fee": 799.0, "overage_price_per_record": 0.03},
                "Scale": {"included_records": 100000, "base_fee": 2499.0, "overage_price_per_record": 0.02},
            }

            profile = _get_user_profile(user_email)
            if "pricing_onboarding_step" not in st.session_state:
                if profile.get("payment_setup_complete", "").lower() == "true" and profile.get("plan_name", ""):
                    st.session_state["pricing_onboarding_step"] = "complete"
                else:
                    st.session_state["pricing_onboarding_step"] = "plan"

            onboarding_step = str(st.session_state.get("pricing_onboarding_step", "plan")).strip().lower()

            if onboarding_step == "plan":
                st.markdown("#### Step 1 of 3 — Select a plan")
                with st.form("pricing_plan_selection_form", clear_on_submit=False):
                    billing_cycle = st.selectbox(
                        "Billing cycle",
                        ["Monthly", "Annual (20% upfront discount)"],
                        index=0 if not profile.get("billing_cycle") else (0 if profile.get("billing_cycle") == "Monthly" else 1),
                        key="pricing_billing_cycle",
                    )
                    plan_name = st.selectbox(
                        "Plan",
                        ["Starter", "Growth", "Scale"],
                        index=max(0, ["Starter", "Growth", "Scale"].index(profile.get("plan_name", "Starter")))
                        if profile.get("plan_name", "Starter") in ["Starter", "Growth", "Scale"]
                        else 0,
                        key="pricing_plan_name",
                    )
                    continue_clicked = st.form_submit_button("Continue to Payment", type="primary")

                if continue_clicked:
                    _update_user_profile(
                        user_email,
                        {
                            "billing_cycle": billing_cycle,
                            "plan_name": plan_name,
                            "plan_selected_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    st.session_state["pricing_onboarding_step"] = "payment"
                    st.rerun()

            elif onboarding_step == "payment":
                plan_name = profile.get("plan_name", "") or "Starter"
                billing_cycle = profile.get("billing_cycle", "") or "Monthly"
                st.markdown("#### Step 2 of 3 — Set up payment details")
                st.caption("For safety, this demo does not collect full card numbers. Store payment tokens via your payment provider instead.")

                with st.form("pricing_payment_details_form", clear_on_submit=False):
                    company_name = st.text_input("Company name", value=profile.get("company_name", ""))
                    billing_email = st.text_input("Billing email", value=profile.get("billing_email", user_email))
                    billing_address = st.text_area("Billing address", value=profile.get("billing_address", ""), height=110)
                    vat_id = st.text_input("VAT / Tax ID (optional)", value=profile.get("vat_id", ""))
                    payment_method = st.selectbox(
                        "Payment method",
                        ["Card (tokenized)", "Invoice", "Bank transfer"],
                        index=0,
                    )
                    card_last4 = ""
                    if payment_method.startswith("Card"):
                        card_last4 = st.text_input("Card last 4 digits", value=profile.get("card_last4", ""), max_chars=4)
                    back_clicked = st.form_submit_button("Back", type="secondary")
                    confirm_clicked = st.form_submit_button("Confirm and Finish", type="primary")

                if back_clicked:
                    st.session_state["pricing_onboarding_step"] = "plan"
                    st.rerun()

                if confirm_clicked:
                    errors: list[str] = []
                    if not company_name.strip():
                        errors.append("Enter a company name.")
                    if "@" not in billing_email or "." not in billing_email:
                        errors.append("Enter a valid billing email.")
                    if payment_method.startswith("Card"):
                        digits = "".join([c for c in card_last4.strip() if c.isdigit()])
                        if len(digits) != 4:
                            errors.append("Card last 4 digits must be 4 numbers.")
                        card_last4 = digits

                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        _update_user_profile(
                            user_email,
                            {
                                "company_name": company_name.strip(),
                                "billing_email": billing_email.strip().lower(),
                                "billing_address": billing_address.strip(),
                                "vat_id": vat_id.strip(),
                                "payment_method": payment_method,
                                "card_last4": card_last4,
                                "payment_setup_complete": "true",
                                "payment_setup_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        st.session_state["pricing_onboarding_step"] = "complete"
                        st.success("Payment details saved. Onboarding complete.")
                        st.rerun()

            else:
                profile = _get_user_profile(user_email)
                plan_name = profile.get("plan_name", "") or "Starter"
                billing_cycle = profile.get("billing_cycle", "") or "Monthly"

                st.markdown("#### Step 3 of 3 — Usage & billing preview")
                st.caption(f"Plan: {plan_name} · Billing cycle: {billing_cycle}")

                selected = plan_catalog.get(plan_name, plan_catalog["Starter"])
                included_records = int(selected["included_records"])
                monthly_base_fee = float(selected["base_fee"])
                overage_price_per_record = float(selected["overage_price_per_record"])

                annual_discount_factor = 0.8 if billing_cycle.startswith("Annual") else 1.0
                base_fee_after_discount = monthly_base_fee * annual_discount_factor

                preview_col, usage_col = st.columns(2, gap="large")
                with preview_col:
                    st.markdown("#### Plan details")
                    st.metric("Included records", f"{included_records:,}")
                    st.metric("Monthly base fee", f"GBP {monthly_base_fee:,.2f}")
                    st.metric("Overage price / record", f"GBP {overage_price_per_record:.4f}")
                    change_col, _ = st.columns([1, 1])
                    with change_col:
                        if st.button("Change Plan", use_container_width=True, key="pricing_change_plan"):
                            st.session_state["pricing_onboarding_step"] = "plan"
                            st.rerun()

                with usage_col:
                    st.markdown("#### Usage Display")
                    usage_records = st.number_input(
                        "Records processed this billing period",
                        min_value=0,
                        value=included_records,
                        step=100,
                        key="pricing_usage_records",
                    )

                overage_records = max(0, int(usage_records) - included_records)
                overage_cost = overage_records * overage_price_per_record
                total_cost = base_fee_after_discount + overage_cost
                price_per_record = total_cost / max(1, int(usage_records))

                st.markdown("#### Billing Summary")
                m1, m2, m3, m4 = st.columns(4, gap="small")
                with m1:
                    st.metric("Used records", f"{int(usage_records):,}")
                with m2:
                    st.metric("Overage records", f"{overage_records:,}")
                with m3:
                    st.metric("Estimated total", f"GBP {total_cost:,.2f}")
                with m4:
                    st.metric("Price per record", f"GBP {price_per_record:.4f}")

                usage_ratio = min(1.0, int(usage_records) / max(1, included_records))
                st.progress(usage_ratio, text=f"Plan usage: {usage_ratio * 100:.1f}% of included records")

                save_snapshot = st.button(
                    "Save Usage Snapshot",
                    type="primary",
                    use_container_width=True,
                    key="pricing_save_usage_snapshot",
                )
                if save_snapshot:
                    _append_usage_snapshot(
                        {
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "email": user_email,
                            "billing_cycle": billing_cycle,
                            "plan_name": plan_name,
                            "included_records": str(included_records),
                            "usage_records": str(int(usage_records)),
                            "overage_records": str(overage_records),
                            "base_subscription": f"{base_fee_after_discount:.2f}",
                            "overage_cost": f"{overage_cost:.2f}",
                            "estimated_total": f"{total_cost:.2f}",
                            "price_per_record": f"{price_per_record:.6f}",
                        }
                    )
                    st.success("Usage snapshot saved to file.")

                history_rows = _load_usage_snapshots(user_email, limit=8)
                if history_rows:
                    st.markdown("#### Recent Usage History")
                    st.dataframe(history_rows, use_container_width=True, height=240)

            logout_col, close_col = st.columns(2, gap="small")
            with logout_col:
              if st.button("Log Out", use_container_width=True, key="pricing_logout_button"):
                st.session_state["pricing_logged_in"] = False
                st.session_state["pricing_show_login_dialog"] = False
                st.session_state.pop("pricing_onboarding_step", None)
                st.session_state.pop("pricing_user_email", None)
                st.rerun()
            with close_col:
              if st.button("Close Setup", use_container_width=True, key="pricing_close_setup_button"):
                st.query_params["page"] = "rematchpricing"
                if "pricing_flow" in st.query_params:
                  del st.query_params["pricing_flow"]
                st.rerun()

