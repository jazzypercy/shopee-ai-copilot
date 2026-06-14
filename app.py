import streamlit as st
import pandas as pd
import os
from google import genai
import datetime

# --- TRIAL LOGIC INITIALIZATION ---
if "trial_active" not in st.session_state:
    st.session_state.trial_active = False
if "trial_start_time" not in st.session_state:
    st.session_state.trial_start_time = None
if "LOW_STOCK_THRESHOLD" not in st.session_state:
    st.session_state.LOW_STOCK_THRESHOLD = 25

def get_trial_remaining():
    if not st.session_state.trial_start_time:
        return "N/A"
    elapsed = datetime.datetime.now() - st.session_state.trial_start_time
    remaining = (datetime.timedelta(hours=24) - elapsed)
    if remaining.total_seconds() <= 0:
        return "Expired"
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AI E-Commerce Co-Pilot", layout="wide", page_icon="🛍️")

# Persistent State Initialization
if "trial_active" not in st.session_state:
    st.session_state.trial_active = False
if "LOW_STOCK_THRESHOLD" not in st.session_state:
    st.session_state.LOW_STOCK_THRESHOLD = 25

# --- 2. TRIAL GATE ---
if not st.session_state.trial_active:
    st.title("Welcome to Shopee AI Copilot")
    st.info("Experience the future of inventory management with our 1-Day Trial.")
    if st.button("Start 1-Day Free Trial"):
        st.session_state.trial_active = True
        st.session_state.trial_start_time = datetime.datetime.now()
        st.rerun()
    st.stop()

# Check if expired
if get_trial_remaining() == "Expired":
    st.error("⏰ Your 1-Day Free Trial has expired.")
    if st.button("Contact Support to Upgrade"):
        st.write("Redirecting to sales...")
    st.stop()

# --- 3. THE APP ZONE ---
st.warning(f"⚠️ Sandbox Mode: {get_trial_remaining()} remaining in your 1-Day Trial.")
st.title("🚀 Shopee AI E-Commerce Co-Pilot")

# --- 4. CONTROL PANEL ---
st.sidebar.header("🛡️ System Control Panel")
store_username = st.sidebar.text_input("Target Store Username", value="asepskin_ph")

st.sidebar.markdown("### 📦 Supply Parameters")
st.session_state.LOW_STOCK_THRESHOLD = st.sidebar.slider(
    "Low Stock Level Warning Flag", 5, 1000, st.session_state.LOW_STOCK_THRESHOLD
)

run_analysis = st.sidebar.button("Launch Autonomous Store Audit", type="primary", use_container_width=True)

# --- CONTACT SECTION ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📩 Need Assistance?")
st.sidebar.write("Have questions or want to upgrade your plan?")
st.sidebar.info("📧 **[your-email@example.com](mailto:your-email@example.com)**")
st.sidebar.write("We typically respond within 2 hours.")

# --- 5. DATA ENGINE ---
def get_mock_data(username):
    products = [f"[{username.upper()}] {item}" for item in [
        "Natural Shampoo", "Body Lotion 20X", "Niacinamide Soap", 
        "Brightening Sunscreen", "Premium EDP Perfume", "Collagen Serum", 
        "Vitamin C Toner", "Hair Growth Oil", "Aloe Vera Gel", "Matte Lipstick"
    ]]
    return pd.DataFrame({
        "Product Name": products,
        "Price (PHP)": [158.0, 115.0, 59.0, 159.0, 125.0, 299.0, 89.0, 199.0, 75.0, 249.0],
        "Current Stock": [14, 142, 8, 410, 50, 55, 30, 22, 120, 15],
        "Monthly Sold": [340, 510, 1200, 850, 0, 150, 400, 95, 600, 210],
        "Rating": [4.8, 4.9, 4.9, 4.7, 4.5, 4.9, 4.8, 4.7, 4.9, 4.8]
    })

# --- 6. RUNTIME LOGIC ---
if run_analysis:
    df = get_mock_data(store_username)
    
    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={
            "Price (PHP)": st.column_config.NumberColumn(format="₱%.2f"),
            "Rating": st.column_config.NumberColumn(format="⭐ %.2f")
        }
    )

    # ALERTS
    low_stock_df = df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD]
    if not low_stock_df.empty:
        st.markdown("### 🚨 High Priority Logistics Alerts")
        for _, row in low_stock_df.iterrows():
            if row['Current Stock'] == 0:
                st.error(f"❌ **OUT OF STOCK:** '{row['Product Name']}' is completely depleted!")
            else:
                st.warning(f"⚠️ **Reorder Alert:** '{row['Product Name']}' has only **{row['Current Stock']}** pieces left.")
    else:
        st.success("✅ All stock levels are currently healthy.")

    # AI ASSETS
    top_prod = df.sort_values(by="Monthly Sold", ascending=False).iloc[0]
    st.markdown(f"### 🧠 Automated Assets for: *{top_prod['Product Name']}*")
    
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    ai_success = False
    
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            # gemini-3.5-flash is the current stable production standard as of June 2026
            response = client.models.generate_content(
                model="gemini-3.5-flash", 
                contents=f"Analyze {top_prod['Product Name']}. Output as: [LIVE_SELLING] (script) and [SOCIAL_CAPTION] (Instagram caption)."
            )
            
            full_text = response.text
            if "[LIVE_SELLING]" in full_text and "[SOCIAL_CAPTION]" in full_text:
                tab1, tab2 = st.tabs(["🎙️ Live Selling", "📱 Social Caption"])
                with tab1: st.markdown(full_text.split("[LIVE_SELLING]")[1].split("[SOCIAL_CAPTION]")[0])
                with tab2: st.markdown(full_text.split("[SOCIAL_CAPTION]")[1])
                ai_success = True
        except Exception as e:
            st.warning(f"AI Service limited or key issue: {e}")
    
    if not ai_success:
        st.info("💡 **Fallback Template:**")
        st.markdown(f"**Check out {top_prod['Product Name']}!** Limited stocks. Mine na before it's gone! #Budol #ShopeePH")
