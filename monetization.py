"""
StudyLoop Monetization Module (Supabase version)
--------------------------------------------------
Same features as before — login, usage tracking, freemium paywall,
Paystack payments — but backed by Supabase (hosted Postgres) instead
of SQLite, so your data survives redeploys on Streamlit Cloud.

SETUP STEPS:

1. Create a free account at https://supabase.com and click "New Project".
   Pick any name/password/region — the password is only for the DB
   dashboard, not something users will ever type.

2. Once the project is ready, go to the SQL Editor (left sidebar) and
   run this to create your tables:

    create table users (
        email text primary key,
        password_hash text not null,
        is_premium boolean default false,
        created_at timestamp default now()
    );

    create table usage (
        email text references users(email),
        month text,
        count integer default 0,
        primary key (email, month)
    );

3. Go to Project Settings > API. You'll need two values:
     - Project URL   (looks like https://xxxx.supabase.co)
     - anon public key   (a long string starting with "eyJ...")

4. pip install supabase streamlit requests

5. Store these as secrets (same place as your Paystack key):
   In Streamlit Cloud: App settings > Secrets, add:

       SUPABASE_URL = "https://xxxx.supabase.co"
       SUPABASE_KEY = "eyJxxxxxxxx..."
       PAYSTACK_SECRET_KEY = "sk_test_xxxxxxxx"

   Locally: put the same lines in .streamlit/secrets.toml
   (and make sure that file is in .gitignore).

6. Save this file as `monetization.py` next to your app.py and import
   from it exactly as before — the function names are unchanged, so
   nothing else in your app needs to change.
"""

import os
import hashlib
import requests
import streamlit as st
from datetime import date
from supabase import create_client, Client

FREE_MONTHLY_LIMIT = 5  # number of free recordings/summaries per month

SUPABASE_URL = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY") or st.secrets.get("PAYSTACK_SECRET_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db():
    """
    Nothing to do here at runtime — tables are created once in the
    Supabase SQL Editor (see setup step 2 above). This function is
    kept so your app.py import line doesn't need to change.
    """
    pass


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------------------------------------------------------------
# USER ACCOUNTS (SIGNUP / LOGIN)
# ---------------------------------------------------------------------

def create_user(email: str, password: str) -> bool:
    existing = supabase.table("users").select("email").eq("email", email).execute()
    if existing.data:
        return False  # already registered
    supabase.table("users").insert({
        "email": email,
        "password_hash": _hash_password(password),
        "is_premium": False,
    }).execute()
    return True


def verify_user(email: str, password: str) -> bool:
    result = supabase.table("users").select("password_hash").eq("email", email).execute()
    if not result.data:
        return False
    return result.data[0]["password_hash"] == _hash_password(password)


def is_premium(email: str) -> bool:
    result = supabase.table("users").select("is_premium").eq("email", email).execute()
    if not result.data:
        return False
    return bool(result.data[0]["is_premium"])


def set_premium(email: str):
    supabase.table("users").update({"is_premium": True}).eq("email", email).execute()


def login_block():
    """
    Renders a login/signup form and stores the logged-in user's email
    in st.session_state['user_email']. Returns the email if logged in,
    otherwise halts the app until they do.
    """
    if "user_email" in st.session_state:
        return st.session_state["user_email"]

    st.subheader("Welcome to StudyLoop")
    tab1, tab2 = st.tabs(["Log In", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Log In"):
            if verify_user(email, password):
                st.session_state["user_email"] = email
                st.rerun()
            else:
                st.error("Incorrect email or password.")

    with tab2:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_pw")
        if st.button("Create Account"):
            if create_user(new_email, new_password):
                st.success("Account created. Please log in.")
            else:
                st.error("That email is already registered.")

    st.stop()


# ---------------------------------------------------------------------
# USAGE TRACKING + PAYWALL
# ---------------------------------------------------------------------

def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def get_usage(email: str) -> int:
    result = (
        supabase.table("usage")
        .select("count")
        .eq("email", email)
        .eq("month", _current_month())
        .execute()
    )
    return result.data[0]["count"] if result.data else 0


def log_usage(email: str):
    """Call this every time the user records a lecture / generates a summary."""
    month = _current_month()
    existing = (
        supabase.table("usage")
        .select("count")
        .eq("email", email)
        .eq("month", month)
        .execute()
    )
    if existing.data:
        new_count = existing.data[0]["count"] + 1
        supabase.table("usage").update({"count": new_count}).eq("email", email).eq("month", month).execute()
    else:
        supabase.table("usage").insert({"email": email, "month": month, "count": 1}).execute()


def check_usage_limit(email: str) -> bool:
    """Call this BEFORE letting the user record/summarize."""
    if is_premium(email):
        return True
    return get_usage(email) < FREE_MONTHLY_LIMIT


# ---------------------------------------------------------------------
# PAYSTACK PAYMENT (unchanged from the SQLite version)
# ---------------------------------------------------------------------

def start_paystack_payment(email: str, amount_naira: int):
    url = "https://api.paystack.co/transaction/initialize"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    payload = {
        "email": email,
        "amount": amount_naira * 100,  # kobo
        "callback_url": "https://your-app-url.streamlit.app",  # update after deploy
    }
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    if data.get("status"):
        return data["data"]["authorization_url"], data["data"]["reference"]
    return None, None


def verify_paystack_payment(reference: str) -> bool:
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    response = requests.get(url, headers=headers)
    data = response.json()
    return data.get("data", {}).get("status") == "success"


def show_upgrade_button(email: str):
    st.warning(f"You've used your {FREE_MONTHLY_LIMIT} free sessions this month.")
    if st.button("Upgrade to Premium – ₦2000/month"):
        checkout_url, reference = start_paystack_payment(email, 2000)
        if checkout_url:
            st.session_state["pending_reference"] = reference
            st.markdown(f"[Click here to complete payment]({checkout_url})")
        else:
            st.error("Could not start payment. Check your Paystack key.")

    if "pending_reference" in st.session_state:
        if st.button("I've completed payment — verify now"):
            if verify_paystack_payment(st.session_state["pending_reference"]):
                set_premium(email)
                del st.session_state["pending_reference"]
                st.success("Payment confirmed! You're now Premium.")
                st.rerun()
            else:
                st.error("Payment not confirmed yet. Try again in a moment.")


# ---------------------------------------------------------------------
# HOW TO WIRE THIS INTO YOUR EXISTING app.py  (unchanged)
# ---------------------------------------------------------------------
"""
At the very top of app.py:

    from monetization import (
        init_db, login_block, check_usage_limit,
        log_usage, show_upgrade_button
    )

    init_db()
    user_email = login_block()   # blocks until logged in

Wherever your existing code records a lecture or generates a summary:

    if check_usage_limit(user_email):
        # ... your existing StudyLoop recording/summary code goes here ...
        log_usage(user_email)
    else:
        show_upgrade_button(user_email)
"""
