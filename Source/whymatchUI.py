import os
from textwrap import dedent

import streamlit as st
from streamlit.components.v1 import html as st_html


FAVICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "favicon.png")


def _safe_set_page_config(**kwargs) -> None:
    try:
        st.set_page_config(**kwargs)
    except Exception:
        pass


_safe_set_page_config(
    page_title="Why Match | ReMatch",
    page_icon=FAVICON_PATH,
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    dedent(
        """
        <style>
          html,
          body,
          .stApp {
            margin: 0;
            min-height: 100%;
          }

          html,
          body {
            height: 100%;
            overflow: hidden !important;
          }

          .stApp,
          div[data-testid="stAppViewContainer"],
          section.main,
          div[data-testid="stAppViewContainer"] > .main {
            height: 100%;
            overflow: hidden !important;
          }

          section[data-testid="stMain"],
          div[data-testid="stMain"] {
            height: auto !important;
            overflow: hidden !important;
          }

          .stApp {
            background:
              radial-gradient(55rem 30rem at 108% 92%, rgba(94, 157, 243, 0.14), transparent 62%),
              radial-gradient(40rem 24rem at -8% -8%, rgba(255, 255, 255, 0.72), transparent 60%),
              #f3f4f6;
          }

          div[data-testid="stAppViewContainer"],
          section.main,
          section[data-testid="stMain"],
          div[data-testid="stMain"] {
            margin-top: 0 !important;
            padding-top: 0 !important;
          }

          div[data-testid="stAppViewContainer"] > .main,
          div[data-testid="stMainBlockContainer"],
          .block-container {
            max-width: 100% !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
          }

          div[data-testid="stHeader"],
          header[data-testid="stHeader"],
          div[data-testid="stToolbar"],
          div[data-testid="stDecoration"],
          #MainMenu,
          footer {
            display: none !important;
          }

          div[data-testid="stElementContainer"] {
            margin-top: 0 !important;
            padding-top: 0 !important;
          }

          div[data-testid="stElementContainer"] iframe {
            background: transparent !important;
          }
        </style>
        """
    ),
    unsafe_allow_html=True,
)

