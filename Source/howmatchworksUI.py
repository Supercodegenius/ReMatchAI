import os
from textwrap import dedent

import streamlit as st
from streamlit.components.v1 import html


FAVICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "favicon.png.jpeg")


def _safe_set_page_config(**kwargs) -> None:
    try:
        st.set_page_config(**kwargs)
    except Exception:
        pass


_safe_set_page_config(
    page_title="How Match Works | ReMatch",
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

html(
    dedent(
        """
        <html>
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <style>
              @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

              :root {
                --hm-bg: #f3f4f6;
                --hm-ink: #12131a;
                --hm-muted: #3e434b;
                --hm-blue: #0f62ff;
              }

              * {
                box-sizing: border-box;
              }

              body {
                margin: 0;
                background:
                  radial-gradient(55rem 30rem at 108% 92%, rgba(94, 157, 243, 0.14), transparent 62%),
                  radial-gradient(40rem 24rem at -8% -8%, rgba(255, 255, 255, 0.72), transparent 60%),
                  var(--hm-bg);
                color: var(--hm-ink);
                font-family: "Manrope", sans-serif;
              }

              .hm-shell {
                width: min(78rem, 100%);
                margin: 0 auto;
                padding: 1.1rem 1rem 1.25rem;
                position: relative;
                overflow: hidden;
              }

              .hm-shell::before {
                content: "";
                position: absolute;
                left: -1.1rem;
                top: 0.3rem;
                width: 31.5rem;
                height: 31.5rem;
                border-radius: 50%;
                background: repeating-radial-gradient(
                  circle at center,
                  rgba(123, 178, 247, 0.17) 0,
                  rgba(123, 178, 247, 0.17) 1px,
                  transparent 2px,
                  transparent 14px
                );
                opacity: 0.33;
                pointer-events: none;
                z-index: 0;
                transform: rotate(12deg);
              }

              .hm-head {
                position: relative;
                z-index: 1;
                text-align: center;
                margin-top: 0.2rem;
              }

              .hm-title {
                margin: 0;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: clamp(2.35rem, 4.2vw, 3.9rem);
                line-height: 1.04;
                letter-spacing: -0.02em;
                font-weight: 800;
                color: var(--hm-ink);
              }

              .hm-title-em {
                color: var(--hm-blue);
              }

              .hm-subtitle {
                margin: 0.62rem auto 0;
                max-width: 56rem;
                color: #32363d;
                font-size: clamp(1.03rem, 1.38vw, 1.55rem);
                line-height: 1.15;
                font-weight: 500;
              }

              .hm-grid {
                position: relative;
                z-index: 1;
                margin-top: 2.4rem;
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 1.55rem;
                align-items: stretch;
              }

              .hm-back-row {
                position: relative;
                z-index: 1;
                margin-top: 1.1rem;
                display: flex;
                justify-content: center;
              }

              .hm-back-btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 12rem;
                padding: 0.88rem 1.35rem;
                border-radius: 0.7rem;
                background: linear-gradient(180deg, #0f62ff, #084dce);
                color: #ffffff !important;
                text-decoration: none !important;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: 0.98rem;
                font-weight: 700;
                box-shadow: 0 8px 16px rgba(15, 98, 255, 0.22);
              }

              .hm-back-btn:hover {
                color: #ffffff !important;
                filter: brightness(1.02);
              }

              .hm-col {
                text-align: left;
                max-width: 35rem;
                margin: 0 auto;
                width: 100%;
                height: 100%;
                padding: 1.5rem 1.35rem 1.2rem;
                border-radius: 0.95rem;
                background: #ffffff;
                border: 1px solid rgba(18, 19, 26, 0.08);
                box-shadow: 0 4px 12px rgba(18, 19, 26, 0.035);
              }

              .hm-icon {
                width: 2.3rem;
                height: 2.3rem;
                border-radius: 0.64rem;
                background: linear-gradient(180deg, #e9f2ff, #dfeafd);
                color: #2f70d8;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 0.88rem;
              }

              .hm-icon-mark {
                width: 0.88rem;
                height: 0.88rem;
                border: 1.8px solid #2f70d8;
                border-radius: 0.2rem;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 0.57rem;
                line-height: 1;
                font-weight: 800;
              }

              .hm-icon-star {
                font-size: 1rem;
                line-height: 1;
              }

              .hm-icon-sliders,
              .hm-icon-bars {
                font-size: 1rem;
                line-height: 1;
              }

              .hm-card-title {
                margin: 0;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: 1.15rem;
                line-height: 1.05;
                color: #1a1c23;
                font-weight: 800;
                letter-spacing: -0.01em;
              }

              .hm-card-text {
                margin: 0.56rem 0 0;
                color: #7a7f89;
                font-size: 0.92rem;
                line-height: 1.25;
                font-weight: 500;
                max-width: 25.6rem;
              }

              .hm-highlight {
                color: var(--hm-blue);
                font-weight: 800;
              }

              @media (max-width: 1080px) {
                .hm-grid {
                  grid-template-columns: repeat(2, minmax(0, 1fr));
                  gap: 1.25rem;
                }
              }

              @media (max-width: 680px) {
                .hm-shell {
                  padding: 0.7rem 0.8rem 0.9rem;
                }

                .hm-shell::before {
                  width: 22rem;
                  height: 22rem;
                  left: -4.2rem;
                  top: 2rem;
                  opacity: 0.2;
                }

                .hm-head {
                  margin-top: 0;
                }

                .hm-title {
                  font-size: clamp(2rem, 8vw, 2.7rem);
                }

                .hm-subtitle {
                  margin-top: 0.45rem;
                  max-width: 100%;
                  font-size: 0.98rem;
                  line-height: 1.2;
                }

                .hm-grid {
                  margin-top: 1.1rem;
                  grid-template-columns: 1fr;
                  gap: 0.95rem;
                }

                .hm-col {
                  padding: 1rem 1rem 0.9rem;
                  border-radius: 0.85rem;
                }

                .hm-icon {
                  width: 2rem;
                  height: 2rem;
                  margin-bottom: 0.72rem;
                }

                .hm-card-title {
                  font-size: 1.02rem;
                }

                .hm-card-text {
                  margin-top: 0.45rem;
                  font-size: 0.84rem;
                  line-height: 1.22;
                }
              }
            </style>
          </head>
          <body>
            <section class="hm-shell">
              <header class="hm-head">
                <h1 class="hm-title">The Re<span class="hm-title-em">Match</span> solution</h1>
                <p class="hm-subtitle">
                  This is a purpose-built platform designed to automate and optimize reinsurance entity
                  matching
                </p>
              </header>

              <div class="hm-grid">
                <article class="hm-col">
                  <div class="hm-icon"><span class="hm-icon-mark">&#10003;</span></div>
                  <h2 class="hm-card-title">Multi-Method Matching Engine</h2>
                  <p class="hm-card-text">
                    <span class="hm-highlight">6 algorithms</span> for unparalleled accuracy. Exact, Fuzzy, Soundex, Jaro-Winkler, Levenshtein &amp; AIMatch
                  </p>
                </article>

                <article class="hm-col">
                  <div class="hm-icon"><span class="hm-icon-star">&#10038;</span></div>
                  <h2 class="hm-card-title">AI-Powered Learning</h2>
                  <p class="hm-card-text">
                    Continuously improve based on your specific data patterns
                  </p>
                </article>

                <article class="hm-col">
                  <div class="hm-icon"><span class="hm-icon-sliders">&#9783;</span></div>
                  <h2 class="hm-card-title">Adjustable Match Thresholds</h2>
                  <p class="hm-card-text">
                    Fine-tune confidence levels to suit your risk appetite
                  </p>
                </article>

                <article class="hm-col">
                  <div class="hm-icon"><span class="hm-icon-bars">&#9637;</span></div>
                  <h2 class="hm-card-title">Built In Detail For Scale</h2>
                  <p class="hm-card-text">
                    50,000 records matched in seconds. Other tools take 5-10 for the same task
                  </p>
                </article>
              </div>
            </section>
            <script>
              (function () {
                const postHeight = () => {
                  const body = document.body;
                  const doc = document.documentElement;
                  const contentHeight = Math.max(
                    body ? body.scrollHeight : 0,
                    doc ? doc.scrollHeight : 0,
                  );
                  window.parent.postMessage(
                    {
                      isStreamlitMessage: true,
                      type: "streamlit:setFrameHeight",
                      height: contentHeight + 8,
                    },
                    "*",
                  );
                };

                window.addEventListener("load", postHeight);
                window.addEventListener("resize", postHeight);
                if (document.body) {
                  const observer = new MutationObserver(postHeight);
                  observer.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    characterData: true,
                  });
                }
                setTimeout(postHeight, 0);
                setTimeout(postHeight, 250);
                setTimeout(postHeight, 800);
              })();
            </script>
          </body>
        </html>
        """
    ),
    height=520,
    scrolling=False,
)

st.markdown(
    dedent(
        """
        <style>
          div[data-testid="stButton"] {
            display: flex;
            justify-content: center;
            margin: 0.18rem 0 0.95rem;
          }

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

left_spacer, button_col, right_spacer = st.columns([4, 2, 4])
with button_col:
    if st.button("Back to Landing", type="primary", use_container_width=True, key="how_match_works_back"):
        st.query_params["page"] = "landing"
        st.rerun()

