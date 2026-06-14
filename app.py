import streamlit as st
import pandas as pd
from curl_cffi import requests
from google import genai
import os

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="AI E-Commerce Co-Pilot", layout="wide", page_icon="🛍️")

# --- 2. INITIALIZE SESSION STATE ---
if "trial_active" not in st.session_state:
    st.session_state.trial_active = False

# --- 3. THE "GATE" LOGIC ---
if not st.session_state.trial_active:
    st.title("Welcome to Shopee AI Copilot")
    st.info("Experience the future of inventory management.")
    st.subheader("Start your 2-day free trial")
    st.write("Get full access to the AI insights engine using our sandbox environment.")
    
    if st.button("Start Free Trial"):
        st.session_state.trial_active = True
        st.rerun() 
    
    st.stop() 

# --- 4. THE "APP" ZONE (Only runs if trial_active is True) ---

# --- THE BANNER ---
st.warning("⚠️ Sandbox Mode: Using sample inventory data for demonstration purposes.")

st.title("🚀 Shopee AI E-Commerce Co-Pilot")
st.markdown("Automate inventory velocity checking, manage stockouts, and instantly write high-converting content for your shop.")
st.markdown("---")

# --- 5. LEFT CONTROL PANEL ---
st.sidebar.header("🛡️ System Control Panel")
store_username = st.sidebar.text_input("Target Store Username", value="asepskin_ph")
LOW_STOCK_THRESHOLD = st.sidebar.slider("Low Stock Level Warning Flag", min_value=5, max_value=1000, value=25)
run_analysis = st.sidebar.button("Launch Autonomous Store Audit", type="primary", use_container_width=True)

# --- 6. DATA ENGINES ---
def get_mock_data(username):
    products = [f"[{username.upper()}] Natural Shampoo", f"[{username.upper()}] Body Lotion", f"[{username.upper()}] Milky Soap"]
    mock_inventory = {
        "Product Name": products,
        "Price (PHP)": [158.00, 115.00, 59.00],
        "Current Stock": [14, 142, 8],
        "Monthly Sold": [340, 510, 1200]
    }
    return pd.DataFrame(mock_inventory), f"{username.title()} (System Backup Mode)"

def get_shopee_store_items(username):
    # (Scraping logic remains the same...)
    return get_mock_data(username) # Defaults to mock for demo purposes

# --- 7. RUNTIME LOGIC ---
if run_analysis:
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    
    if not api_key:
        st.error("🔒 Platform Configuration: API Key missing.")
    else:
        with st.spinner("📡 Connecting to storefront..."):
            df, result_meta = get_shopee_store_items(store_username.strip())
            
        st.success(f"📊 Live Stream Connected: **{result_meta}**")
        st.dataframe(df, use_container_width=True)
        
        top_product = df.sort_values(by="Monthly Sold", ascending=False).iloc[0]
        st.markdown(f"### 🧠 Automated Sales Assets for: *{top_product['Product Name']}*")
        
        prompt = f"""Analyze {top_product['Product Name']} (₱{top_product['Price (PHP)']}).
        Provide output with exactly these two headers:
        [LIVE_SELLING] (High-energy script with 'budol' and 'check-out na')
        [SOCIAL_CAPTION] (Instagram/Shopee Feed style with emojis)"""
        
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
            
            # Split AI response into two tabs
            full_text = response.text
            live_script = full_text.split("[LIVE_SELLING]")[1].split("[SOCIAL_CAPTION]")[0]
            social_cap = full_text.split("[SOCIAL_CAPTION]")[1]
            
            tab1, tab2 = st.tabs(["🎙️ Live Selling Script", "📱 Social Media Caption"])
            with tab1: st.markdown(live_script)
            with tab2: st.markdown(social_cap)
            
        except Exception as e:
            st.error(f"AI Error: {e}")