st_html(
    dedent(
        """
        <style>
          html,
          body {
            margin: 0;
            padding: 0;
            background: transparent;
            overflow: hidden;
          }

          .wm-shell {
            width: min(76.5rem, calc(100% - 2.4rem));
            margin: 0 auto;
            padding: 1.05rem 0 1.2rem;
            box-sizing: border-box;
            position: relative;
            text-align: center;
            overflow-x: clip;
            font-family: "Plus Jakarta Sans", sans-serif;
          }

          .wm-shell::before {
            content: "";
            position: absolute;
            left: 50%;
            top: 4.2rem;
            transform: translateX(-50%);
            width: 41rem;
            height: 41rem;
            border-radius: 50%;
            background: repeating-radial-gradient(
              circle at center,
              rgba(123, 178, 247, 0.18) 0,
              rgba(123, 178, 247, 0.18) 1px,
              transparent 2px,
              transparent 14px
            );
            opacity: 0.22;
            pointer-events: none;
            z-index: 0;
          }

          .wm-content {
            position: relative;
            z-index: 1;
            padding: 1rem 0.2rem 0;
          }

          .wm-title {
            margin: 0;
            font-size: clamp(2.35rem, 4.2vw, 3.9rem);
            line-height: 1.04;
            letter-spacing: -0.02em;
            font-weight: 800;
            color: #12131a;
          }

          .wm-title-em {
            color: #0f62ff;
          }

          .wm-subtitle {
            margin: 0.7rem auto 0;
            max-width: 54rem;
            font-size: clamp(1.03rem, 1.35vw, 1.4rem);
            line-height: 1.18;
            color: #343741;
            font-weight: 500;
          }

          .wm-grid {
            margin-top: 2.15rem;
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: clamp(0.95rem, 1.45vw, 1.42rem);
            text-align: left;
          }

          @media (max-width: 1200px) {
            .wm-shell {
              width: min(74rem, calc(100% - 1.6rem));
            }
          }

          .wm-card {
            border: 1px solid rgba(18, 19, 26, 0.08);
            border-radius: 0.88rem;
            background: #ffffff;
            min-height: 15.2rem;
            padding: 1.32rem 1.48rem;
          }

          .wm-icon {
            width: 2.6rem;
            height: 2.6rem;
            border-radius: 0.68rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(180deg, #e9f2ff, #dae8fc);
            color: #2f70d8;
            margin-bottom: 1rem;
          }

          .wm-icon-check {
            width: 1rem;
            height: 1rem;
            border: 2px solid #2f70d8;
            border-radius: 0.2rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7rem;
            font-weight: 800;
            line-height: 1;
          }

          .wm-icon-sun {
            font-size: 1.18rem;
            line-height: 1;
          }

          .wm-card h2 {
            margin: 0 0 0.62rem;
            font-size: 2.87rem;
            line-height: 0.98;
            color: #1b1d24;
            font-weight: 700;
          }

          .wm-list {
            list-style: none;
            padding: 0;
            margin: 0;
          }

          .wm-list li {
            color: #343741;
            line-height: 1.00;
            font-size: 1.22rem;
            margin-bottom: 0.31rem;
            font-weight: 500;
          }

          .wm-actions {
            margin-top: 1.35rem;
            display: flex;
            justify-content: center;
          }

          @media (min-width: 981px) {
            .wm-actions {
              margin-top: 1.7rem;
            }
          }

          .wm-back-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 12rem;
            padding: 0.88rem 1.35rem;
            border-radius: 0.7rem;
            background: linear-gradient(180deg, #0f62ff, #084dce);
            color: #ffffff !important;
            text-decoration: none !important;
            font-size: 0.98rem;
            font-weight: 700;
            box-shadow: 0 8px 16px rgba(15, 98, 255, 0.22);
          }

          .wm-back-btn:hover {
            color: #ffffff !important;
            filter: brightness(1.02);
          }

          @media (max-width: 980px) {
            .wm-shell {
              width: calc(100% - 1rem);
              padding: 0.85rem 0 1rem;
            }

            .wm-shell::before {
              width: 30rem;
              height: 30rem;
              top: 5rem;
            }

            .wm-subtitle {
              max-width: 100%;
              line-height: 1.22;
              font-size: 1.2rem;
            }

            .wm-grid {
              margin-top: 1.45rem;
              grid-template-columns: 1fr;
              gap: 0.9rem;
            }

            .wm-card {
              min-height: 0;
              padding: 1.05rem 1.1rem;
            }

            .wm-card h2 {
              font-size: 2.25rem;
            }

            .wm-list li {
              font-size: 1.02rem;
              line-height: 1.08;
            }
          }
        </style>

        <section class="wm-shell">
          <div class="wm-content">
            <h1 class="wm-title">Why Re<span class="wm-title-em">Match</span> is different</h1>
            <p class="wm-subtitle">
              Generic Insured Name Matching tools fail on reinsurance data. We built a specialised engine that
              understands the context of your industry
            </p>

            <div class="wm-grid">
              <article class="wm-card">
                <div class="wm-icon"><span class="wm-icon-check">&#10003;</span></div>
                <h2>Now</h2>
                <ul class="wm-list">
                  <li>Multi-Method Matching (6 Methods)</li>
                  <li>Self-Learning AI</li>
                  <li>Built Specifically For Reinsurance</li>
                </ul>
              </article>
              <article class="wm-card">
                <div class="wm-icon"><span class="wm-icon-sun">&#10038;</span></div>
                <h2>Soon</h2>
                <ul class="wm-list">
                  <li>Batch Processing</li>
                  <li>Exposure Calculation</li>
                  <li>RCR &amp; RDS Reporting</li>
                </ul>
              </article>
            </div>

            <div class="wm-actions">
              <a class="wm-back-btn" href="?page=landing&nav=whymatch" target="_self">Back to Landing</a>
            </div>
          </div>
        </section>
        """
    ),
    height=590,
    scrolling=False,
)

