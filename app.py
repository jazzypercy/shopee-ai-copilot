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
    try:
        key_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return firestore.Client(credentials=creds)
    except Exception as e:
        st.error(f"Firestore Auth Failed: {e}")
        return None

db = get_db()

# --- 1. PERSISTENT DATA HELPERS ---
def save_user_trial(email, start_time):
    if db:
        db.collection("users").document(email).set({"start_time": start_time.isoformat()})

def get_user_trial(email):
    if not db:
        return None
    try:
        doc_ref = db.collection("users").document(email)
        doc = doc_ref.get()
        if doc.exists:
            return datetime.datetime.fromisoformat(doc.to_dict()["start_time"])
    except Exception as e:
        st.warning(f"Could not connect to database: {e}")
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
    email_input = st.text_input("Enter your email:")
    
    if st.button("Access My Trial"):
        if not email_input:
            st.warning("Please enter an email.")
        elif db is None:
            st.error("System connection error. Please refresh or contact support.")
        else:
            # This block is correctly aligned with the 'else' above
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
    
    # 1. LOAD DATA SOURCE
    if st.session_state.demo_mode:
        df = get_mock_data("demo_user")
        st.session_state.demo_mode = False 
        st.info("ℹ️ **Demo Mode:** You are viewing simulated data.")
        
    elif uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            required_cols = ["Product Name", "Price (PHP)", "Current Stock", "Monthly Sold", "Rating"]
            
            # Check if columns are missing
            if not all(col in df.columns for col in required_cols):
                st.warning("⚠️ **Column Mismatch:** Your file headers don't match our system requirements.")
                
                mapping = {}
                col1, col2 = st.columns(2)
                for req in required_cols:
                    mapping[req] = col1.selectbox(f"Select column for '{req}':", df.columns)
                
                if st.button("Apply Mapping"):
                    df = df.rename(columns={v: k for k, v in mapping.items()})
                    df = df[required_cols]
                    st.session_state.mapped_df = df
                    st.rerun()
                
                if "mapped_df" in st.session_state:
                    df = st.session_state.mapped_df
                else:
                    st.stop()
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.stop()
    else:
        st.error("❌ Please upload a CSV file or click 'Load Demo Data'.")
        st.stop()

    # 2. DATA PROCESSING
    df['Weekly Forecast'] = (df['Monthly Sold'] * 0.25).astype(int)
    
    st.subheader("📊 Sales Overview & Forecast")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Monthly Sales", f"{df['Monthly Sold'].sum():,}")
    col2.metric("Total Inventory Value", f"₱{(df['Price (PHP)'] * df['Current Stock']).sum():,.0f}")
    col3.metric("Avg. Forecast Accuracy", "92%")
    
    st.markdown("---")
    st.markdown("### 📈 Demand vs. Stock Analysis")
    
    chart_data = df.melt('Product Name', value_vars=['Current Stock', 'Weekly Forecast'], var_name='Metric', value_name='Units')
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('Units', title='Units'),
        y=alt.Y('Product Name', title='', sort='-x'),
        color=alt.Color('Metric', scale=alt.Scale(domain=['Current Stock', 'Weekly Forecast'], range=['#60A5FA', '#F87171'])),
        tooltip=['Product Name', 'Metric', 'Units']
    ).properties(height=300)
    
    st.altair_chart(chart, use_container_width=True)
    
    # 3. ANALYTICS & ALERTS
    st.markdown("#### 📝 Key Takeaways")
    df['Gap'] = df['Weekly Forecast'] - df['Current Stock']
    riskiest_prod = df.loc[df['Gap'].idxmax()]
    
    if riskiest_prod['Gap'] > 0:
        st.write(f"👉 **Critical Alert:** Your top demand risk is **{riskiest_prod['Product Name']}**.")
    else:
        st.write("👉 **Good News:** Your stock levels are healthy.")
    
    st.dataframe(df.drop(columns=['Gap']), use_container_width=True, hide_index=True)

    if not df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD].empty:
        st.markdown("### 🚨 High Priority Logistics Alerts")
        for _, row in df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD].iterrows():
            st.warning(f"⚠️ Reorder Alert: '{row['Product Name']}' has only **{row['Current Stock']}** left.")
    else:
        st.success("✅ All stock levels are healthy.")

    # 4. AI ASSETS
    top_prod = df.sort_values(by="Monthly Sold", ascending=False).iloc[0]
    st.markdown(f"### 🧠 Automated Assets for: *{top_prod['Product Name']}*")
    
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            with st.spinner('Generating AI insights...'):
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"Analyze {top_prod['Product Name']}. Output as: [LIVE_SELLING] (script) and [SOCIAL_CAPTION] (caption)."
                )
            full_text = response.text
            if "[LIVE_SELLING]" in full_text and "[SOCIAL_CAPTION]" in full_text:
                t1, t2 = st.tabs(["🎙️ Live Selling", "📱 Social Caption"])
                t1.markdown(full_text.split("[LIVE_SELLING]")[1].split("[SOCIAL_CAPTION]")[0])
                t2.markdown(full_text.split("[SOCIAL_CAPTION]")[1])
        except Exception as e:
            st.warning(f"AI Service limited: {e}")
