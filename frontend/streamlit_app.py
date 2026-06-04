"""Allerjeez Streamlit frontend.

Run with: uv run streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

API_BASE_URL = os.environ.get("ALLERJEEZ_API_URL", "http://127.0.0.1:8000")
HTTP_TIMEOUT = 60.0  # generous because /scan/analyze runs Gemini calls


COMMON_ALLERGENS = [
    "peanuts",
    "tree-nuts",
    "milk",
    "eggs",
    "wheat",
    "soy",
    "fish",
    "shellfish",
    "sesame",
    "mustard",
    "gluten",
    "celery",
    "lupin",
    "sulphites",
]

DIETARY_PREFERENCES = [
    "vegetarian",
    "vegan",
    "pescatarian",
    "halal",
    "kosher",
    "jain",
    "low-sugar",
    "low-sodium",
    "keto",
]

CONDITIONS = [
    "pregnancy",
    "breastfeeding",
    "diabetes-type-1",
    "diabetes-type-2",
    "hypertension",
    "kidney-disease",
    "celiac-disease",
    "ibs",
    "lactose-intolerant",
    "phenylketonuria",
]

VERDICT_BADGES = {
    "safe-for-you": ("Safe for you", "#7be07b"),
    "caution-for-you": ("Use with caution", "#ffd66b"),
    "avoid-for-you": ("Avoid", "#ff7575"),
    "unknown": ("Could not analyze", "#cfcfcf"),
}


THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;700;900&display=swap');

/* page background */
.stApp {
    background: #ff7a2b !important;
}

/* hide default chrome */
header[data-testid="stHeader"] {
    background: transparent !important;
}
#MainMenu, footer { visibility: hidden; }

/* fonts */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #1a1a1a;
}

h1, h2, h3 {
    font-family: 'Archivo Black', sans-serif;
    color: #1a1a1a !important;
    letter-spacing: -0.02em;
}

/* the big hero title */
.allerjeez-title {
    font-family: 'Archivo Black', sans-serif;
    font-size: 5.5rem;
    text-align: center;
    color: #1a1a1a;
    margin: 1.5rem 0 0.25rem 0;
    letter-spacing: -0.04em;
    line-height: 1;
}
.allerjeez-title .dot {
    color: #1a1a1a;
}
.allerjeez-tagline {
    font-family: 'Inter', serif;
    font-style: italic;
    text-align: center;
    font-size: 1.15rem;
    color: #1a1a1a;
    margin-bottom: 2.25rem;
}

/* neo-brutalist tile */
.brut-tile {
    background: #ffffff;
    border: 3px solid #1a1a1a;
    border-radius: 14px;
    padding: 14px 16px;
    box-shadow: 6px 6px 0 #1a1a1a;
    text-align: center;
    min-height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.brut-tile .label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #444;
}
.brut-tile .value {
    font-family: 'Archivo Black', sans-serif;
    font-size: 1.45rem;
    color: #1a1a1a;
    line-height: 1.15;
    margin-top: 6px;
}
.brut-tile .sub {
    font-size: 0.78rem;
    color: #444;
    margin-top: 4px;
    line-height: 1.3;
}

/* pastel color variants for tiles */
.tile-green  { background: #c8f7a6; }  /* pastel green */
.tile-yellow { background: #fff2a8; }  /* pastel yellow */
.tile-pink   { background: #ffb6c8; }  /* pastel pink */
.tile-coral  { background: #ffc8a8; }  /* pastel coral */

/* the form panel — transparent so only inputs are white */
[data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin-bottom: 0 !important;
}
[data-testid="stForm"] > div {
    gap: 1.25rem !important;
}
[data-testid="stFormSubmitButton"] {
    margin-top: 0.5rem !important;
    margin-bottom: 0 !important;
}
[data-testid="stForm"] label,
[data-testid="stForm"] label *,
[data-testid="stForm"] label p,
[data-testid="stForm"] label div,
.stTextInput label,
.stTextInput label *,
.stTextInput label p,
.stTextInput label div {
    color: #1a1a1a !important;
    font-weight: 900 !important;
    font-size: 1.5rem !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.01em !important;
    line-height: 1.2 !important;
    margin-bottom: 0.5rem !important;
}

/* primary buttons */
.stButton > button,
.stForm button,
[data-testid="stFormSubmitButton"] button {
    background: #ffd0aa !important;
    color: #1a1a1a !important;
    border: 3px solid #1a1a1a !important;
    border-radius: 14px !important;
    box-shadow: 6px 6px 0 #1a1a1a !important;
    font-family: 'Archivo Black', sans-serif !important;
    font-size: 1.05rem !important;
    padding: 0.55rem 1.25rem !important;
    transition: transform 0.05s ease, box-shadow 0.05s ease !important;
}
.stButton > button:hover,
.stForm button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    transform: translate(2px, 2px) !important;
    box-shadow: 3px 3px 0 #1a1a1a !important;
    background: #ffe2c8 !important;
}
[data-testid="stFormSubmitButton"] {
    display: flex !important;
    justify-content: center !important;
}
.stButton > button[kind="primary"],
.stButton > button[kind="primaryFormSubmit"],
[data-testid="stFormSubmitButton"] button,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primaryFormSubmit"] {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border: 3px solid #1a1a1a !important;
    box-shadow: none !important;
    border-radius: 10px !important;
    font-family: 'Archivo Black', sans-serif !important;
    height: 52px !important;
    padding: 0 2rem !important;
    width: auto !important;
    min-width: 200px !important;
    letter-spacing: 0.05em !important;
    line-height: 1 !important;
    margin: 0 auto !important;
    display: block !important;
}
.stButton > button[kind="primary"] *,
[data-testid="stFormSubmitButton"] button *,
[data-testid="stBaseButton-primary"] *,
[data-testid="stBaseButton-primaryFormSubmit"] * {
    color: #ffffff !important;
    font-family: 'Archivo Black', sans-serif !important;
    font-size: 1.45rem !important;
    font-weight: 900 !important;
    letter-spacing: 0.05em !important;
    line-height: 1 !important;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background: #000000 !important;
    color: #ffffff !important;
    box-shadow: none !important;
    transform: none !important;
}

/* text inputs + multiselects — kill BaseWeb wrappers, single chunky box */
.stTextInput [data-baseweb="base-input"],
.stTextInput div[data-baseweb="input"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
.stTextInput input,
.stSelectbox div[data-baseweb="select"],
.stMultiSelect div[data-baseweb="select"],
.stFileUploader section {
    border: 3px solid #1a1a1a !important;
    border-radius: 12px !important;
    background: #ffffff !important;
    box-shadow: 4px 4px 0 #1a1a1a !important;
    color: #1a1a1a !important;
}
.stTextInput input {
    height: 64px !important;
    line-height: 64px !important;
    font-size: 1.25rem !important;
    padding: 0 1.25rem !important;
    box-sizing: border-box !important;
}
.stTextInput div[data-baseweb="input"] {
    height: 64px !important;
}
.stTextInput input::placeholder {
    color: #888 !important;
}

.stFileUploader section button {
    box-shadow: none !important;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: #ffe2c8 !important;
    border-right: 3px solid #1a1a1a !important;
}

/* verdict badge */
.verdict-badge {
    display: inline-block;
    padding: 10px 18px;
    border: 3px solid #1a1a1a;
    border-radius: 12px;
    box-shadow: 5px 5px 0 #1a1a1a;
    font-family: 'Archivo Black', sans-serif;
    font-size: 1.15rem;
    margin: 6px 0 12px 0;
}

/* report cards */
.report-card {
    background: #ffffff;
    border: 3px solid #1a1a1a;
    border-radius: 12px;
    padding: 12px 14px;
    margin: 8px 0;
    box-shadow: 5px 5px 0 #1a1a1a;
}
.report-card.red    { background: #ffd0d0; }
.report-card.orange { background: #ffe1a8; }
.report-card.blue   { background: #c9e8ff; }
.report-card.gray   { background: #ececec; }

.report-card .ing-name {
    font-family: 'Archivo Black', sans-serif;
    font-size: 1.05rem;
}
.report-card .ing-raw {
    font-style: italic;
    color: #555;
    font-size: 0.85rem;
}
.report-card .ing-reason {
    margin-top: 4px;
}
.report-card .ing-explain {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 2px dashed #1a1a1a;
    font-size: 0.95rem;
    line-height: 1.45;
    color: #1a1a1a;
}

/* expanders */
.streamlit-expanderHeader {
    border: 3px solid #1a1a1a !important;
    border-radius: 12px !important;
    background: #fff !important;
    box-shadow: 4px 4px 0 #1a1a1a !important;
    font-family: 'Archivo Black', sans-serif !important;
}

/* ============== SCAN PAGE STYLES ============== */
.scan-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 0.5rem 0 1.5rem 0;
}
.scan-header-brand {
    font-family: 'Archivo Black', sans-serif;
    font-size: 1.6rem;
    color: #1a1a1a;
}
.scan-health-badge {
    background: #1a1a1a;
    color: #c8f7a6;
    border: 3px solid #1a1a1a;
    border-radius: 10px;
    padding: 8px 14px;
    font-family: 'Archivo Black', sans-serif;
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}
.scan-greeting-pill {
    display: inline-block;
    background: #1a1a1a;
    color: #ffffff;
    border: 3px solid #1a1a1a;
    border-radius: 999px;
    padding: 8px 16px;
    font-family: 'Archivo Black', sans-serif;
    font-size: 0.95rem;
    letter-spacing: 0.04em;
    margin-bottom: 0.75rem;
}
.scan-mega-title {
    font-family: 'Archivo Black', sans-serif;
    font-size: 4rem;
    line-height: 0.92;
    color: #1a1a1a;
    letter-spacing: -0.03em;
    margin: 0.25rem 0 1rem 0;
    text-transform: uppercase;
}
.scan-mega-sub {
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    color: #1a1a1a;
    font-weight: 600;
    max-width: 480px;
    margin-bottom: 1.5rem;
}

/* big action buttons (Upload / Camera) — target by Streamlit key */
button[kind="secondary"][data-testid*="upload_mode_btn"],
button[data-testid="stBaseButton-secondary"]:has(div p:is(:contains("UPLOAD IMAGE"))) {
    background: #ffe27a !important;
}
button[kind="secondary"][data-testid*="camera_mode_btn"] {
    background: #ffc8a8 !important;
}
/* common styling for both — use class added by our wrapper */
.scan-action-btn .stButton > button,
.scan-action-btn button {
    width: 100% !important;
    height: 72px !important;
    border: 3px solid #1a1a1a !important;
    border-radius: 14px !important;
    box-shadow: 6px 6px 0 #1a1a1a !important;
    font-family: 'Archivo Black', sans-serif !important;
    font-size: 1.05rem !important;
    letter-spacing: 0.04em !important;
    color: #1a1a1a !important;
    text-transform: uppercase;
}
.scan-action-btn .stButton > button p,
.scan-action-btn button p {
    color: #1a1a1a !important;
    font-family: 'Archivo Black', sans-serif !important;
    font-size: 1.05rem !important;
}
.scan-action-btn.yellow .stButton > button,
.scan-action-btn.yellow button { background: #ffe27a !important; }
.scan-action-btn.coral .stButton > button,
.scan-action-btn.coral button { background: #ffc8a8 !important; }

/* profile card */
.profile-card {
    background: #c8f7a6;
    border: 3px solid #1a1a1a;
    border-radius: 14px;
    box-shadow: 6px 6px 0 #1a1a1a;
    padding: 16px 18px;
    margin: 1rem 0;
}
.profile-card .profile-title {
    font-family: 'Archivo Black', sans-serif;
    font-size: 0.85rem;
    letter-spacing: 0.06em;
    color: #1a1a1a;
    border-bottom: 2px solid #1a1a1a;
    padding-bottom: 6px;
    margin-bottom: 10px;
}
.profile-card .profile-line {
    font-size: 0.95rem;
    color: #1a1a1a;
    margin: 6px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.profile-card .pill-cross,
.profile-card .pill-warn {
    display: inline-block;
    width: 22px;
    height: 22px;
    border-radius: 999px;
    border: 2px solid #1a1a1a;
    text-align: center;
    font-family: 'Archivo Black', sans-serif;
    font-size: 0.78rem;
    line-height: 18px;
    flex-shrink: 0;
}
.profile-card .pill-cross { background: #ff8888; color: #1a1a1a; }
.profile-card .pill-warn  { background: #ffd66b; color: #1a1a1a; }

/* dropzone framing around st.file_uploader */
.dropzone-wrap {
    background: #b6e8ff;
    border: 3px dashed #1a1a1a;
    border-radius: 14px;
    box-shadow: 6px 6px 0 #1a1a1a;
    padding: 8px;
    margin-top: 1rem;
}
.dropzone-wrap [data-testid="stFileUploader"] section {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1.5rem !important;
}
.dropzone-wrap [data-testid="stFileUploader"] section small {
    color: #1a1a1a !important;
}
.dropzone-wrap [data-testid="stFileUploader"] section button {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    font-family: 'Archivo Black', sans-serif !important;
}

/* how-it-works strip — pastel pop boxes, no white */
.how-strip {
    display: flex;
    gap: 14px;
    margin: 1.25rem 0 0.75rem 0;
    flex-wrap: wrap;
}
.how-step {
    flex: 1 1 0;
    min-width: 180px;
    border: 3px solid #1a1a1a;
    border-radius: 14px;
    box-shadow: 5px 5px 0 #1a1a1a;
    padding: 18px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 8px;
    min-height: 150px;
}
.how-step.s1 { background: #ffe27a; }  /* pastel yellow */
.how-step.s2 { background: #ffc8a8; }  /* pastel coral */
.how-step.s3 { background: #c8f7a6; }  /* pastel green */
.how-step .num {
    font-family: 'Archivo Black', sans-serif;
    font-size: 2rem;
    line-height: 1;
    color: #1a1a1a;
}
.how-step .text {
    font-size: 0.95rem;
    color: #1a1a1a;
    font-weight: 600;
    line-height: 1.35;
}

/* trust badge — single centered card */
.trust-badge {
    text-align: center;
    background: #b6e8ff;  /* pastel blue */
    border: 3px solid #1a1a1a;
    border-radius: 16px;
    box-shadow: 7px 7px 0 #1a1a1a;
    padding: 18px 22px;
    margin: 1.25rem auto 0 auto;
    max-width: 540px;
}
.trust-badge .label {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #444;
}
.trust-badge .value {
    font-family: 'Archivo Black', sans-serif;
    font-size: 1.6rem;
    color: #1a1a1a;
    margin-top: 6px;
}
.trust-badge .sub {
    font-size: 0.85rem;
    color: #1a1a1a;
    margin-top: 6px;
}

/* footer microcopy */
.footer-strip {
    text-align: center;
    margin: 2rem 0 0.5rem 0;
    color: #1a1a1a;
    font-size: 0.85rem;
    opacity: 0.85;
}
.footer-strip a {
    color: #1a1a1a;
    font-weight: 700;
}
</style>
"""


