# --- 0. IMPORTS & CLOUD SETUP ---
import streamlit as st
import pandas as pd
import os
from google import genai
import datetime
import json
import altair as alt
from google.cloud import firestore
from google.oauth2 import service_account

@st.cache_resource
def get_db():
    key_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return firestore.Client(credentials=creds)

db = get_db()

# --- 1. PERSISTENT DATA HELPERS ---
def save_user_trial(email, start_time):
    db.collection("users").document(email).set({"start_time": start_time.isoformat()})

def get_user_trial(email):
    doc = db.collection("users").document(email).get()
    if doc.exists:
        return datetime.datetime.fromisoformat(doc.to_dict()["start_time"])
    return None

def is_trial_expired(start_time):
    return (datetime.datetime.now() - start_time) > datetime.timedelta(hours=24)

# --- 2. CONFIGURATION & STATE ---
st.set_page_config(page_title="GrowthPilot AI", layout="wide", page_icon="🛍️")

if "trial_active" not in st.session_state: st.session_state.trial_active = False
if "LOW_STOCK_THRESHOLD" not in st.session_state: st.session_state.LOW_STOCK_THRESHOLD = 25
if "demo_mode" not in st.session_state: st.session_state.demo_mode = False

# --- 3. THE STRICT TRIAL GATE ---
if not st.session_state.trial_active:
    st.title("Welcome to GrowthPilot AI")
    email_input = st.text_input("Enter your email to start/resume your trial:")
    
    if st.button("Access My Trial"):
        if not email_input:
            st.warning("Please enter a valid email address.")
        else:
            disposable_domains = ["mailinator.com", "10minutemail.com", "guerrillamail.com"]
            if any(domain in email_input for domain in disposable_domains):
                st.error("Please use a professional or personal email.")
            else:
                existing_start = get_user_trial(email_input)
                if existing_start:
                    if is_trial_expired(existing_start):
                        st.error("❌ Your 24-hour trial period has ended.")
                        st.stop()
                    else:
                        st.session_state.trial_start_time = existing_start
                else:
                    st.session_state.trial_start_time = datetime.datetime.now()
                    save_user_trial(email_input, st.session_state.trial_start_time)
                
                st.session_state.user_email = email_input
                st.session_state.trial_active = True
                st.rerun()
    st.stop()

# --- 4. CONTROL PANEL ---
st.sidebar.header("🛡️ System Control Panel")
uploaded_file = st.sidebar.file_uploader("Upload Product Performance CSV", type=["csv"])

@st.cache_data
def get_sample_csv_template():
    df = pd.DataFrame({
        "Product Name": ["Natural Shampoo", "Body Lotion 20X", "Niacinamide Soap", "Brightening Sunscreen"],
        "Price (PHP)": [158.0, 115.0, 59.0, 159.0],
        "Current Stock": [14, 142, 8, 410],
        "Monthly Sold": [340, 510, 1200, 850],
        "Rating": [4.8, 4.9, 4.9, 4.7]
    })
    return df.to_csv(index=False).encode('utf-8')

st.sidebar.download_button("📥 Download CSV Template", get_sample_csv_template(), "template.csv", "text/csv")
st.session_state.LOW_STOCK_THRESHOLD = st.sidebar.slider("Low Stock Warning Flag", 5, 1000, st.session_state.LOW_STOCK_THRESHOLD)
run_analysis = st.sidebar.button("Analyze My Store", type="primary", use_container_width=True)

# --- 5. LANDING PAGE ---
if not run_analysis and not st.session_state.demo_mode:
    st.title("🚀 Growth Pilot Ai")
    with st.popover("📖 How to use GrowthPilot AI"):
        st.markdown("1. Upload CSV or Load Demo Data.\n2. Configure stock thresholds.\n3. Analyze to get AI assets.")
    if st.button("✨ Load Demo Data"):
        st.session_state.demo_mode = True
        st.rerun()

# --- 6. RUNTIME LOGIC ---
if run_analysis or st.session_state.demo_mode:
    # Logic for processing data (as provided in your snippet)
    # Ensure this block handles mapping and data processing as you already designed.
    # [Insert your existing Section 7 code here]
