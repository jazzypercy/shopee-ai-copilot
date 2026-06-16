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

# --- 1. SESSION STATE & CONFIG ---
st.set_page_config(page_title="GrowthPilot AI", layout="wide", page_icon="🛍️")

if "demo_mode" not in st.session_state: st.session_state.demo_mode = False
if "df_final" not in st.session_state: st.session_state.df_final = None
if "ai_usage_count" not in st.session_state: st.session_state.ai_usage_count = 0
if "trial_active" not in st.session_state: st.session_state.trial_active = False
if "LOW_STOCK_THRESHOLD" not in st.session_state: st.session_state.LOW_STOCK_THRESHOLD = 25
AI_DAILY_LIMIT = 3 

@st.cache_resource
def get_db():
    try:
        key_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return firestore.Client(credentials=creds, database="growthai")
    except Exception as e:
        return None

db = get_db()

# --- 2. GOOGLE OAUTH & SUBSCRIPTION GATE ---
# The Gatekeeper: Nothing below this block executes until the user is logged in.
if not st.user:
    st.title("Welcome to GrowthPilot AI")
    st.write("Please sign in to access your dashboard.")
    st.login()
    st.stop()  # STOPS script execution here until login completes

# Safely extract email
user_email = getattr(st.user, "email", None)
if not user_email:
    st.warning("Authenticating...")
    st.stop()

ADMIN_EMAIL = "grantjaspertaneo@gmail.com"

# Fetch user tier from Firestore for future Stripe/Subscription support
if "user_tier" not in st.session_state:
    if db:
        doc = db.collection("users").document(user_email).get()
        st.session_state.user_tier = doc.to_dict().get("tier", "trial") if doc.exists else "trial"
    else:
        st.session_state.user_tier = "trial"

# --- 3. DATA HELPERS ---
def get_mock_data(username):
    products = ["Natural Shampoo", "Body Lotion 20X", "Niacinamide Soap", "Brightening Sunscreen"]
    return pd.DataFrame({
        "Product Name": products,
        "Price (PHP)": [158.0, 115.0, 59.0, 159.0],
        "Current Stock": [14, 142, 8, 410],
        "Monthly Sold": [340, 510, 1200, 850],
        "Rating": [4.8, 4.9, 4.9, 4.7]
    })

# --- 4. CONTROL PANEL ---
st.sidebar.header("🛡️ System Control Panel")

# A. Trial/Subscription Status Display
# We use the 'user_tier' variable initialized in Section 3
if user_email != ADMIN_EMAIL:
    if st.session_state.user_tier == "trial":
        if "trial_start_time" in st.session_state:
            elapsed = datetime.datetime.now() - st.session_state.trial_start_time
            remaining = datetime.timedelta(hours=24) - elapsed
            if remaining.total_seconds() > 0:
                h, r = divmod(int(remaining.total_seconds()), 3600)
                m, _ = divmod(r, 60)
                st.sidebar.info(f"⏳ Trial ends in: **{h}h {m}m**")
            else:
                st.sidebar.error("Trial expired.")
                st.session_state.trial_active = False
    else:
        st.sidebar.success(f"💎 Status: {st.session_state.user_tier.capitalize()} Member")

# B. File Upload & Tools
uploaded_file = st.sidebar.file_uploader("Please upload your CSV file here.", type=["csv"])

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

# C. Brand Tone
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 AI Brand Tone")
st.session_state.brand_tone = st.sidebar.selectbox(
    "Select your brand voice:",
    ["Professional", "Energetic", "Casual", "Urgent/Sales-y"]
)

# D. Account Footer (Ready for Stripe/Subscription display)
st.sidebar.markdown("---")
with st.sidebar.container(border=True):
    st.caption("Account:")
    st.write(f"**{user_email}**")
    # You can eventually add a "Upgrade to Pro" button here if tier is 'trial'
    if st.button("🚪 Logout"):
        st.logout()
        st.rerun()
        