def inject_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def api_post(path: str, json: dict) -> httpx.Response:
    return httpx.post(f"{API_BASE_URL}{path}", json=json, timeout=HTTP_TIMEOUT)


def api_get(path: str, params: dict | None = None) -> httpx.Response:
    return httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=HTTP_TIMEOUT)


def api_put(path: str, json: dict, params: dict | None = None) -> httpx.Response:
    return httpx.put(
        f"{API_BASE_URL}{path}", json=json, params=params, timeout=HTTP_TIMEOUT
    )


def api_upload(
    path: str, file_bytes: bytes, filename: str, mime: str, params: dict
) -> httpx.Response:
    files = {"file": (filename, file_bytes, mime)}
    return httpx.post(
        f"{API_BASE_URL}{path}", files=files, params=params, timeout=HTTP_TIMEOUT
    )


def render_tile(label: str, value: Any, color_class: str, sub: str | None = None) -> str:
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return (
        f"<div class='brut-tile {color_class}'>"
        f"<div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>"
        f"{sub_html}"
        f"</div>"
    )


def render_hero() -> None:
    st.markdown(
        "<div class='allerjeez-title'>allerjeez<span class='dot'>.</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='allerjeez-tagline'>Scan food labels. Get personalized safety warnings.</div>",
        unsafe_allow_html=True,
    )


