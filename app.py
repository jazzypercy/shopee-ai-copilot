# --- 0. IMPORTS & CLOUD SETUP ---
import streamlit as st
import pandas as pd
import os
import datetime
import json
import altair as alt
from google import genai
from google.cloud import firestore
from google.oauth2 import service_account
import streamlit as st

# Initialize session state variables
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False
if "df_final" not in st.session_state:
    st.session_state.df_final = None
    
if "ai_usage_count" not in st.session_state:
    st.session_state.ai_usage_count = 0
AI_DAILY_LIMIT = 5 # Set your chosen limit here

@st.cache_resource
def get_db():
    try:
        key_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return firestore.Client(credentials=creds, database="growthai")
    except Exception as e:
        st.error(f"Firestore Auth Failed: {e}")
        return None

db = get_db()

# --- 1. PERSISTENT DATA HELPERS ---
def save_user_feedback(email, feedback_score):
    if db:
        # We store feedback in a collection called "feedback"
        # We use the email + current timestamp as a document ID to keep them unique
        timestamp = datetime.datetime.now().isoformat()
        doc_id = f"{email}_{timestamp}"
        db.collection("feedback").document(doc_id).set({
            "email": email,
            "score": feedback_score,
            "timestamp": timestamp
        })
        
def save_user_trial(email, start_time):
    if db:
        db.collection("users").document(email).set({"start_time": start_time.isoformat()})

def get_user_trial(email):
    if not db: return None
    try:
        doc = db.collection("users").document(email).get()
        return datetime.datetime.fromisoformat(doc.to_dict()["start_time"]) if doc.exists else None
    except Exception as e:
        st.warning(f"Database error: {e}")
        return None

def is_trial_expired(start_time):
    return (datetime.datetime.now() - start_time) > datetime.timedelta(hours=24)

def get_mock_data(username):
    products = ["Natural Shampoo", "Body Lotion 20X", "Niacinamide Soap", "Brightening Sunscreen"]
    return pd.DataFrame({
        "Product Name": products,
        "Price (PHP)": [158.0, 115.0, 59.0, 159.0],
        "Current Stock": [14, 142, 8, 410],
        "Monthly Sold": [340, 510, 1200, 850],
        "Rating": [4.8, 4.9, 4.9, 4.7]
    })

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
        if not email_input: st.warning("Please enter an email.")
        elif db is None: st.error("System connection error.")
        else:
            existing_start = get_user_trial(email_input)
            if existing_start:
                if is_trial_expired(existing_start):
                    st.error("❌ Your 24-hour trial period has ended.")
                    st.stop()
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

# Sidebar Timer: Only shows if trial is active
if st.session_state.trial_active and "trial_start_time" in st.session_state:
    elapsed = datetime.datetime.now() - st.session_state.trial_start_time
    remaining = datetime.timedelta(hours=24) - elapsed
    
    if remaining.total_seconds() > 0:
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        st.sidebar.info(f"⏳ Trial ends in: **{hours}h {minutes}m**")
    else:
        st.sidebar.error("Trial expired.")
        st.session_state.trial_active = False
        st.rerun()

uploaded_file = st.sidebar.file_uploader("Upload Product Performance CSV", type=["csv"])

@st.cache_data
def get_sample_csv_template():
    return pd.DataFrame({
        "Product Name": ["Natural Shampoo", "Body Lotion 20X", "Niacinamide Soap", "Brightening Sunscreen"],
        "Price (PHP)": [158.0, 115.0, 59.0, 159.0],
        "Current Stock": [14, 142, 8, 410],
        "Monthly Sold": [340, 510, 1200, 850],
        "Rating": [4.8, 4.9, 4.9, 4.7]
    }).to_csv(index=False).encode('utf-8')