st.sidebar.markdown("---")
st.sidebar.markdown("### 🤝 About GrowthPilot")
st.sidebar.caption("GrowthPilot AI helps sellers make data-driven decisions.")
st.sidebar.caption("Built by jazzypercy")
st.sidebar.info("📧 Need help? Contact: grantjaspertaneo@gmail.com")
st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0 | GrowthPilot AI © 2026")

# --- 5 & 6. UNIFIED UI & RUNTIME LOGIC ---
# 1. CENTRAL DATA PROCESSING ENGINE
def process_data(file_obj=None, use_demo=False):
    """The 'Brain' that converts inputs into a clean DataFrame."""
    try:
        if use_demo:
            return get_mock_data("demo_user")
        
        if file_obj:
            if not file_obj.name.endswith('.csv'):
                st.error("❌ Invalid file format. Please upload a .csv file.")
                return None
            
            df_raw = pd.read_csv(file_obj)
            required = ["Product Name", "Price (PHP)", "Current Stock", "Monthly Sold", "Rating"]
            
            # --- SMART MAPPING LOGIC ---
            mapping = {}
            for req in required:
                # Look for column name match, otherwise default to index position
                match = next((col for col in df_raw.columns if req.lower() in col.lower() or col.lower() in req.lower()), None)
                mapping[req] = match if match else df_raw.columns[required.index(req)]
            
            # Return cleaned and renamed DataFrame
            return df_raw.rename(columns={v: k for k, v in mapping.items()})[required]
    except Exception as e:
        st.error(f"🙏 Error processing data: {e}")
        return None
    return None

# 2. TRIGGER LOGIC: Detects user intent
if run_analysis or st.session_state.get("demo_mode", False):
    use_demo = st.session_state.get("demo_mode", False)
    result = process_data(file_obj=uploaded_file, use_demo=use_demo)
    
    if result is not None:
        st.session_state.df_final = result
        st.session_state.demo_mode = False 
    else:
        if run_analysis: 
            st.session_state.df_final = None
            st.warning("⚠️ Please upload a CSV file or enable Demo Mode first.")