def render_trust_badge() -> None:
    st.markdown(
        """
        <div class='trust-badge'>
            <div class='label'>Data we trust</div>
            <div class='value'>FDA · EFSA · IARC · WHO</div>
            <div class='sub'>Allergens, additives & carcinogens — sourced from authoritative bodies, not guessed.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_how_it_works() -> None:
    st.markdown(
        """
        <div class='how-strip'>
            <div class='how-step s1'>
                <div class='num'>1</div>
                <div class='text'>Snap or upload a food product photo.</div>
            </div>
            <div class='how-step s2'>
                <div class='num'>2</div>
                <div class='text'>AI reads the label and pulls a clean ingredient list.</div>
            </div>
            <div class='how-step s3'>
                <div class='num'>3</div>
                <div class='text'>We flag YOUR allergens, carcinogens, and shady additives.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class='footer-strip'>
            Built with FastAPI · Postgres · Gemini · Streamlit ·
            <a href='https://github.com/dhaniyaaaku/allerjeez' target='_blank'>source on GitHub</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login() -> None:
    render_hero()

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        display_name = st.text_input(
            "Display name (optional)", placeholder="What should we call you?"
        )
        submitted = st.form_submit_button(
            "Login", type="primary", use_container_width=True
        )

    render_how_it_works()
    render_trust_badge()

    if submitted:
        if not email:
            st.error("Please enter an email.")
            return

        try:
            response = api_post(
                "/users",
                json={
                    "email": email,
                    "display_name": display_name or None,
                },
            )
        except httpx.RequestError as exc:
            st.error(f"Couldn't reach the backend. Is it running? Details: {exc}")
            return

        if response.status_code == 422:
            st.error("That doesn't look like a valid email.")
            return
        if response.status_code >= 400:
            st.error(f"Backend error: {response.text}")
            return

        user = response.json()
        st.session_state["email"] = user["email"]
        st.session_state["display_name"] = user.get("display_name")
        st.session_state["page"] = "scan"
        st.rerun()


def render_sidebar(email: str, display_name: str) -> None:
    with st.sidebar:
        st.markdown(
            f"<div style='font-family: Archivo Black; font-size: 1.6rem;'>"
            f"allerjeez<span style='color:#1a1a1a;'>.</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**Signed in as**  \n{display_name}")
        st.caption(email)

        st.markdown("---")
        st.markdown("**Navigate**")
        if st.button("Scan a product", use_container_width=True, type="primary"):
            st.session_state["page"] = "scan"
            st.rerun()
        if st.button("Profile", use_container_width=True):
            st.session_state["page"] = "profile"
            st.rerun()
        if st.button("Scan history", use_container_width=True):
            st.session_state["page"] = "history"
            st.rerun()

        st.markdown("---")
        if st.button("Log out", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def _resolve_display_name(user: dict, email: str) -> str:
    raw = (user.get("display_name") or "").strip()
    # ignore obvious junk values left from earlier testing
    if raw and raw.lower() not in {"string", "user", "test", "none", "null"}:
        return raw
    # fallback: the part of the email before @
    local = email.split("@", 1)[0]
    return local.replace(".", " ").replace("_", " ").title() if local else email


def fetch_user(email: str) -> dict | None:
    response = api_get("/users/me", params={"email": email})
    if response.status_code != 200:
        st.error(f"Couldn't load your profile: {response.text}")
        return None
    return response.json()


def render_profile() -> None:
    email = st.session_state["email"]
    user = fetch_user(email)
    if user is None:
        return

    st.title("Your health profile")
    st.caption(
        "Allerjeez personalizes every scan against this profile. "
        "Update anytime — your future scans use the latest version."
    )

    with st.form("profile_form"):
        new_display_name = st.text_input(
            "Display name",
            value=user.get("display_name") or "",
        )

        st.markdown("#### Allergies")
        st.caption("Common food allergens you react to.")
        allergies = st.multiselect(
            "Allergies",
            options=COMMON_ALLERGENS,
            default=user.get("allergies", []),
            label_visibility="collapsed",
        )

        st.markdown("#### Dietary preferences")
        st.caption("Choices about what you eat.")
        dietary_preferences = st.multiselect(
            "Dietary preferences",
            options=DIETARY_PREFERENCES,
            default=user.get("dietary_preferences", []),
            label_visibility="collapsed",
        )

        st.markdown("#### Conditions")
        st.caption("Health conditions that affect what's safe to eat.")
        conditions = st.multiselect(
            "Conditions",
            options=CONDITIONS,
            default=user.get("conditions", []),
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button("Save profile", type="primary")

    if submitted:
        payload = {
            "display_name": new_display_name or None,
            "allergies": allergies,
            "dietary_preferences": dietary_preferences,
            "conditions": conditions,
        }
        save_response = api_put(
            "/users/me/profile", json=payload, params={"email": email}
        )
        if save_response.status_code == 200:
            st.success("Profile saved.")
            st.session_state["display_name"] = new_display_name or None
        else:
            st.error(f"Couldn't save: {save_response.text}")


def render_verdict(verdict: str) -> None:
    label, color = VERDICT_BADGES.get(verdict, (verdict, "#cfcfcf"))
    st.markdown(
        f"<div class='verdict-badge' style='background:{color};'>{label}</div>",
        unsafe_allow_html=True,
    )


def _flag_card(flag: dict, color_class: str) -> str:
    explanation = (flag.get("explanation") or "").strip()
    explanation_html = (
        f"<div class='ing-explain'>{explanation}</div>" if explanation else ""
    )
    return (
        f"<div class='report-card {color_class}'>"
        f"<div class='ing-name'>{flag['ingredient_name']}</div>"
        f"<div class='ing-raw'>label said: {flag['raw_text_from_label']}</div>"
        f"<div class='ing-reason'>{flag['reason']}</div>"
        f"{explanation_html}"
        f"</div>"
    )


def render_report(report: dict[str, Any]) -> None:
    product = report.get("product_name") or "Unnamed product"
    st.subheader(product)
    render_verdict(report.get("overall_verdict", "unknown"))

    personal = report.get("personal_allergens", [])
    if personal:
        st.markdown("### Personal allergens")
        for flag in personal:
            st.markdown(_flag_card(flag, "red"), unsafe_allow_html=True)

    carcinogens = report.get("carcinogens", [])
    if carcinogens:
        st.markdown("### Carcinogen concerns")
        for flag in carcinogens:
            st.markdown(_flag_card(flag, "orange"), unsafe_allow_html=True)

    controversial = report.get("controversial_additives", [])
    if controversial:
        st.markdown("### Controversial additives")
        for flag in controversial:
            st.markdown(_flag_card(flag, "orange"), unsafe_allow_html=True)

    other_allergens = report.get("other_allergens", [])
    if other_allergens:
        st.markdown("### Other allergens (not yours, but flagged)")
        for flag in other_allergens:
            st.markdown(_flag_card(flag, "blue"), unsafe_allow_html=True)

    safe_known = report.get("safe_known_ingredients", [])
    if safe_known:
        st.markdown("### Safe / known ingredients")
        st.caption(", ".join(safe_known))

    unknown = report.get("unknown_ingredients", [])
    if unknown:
        st.markdown("### Could not identify")
        st.caption(", ".join(unknown))

    extraction = report.get("extraction", {})
    with st.expander("Show full extracted ingredient list"):
        for ing in extraction.get("ingredients", []):
            st.markdown(f"- {ing}")
        st.caption(
            f"Extraction confidence: {extraction.get('confidence', 0):.0%}"
            + (f" • {extraction['notes']}" if extraction.get("notes") else "")
        )


def _render_profile_card(user: dict) -> None:
    allergies = user.get("allergies", []) or []
    conditions = user.get("conditions", []) or []
    dietary = user.get("dietary_preferences", []) or []

    lines_html = ""
    for a in allergies[:5]:
        lines_html += (
            f"<div class='profile-line'>"
            f"<span class='pill-cross'>X</span>{a.replace('-', ' ').title()} allergy"
            f"</div>"
        )
    for c in conditions[:3]:
        lines_html += (
            f"<div class='profile-line'>"
            f"<span class='pill-warn'>!</span>{c.replace('-', ' ').title()}"
            f"</div>"
        )
    for d in dietary[:2]:
        lines_html += (
            f"<div class='profile-line'>"
            f"<span class='pill-warn'>!</span>{d.replace('-', ' ').title()}"
            f"</div>"
        )

    if not lines_html:
        lines_html = (
            "<div class='profile-line' style='font-style:italic; color:#444;'>"
            "No allergies or conditions set yet. Visit Profile to add them."
            "</div>"
        )

    st.markdown(
        f"""
        <div class='profile-card'>
            <div class='profile-title'>YOUR SAFETY PROFILE</div>
            {lines_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scan() -> None:
    email = st.session_state["email"]
    user = fetch_user(email)
    if user is None:
        return

    display_name = (user.get("display_name") or email.split("@")[0]).upper()

    # top row: brand + health badge
    st.markdown(
        f"""
        <div class='scan-header-row'>
            <div class='scan-header-brand'>allerjeez<span style='color:#1a1a1a;'>.</span></div>
            <div class='scan-health-badge'>SHIELD &nbsp;YOUR HEALTH. OUR PRIORITY.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # greeting pill + headline + sub
    st.markdown(
        f"""
        <div class='scan-greeting-pill'>HEY {display_name}</div>
        <div class='scan-mega-title'>What are you<br>eating today?</div>
        <div class='scan-mega-sub'>
            Scan a label or upload a photo to get AI-powered safety insights in seconds.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # action row + profile/dropzone row
    use_camera = st.session_state.get("scan_mode") == "camera"

    a1, a2 = st.columns(2)
    with a1:
        st.markdown("<div class='scan-action-btn yellow'>", unsafe_allow_html=True)
        if st.button("UPLOAD IMAGE", use_container_width=True, key="upload_mode_btn"):
            st.session_state["scan_mode"] = "upload"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with a2:
        st.markdown("<div class='scan-action-btn coral'>", unsafe_allow_html=True)
        if st.button("TAKE A PHOTO", use_container_width=True, key="camera_mode_btn"):
            st.session_state["scan_mode"] = "camera"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("&nbsp;")

    p_col, d_col = st.columns([1, 1.4])

    with p_col:
        _render_profile_card(user)
        if st.button("Edit profile  ->", key="goto_profile_btn"):
            st.session_state["page"] = "profile"
            st.rerun()

    with d_col:
        st.markdown("<div class='dropzone-wrap'>", unsafe_allow_html=True)

        uploaded = None
        if use_camera:
            uploaded = st.camera_input("Take a photo of the label")
        else:
            uploaded = st.file_uploader(
                "Drop a label image here, or click to browse",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=False,
                label_visibility="collapsed",
            )

        st.markdown("</div>", unsafe_allow_html=True)

    if uploaded is not None:
        st.markdown("---")
        st.image(uploaded, caption="Selected image", use_container_width=True)
        analyze = st.button("Analyze", type="primary")

        if analyze:
            with st.spinner(
                "Reading the label, looking up ingredients, building your report..."
            ):
                file_bytes = uploaded.getvalue()
                response = api_upload(
                    "/scan/analyze",
                    file_bytes=file_bytes,
                    filename=uploaded.name if hasattr(uploaded, "name") else "scan.jpg",
                    mime=getattr(uploaded, "type", None) or "image/jpeg",
                    params={"email": email},
                )

            if response.status_code != 200:
                st.error(f"Scan failed ({response.status_code}): {response.text}")
                return

            report = response.json()
            st.session_state["last_report"] = report
            st.markdown("---")
            render_report(report)


def render_history() -> None:
    email = st.session_state["email"]

    st.title("Scan history")
    st.caption("Your past scans, newest first.")

    response = api_get("/scan/me", params={"email": email})
    if response.status_code != 200:
        st.error(f"Couldn't load history: {response.text}")
        return

    scans = response.json()
    if not scans:
        st.info("No scans yet. Head over to 'Scan a product' to start.")
        return

    for i, report in enumerate(scans):
        with st.expander(
            f"{report.get('product_name') or 'Unnamed product'} — "
            f"{report.get('overall_verdict', 'unknown')}",
            expanded=(i == 0),
        ):
            render_report(report)


def main() -> None:
    st.set_page_config(
        page_title="Allerjeez",
        page_icon=None,
        layout="wide",
    )
    inject_theme()

    if "email" not in st.session_state:
        render_login()
        return

    email = st.session_state["email"]
    user = fetch_user(email)
    if user is None:
        if st.button("Sign in again"):
            st.session_state.clear()
            st.rerun()
        return

    display_name = _resolve_display_name(user, email)
    st.session_state["display_name"] = user.get("display_name")
    render_sidebar(email, display_name)

    page = st.session_state.get("page", "scan")
    if page == "profile":
        render_profile()
    elif page == "history":
        render_history()
    else:
        render_scan()


if __name__ == "__main__":
    main()