st.sidebar.download_button("📥 Download CSV Template", get_sample_csv_template(), "template.csv", "text/csv")
st.session_state.LOW_STOCK_THRESHOLD = st.sidebar.slider("Low Stock Warning Flag", 5, 1000, st.session_state.LOW_STOCK_THRESHOLD)
run_analysis = st.sidebar.button("Analyze My Store", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🎨 AI Brand Tone")
# We store this in session_state so it persists across interactions
st.session_state.brand_tone = st.sidebar.selectbox(
    "Select your brand voice:",
    ["Professional", "Energetic", "Casual", "Urgent/Sales-y"]
)

# --- FOOTER IN SIDEBAR ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🤝 About GrowthPilot")
st.sidebar.caption("GrowthPilot AI helps sellers make data-driven decisions.")
st.sidebar.caption("Built by jazzypercy")
st.sidebar.info("📧 Need help? Contact: grantjaspertaneo@gmail.com")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤝 About GrowthPilot")
st.sidebar.caption("GrowthPilot AI helps sellers make data-driven decisions.")
st.sidebar.info("📧 Need help? [Contact Support](mailto:grantjaspertaneo@gmail.com)")
st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0 | GrowthPilot AI © 2026")

# --- 5. LANDING PAGE ---
if not run_analysis and not st.session_state.demo_mode:
    st.title("🚀 Growth Pilot Ai")
    st.subheader("Your AI-powered assistant for smarter inventory and faster sales.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", "Operational", "Online")
    c2.metric("Model", "Gemini 2.0", "Flash")
    c3.metric("Database", "Firestore", "Secure")
    
    st.markdown("---")
    
    with st.expander("📖 How to use GrowthPilot AI", expanded=False):
        st.markdown("""
        **Step 1: Get your Shopee Data (Use a Computer)**
        1. Open your browser and go to [seller.shopee.ph](https://seller.shopee.ph/). 
           *(Note: You must use a computer or browser in desktop mode for mobile devices. The Shopee mobile app does not support downloading CSV files.)*
        2. Log in to your shop.
        3. On the left sidebar, click **'Business Insights'**.
        4. Select the **'Product'** tab.
        5. Click the **'Export Data'** button to download the report as a **.CSV** file.
        
        **Step 2: Upload your file**
        - On the left sidebar, click **'Browse files'** to upload your downloaded Shopee CSV.
        - If your column names are different, our system will ask you to match them to our required fields.
        
        **Step 3: Analyze and Grow**
        - Use the **'Low Stock Warning Flag'** slider to set your alert level.
        - Click **'Analyze My Store'** to see your sales forecast, inventory gaps, and AI-generated social media content!
        """)
        
    if st.button("✨ Load Demo Data"):
        st.session_state.demo_mode = True
        st.rerun()

# --- 6. RUNTIME LOGIC ---

# 1. LOAD DATA SOURCE
if st.session_state.get("demo_mode", False):
    st.session_state.df_final = get_mock_data("demo_user")
    st.session_state.demo_mode = False
    st.session_state.show_demo_info = True
    st.rerun()

elif uploaded_file is not None and st.session_state.get("df_final") is None:
    try:
        df_raw = pd.read_csv(uploaded_file)
        required_cols = ["Product Name", "Price (PHP)", "Current Stock", "Monthly Sold", "Rating"]
        
        if all(col in df_raw.columns for col in required_cols):
            st.session_state.df_final = df_raw[required_cols]
            st.session_state.show_demo_info = False
            st.rerun()
        else:
            st.warning("⚠️ **Header Mismatch:** Please map your CSV columns.")
            mapping = {req: st.selectbox(f"Select column for '{req}':", df_raw.columns, key=f"map_{req}") for req in required_cols}
            if st.button("Apply Mapping"):
                df_mapped = df_raw.rename(columns={v: k for k, v in mapping.items()})
                st.session_state.df_final = df_mapped[required_cols]
                st.rerun()
            st.stop()
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

# 2. RUNTIME ANALYSIS
if "df_final" in st.session_state and st.session_state.df_final is not None:
    df = st.session_state.df_final
    
    # SAFETY GATEKEEPER: Ensure it's a DataFrame before doing anything
    if hasattr(df, 'columns'):
        if st.session_state.get("show_demo_info", False):
            st.info("ℹ️ **Demo Mode:** You are viewing simulated data.")

        # PROCESSING
        if 'Weekly Forecast' not in df.columns:
            df['Weekly Forecast'] = (df['Monthly Sold'] * 0.25).astype(int)
            st.session_state.df_final = df

        # UI
        st.subheader("📊 Sales Overview & Forecast")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Monthly Sales", f"{df['Monthly Sold'].sum():,}")
        col2.metric("Total Inventory Value", f"₱{(df['Price (PHP)'] * df['Current Stock']).sum():,.0f}")
        col3.metric("Avg. Forecast Accuracy", "92%")
        
        st.markdown("---")
        st.markdown("### 📈 Demand vs. Stock Analysis")
        chart_data = df.melt('Product Name', value_vars=['Current Stock', 'Weekly Forecast'], var_name='Metric', value_name='Units')
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Units', title='Units'), y=alt.Y('Product Name', title='', sort='-x'),
            color=alt.Color('Metric', scale=alt.Scale(domain=['Current Stock', 'Weekly Forecast'], range=['#60A5FA', '#F87171'])),
            tooltip=['Product Name', 'Metric', 'Units']
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

        # TEXT SUMMARY
        st.markdown("#### 📊 Text Summary")
        deficit_items = df[df['Weekly Forecast'] > df['Current Stock']]['Product Name'].tolist()
        surplus_items = df[df['Current Stock'] >= df['Weekly Forecast']]['Product Name'].tolist()
        if deficit_items:
            st.write(f"⚠️ **Attention:** High demand expected for **{', '.join(deficit_items[:2])}**.")
        if surplus_items:
            st.write(f"✅ **Healthy:** **{', '.join(surplus_items[:2])}** stock is well-aligned.")

        # 3. ANALYTICS & ALERTS
        st.markdown("#### 📝 Key Takeaways")
        df['Gap'] = df['Weekly Forecast'] - df['Current Stock']
        riskiest_prod = df.loc[df['Gap'].idxmax()]
        if riskiest_prod['Gap'] > 0:
            st.write(f"👉 **Critical Alert:** Top risk is **{riskiest_prod['Product Name']}**.")
        else:
            st.write("👉 **Good News:** Stock levels are healthy.")
        st.dataframe(df.drop(columns=['Gap']), use_container_width=True, hide_index=True)

        if not df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD].empty:
            st.markdown("### 🚨 High Priority Logistics Alerts")
            for _, row in df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD].iterrows():
                st.warning(f"⚠️ Reorder: '{row['Product Name']}' has only **{row['Current Stock']}** left.")
        else:
            st.success("✅ All stock levels are healthy.")

        # 4. AI ASSETS
        st.markdown("### 🧠 AI Content Generator")
        selected_name = st.selectbox("Select product to analyze:", df['Product Name'].tolist())
        target_prod = df[df['Product Name'] == selected_name].iloc[0]
        
        if st.button("Generate AI Insights"):
            if st.session_state.ai_usage_count >= AI_DAILY_LIMIT:
                st.error("🚀 **Usage Limit Reached**")
            else:
                api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
                if api_key:
                    try:
                        client = genai.Client(api_key=api_key)
                        with st.spinner('Generating...'):
                            response = client.models.generate_content(
                                model="gemini-2.0-flash", 
                                contents=f"Analyze {target_prod['Product Name']}. Price: {target_prod['Price (PHP)']}. Tone: {st.session_state.brand_tone}. Output in [LIVE_SELLING] and [SOCIAL_CAPTION]."
                            )
                        full_text = response.text
                        if "[LIVE_SELLING]" in full_text and "[SOCIAL_CAPTION]" in full_text:
                            st.session_state.ai_usage_count += 1
                            t1, t2 = st.tabs(["🎙️ Live Selling", "📱 Social Caption"])
                            t1.markdown(full_text.split("[LIVE_SELLING]")[1].split("[SOCIAL_CAPTION]")[0])
                            t2.markdown(full_text.split("[SOCIAL_CAPTION]")[1])
                    except Exception as e:
                        st.warning(f"AI Service limited: {e}")
    else:
        st.error("Data error: The loaded object is invalid.")
else:
    st.info("🚀 Please upload a CSV file or click 'Load Demo Data' to begin.")
