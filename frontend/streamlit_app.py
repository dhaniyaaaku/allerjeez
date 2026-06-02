"""Allerjeez Streamlit frontend.

Run with: uv run streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_BASE_URL = os.environ.get("ALLERJEEZ_API_URL", "http://127.0.0.1:8000")
HTTP_TIMEOUT = 10.0


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


def api_post(path: str, json: dict) -> httpx.Response:
    return httpx.post(f"{API_BASE_URL}{path}", json=json, timeout=HTTP_TIMEOUT)


def api_get(path: str, params: dict | None = None) -> httpx.Response:
    return httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=HTTP_TIMEOUT)


def api_put(path: str, json: dict, params: dict | None = None) -> httpx.Response:
    return httpx.put(
        f"{API_BASE_URL}{path}", json=json, params=params, timeout=HTTP_TIMEOUT
    )


def render_login() -> None:
    st.title("Allerjeez")
    st.caption("AI-powered food ingredient safety analyser")

    st.markdown("### Sign in")
    st.caption(
        "Enter your email to start. Allerjeez doesn't require a password — "
        "this is a portfolio demo, not a production app."
    )

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        display_name = st.text_input(
            "Display name (optional)", placeholder="What should we call you?"
        )
        submitted = st.form_submit_button("Continue")

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
        st.rerun()


def render_profile() -> None:
    email = st.session_state["email"]

    response = api_get("/users/me", params={"email": email})
    if response.status_code != 200:
        st.error(f"Couldn't load your profile: {response.text}")
        if st.button("Log out"):
            st.session_state.clear()
            st.rerun()
        return

    user = response.json()
    display_name = user.get("display_name") or email

    with st.sidebar:
        st.markdown(f"**Signed in as**\n\n{display_name}")
        st.caption(email)
        if st.button("Log out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.title(f"Hi, {display_name}.")
    st.caption(
        "Set up your health profile. Allerjeez will use this to personalize "
        "every food product scan."
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


def main() -> None:
    st.set_page_config(
        page_title="Allerjeez",
        page_icon=None,
        layout="centered",
    )

    if "email" not in st.session_state:
        render_login()
    else:
        render_profile()


if __name__ == "__main__":
    main()