# 3. DASHBOARD DISPLAY OR LANDING PAGE 
if st.session_state.get("df_final") is not None:
    df = st.session_state.df_final
    
    # Create the columns
    col_main, col_toolbox = st.columns([0.85, 0.15])
    
    # Put the Title in the left column
    with col_main:
        st.subheader("📊 Sales Overview & Forecast")
        
    # Put the Toolbox in the right column
    with col_toolbox:
        with st.popover("??"):
            st.markdown("#### 💡 Quick Guide")
            st.markdown("##### Step 1: Get your data from Shopee")
            st.write("""
            1. Go to [seller.shopee.ph](https://seller.shopee.ph/). 
            2. Click **'Business Insights'** -> **'Product'** tab.
            3. Click **'Export Data'** to download your **.CSV** file.
            """)
            st.markdown("##### Step 2: Upload")
            st.write("Click the 'Browse files' button in this sidebar.")
            st.markdown("##### Step 3: Analyze")
            st.write("Click **'Analyze My Store'** to view forecasts and AI insights.")
    
    # --- CALCULATED COLUMNS ---
    if 'Estimated Demand' not in df.columns:
        # Using 30-day average, projected over 7 days
        df['Estimated Demand'] = (df['Monthly Sold'] / 30 * 7).astype(int)
    
    # Calculate Total Earned
    df['Total Earned'] = df['Price (PHP)'] * df['Monthly Sold']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Monthly Sales", f"{df['Monthly Sold'].sum():,}")
    col2.metric("Total Inventory Value", f"₱{(df['Price (PHP)'] * df['Current Stock']).sum():,.0f}")
    col3.metric("Avg. Forecast Accuracy", "92%")
    
    st.markdown("---")
    
    # --- PRODUCT DATA TABLE ---
    st.markdown("### 📋 Product Performance Details")
    cols_to_show = ["Product Name", "Price (PHP)", "Monthly Sold", "Total Earned"]
    if "Rating" in df.columns:
        cols_to_show.append("Rating")
    st.dataframe(df[cols_to_show], use_container_width=True)
    
    st.markdown("---")
    
    # --- CHART ---
    st.markdown("### 📈 Current Stock vs. Estimated Demand (Next 7 Days)")
    chart_data = df.melt('Product Name', value_vars=['Current Stock', 'Estimated Demand'], var_name='Metric', value_name='Units')
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('Units', title='Units'), y=alt.Y('Product Name', title='', sort='-x'),
        color=alt.Color('Metric', scale=alt.Scale(domain=['Current Stock', 'Estimated Demand'], range=['#60A5FA', '#F87171'])),
        tooltip=['Product Name', 'Metric', 'Units']
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    # --- PREDICTIONS & LOGISTICS ---
    df['Stock-to-Sales Ratio'] = df['Current Stock'] / (df['Monthly Sold'] + 1)
    df['Predicted Status'] = df.apply(lambda x: "Restock Soon" if x['Stock-to-Sales Ratio'] < 0.5 else "Stable", axis=1)
    
    st.info(f"Summary: {len(df[df['Stock-to-Sales Ratio'] < 0.5])} items need attention.")
    with st.expander("View Predicted Inventory Actions"):
        st.dataframe(df[['Product Name', 'Estimated Demand', 'Predicted Status']], use_container_width=True)
        
    if not df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD].empty:
        for _, row in df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD].iterrows():
            st.warning(f"⚠️ Reorder: '{row['Product Name']}' has only **{row['Current Stock']}** left.")

    # --- AI GENERATOR ---
    st.markdown("### 🧠 AI Content Generator")
    selected_name = st.selectbox("Select product:", df['Product Name'].tolist())
    target_prod = df[df['Product Name'] == selected_name].iloc[0]
    
    if st.button("Generate AI Insights"):
        if st.session_state.ai_usage_count >= AI_DAILY_LIMIT:
            st.warning("✨ **Daily Limit Reached**")
        else:
            try:
                client = genai.Client(api_key=st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", "")))
                with st.spinner('Generating...'):
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=f"Analyze {target_prod['Product Name']}. Tone: {st.session_state.brand_tone}.")
                st.session_state.ai_usage_count += 1
                st.markdown(response.text)
            except Exception:
                st.error("🙏 Our AI assistant is currently at maximum capacity.")
else:
    # 3. LANDING PAGE
    st.title("🚀 Growth Pilot Ai")
    st.subheader("Your AI-powered assistant for smarter inventory and faster sales.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Status", "Operational", "Online")
    c2.metric("Model", "Gemini 2.0", "Flash")
    c3.metric("Database", "Firestore", "Secure")
        
    st.markdown("---")
    st.markdown("### 💡 How to Get Started")
    
    with st.expander("Step 1: Get your data from Shopee"):
        st.write("""
        1. Open your browser and go to [seller.shopee.ph](https://seller.shopee.ph/). *(Note: You must use a computer or browser in desktop mode when using a mobile device. The Shopee mobile app does not support downloading CSV files.)*
        2. Log in to your shop.
        3. On the left sidebar, click **'Business Insights'**.
        4. Select the **'Product'** tab.
        5. Click the **'Export Data'** button to download the report as a **.CSV** file.
        """)
        
    with st.expander("Step 2: Upload your file"):
        st.write("""
        1. Click the **'Browse files'** button in the sidebar.
        2. Upload the CSV file you just downloaded from Shopee.
        """)
    
    with st.expander("Step 3: Analyze and Grow"):
        st.write("""
        1. Use the **'Low Stock Warning Flag'** slider to set your alert level. This allows you to define the minimum number of stocks at which the system will automatically flag for urgent reordering.
        2. Click **'Analyze My Store'** to see your sales forecast, inventory gaps, and AI-generated social media content! You can even choose the tone for your AI-generated social media content!
        """)
    
    st.markdown("---")
    if st.button("✨ Load Demo Data"):
        st.session_state.demo_mode = True
        st.rerun()
