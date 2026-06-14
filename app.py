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
    st.subheader("Start your 14-day free trial")
    st.write("Get full access to the AI insights engine using our sandbox environment.")
    
    if st.button("Start Free Trial"):
        st.session_state.trial_active = True
        st.rerun() 
    
    st.stop() 

# --- 4. THE "APP" ZONE ---
st.warning("⚠️ Sandbox Mode: Using sample inventory data for demonstration purposes.")
st.title("🚀 Shopee AI E-Commerce Co-Pilot")
st.markdown("Automate inventory velocity checking, manage stockouts, and instantly write high-converting content for your shop.")
st.markdown("---")

# --- 5. LEFT CONTROL PANEL ---
st.sidebar.header("🛡️ System Control Panel")
store_username = st.sidebar.text_input("Target Store Username", value="asepskin_ph")
LOW_STOCK_THRESHOLD = st.sidebar.slider("Low Stock Level Warning Flag", 5, 1000, 25)
run_analysis = st.sidebar.button("Launch Autonomous Store Audit", type="primary", use_container_width=True)

# --- 6. DATA ENGINES ---
def get_mock_data(username):
    products = [
        f"[{username.upper()}] Natural Polygonum Shampoo", f"[{username.upper()}] Body Lotion 20X Intense",
        f"[{username.upper()}] Niacinamide Gluta Milky Soap", f"[{username.upper()}] Brightening Sunscreen",
        f"[{username.upper()}] Premium EDP Perfume 50ML", f"[{username.upper()}] Collagen Anti-Aging Serum",
        f"[{username.upper()}] Vitamin C Whitening Toner", f"[{username.upper()}] Organic Hair Growth Oil",
        f"[{username.upper()}] Aloe Vera Soothing Gel", f"[{username.upper()}] Matte Liquid Lipstick"
    ]
    mock_inventory = {
        "Product Name": products,
        "Price (PHP)": [158.0, 115.0, 59.0, 159.0, 125.0, 299.0, 89.0, 199.0, 75.0, 249.0],
        "Current Stock": [14, 142, 8, 410, 0, 55, 30, 22, 120, 15],
        "Monthly Sold": [340, 510, 1200, 850, 0, 150, 400, 95, 600, 210],
        "Total Historical Sold": [4200, 6100, 15300, 9800, 12, 1200, 3500, 800, 5400, 950],
        "Internal Rating (Stars)": [4.85, 4.90, 4.95, 4.78, 4.50, 4.92, 4.88, 4.75, 4.99, 4.80]
    }
    return pd.DataFrame(mock_inventory), f"{username.title()} (System Backup Mode)"

# --- 7. RUNTIME LOGIC ---
if run_analysis:
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    
    if not api_key:
        st.error("🔒 Platform Configuration: API Key missing.")
    else:
        with st.spinner("📡 Connecting to storefront..."):
            df, result_meta = get_mock_data(store_username.strip()) # Using mock for stable demo
            
        st.success(f"📊 Live Stream Connected: **{result_meta}**")
        
        # PRO LOOK: Formatting columns
        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={
                "Price (PHP)": st.column_config.NumberColumn("Price (PHP)", format="₱%.2f"),
                "Internal Rating (Stars)": st.column_config.NumberColumn("Rating", format="⭐ %.2f")
            }
        )
        
        top_product = df.sort_values(by="Monthly Sold", ascending=False).iloc[0]
        st.markdown(f"### 🧠 Automated Sales Assets for: *{top_product['Product Name']}*")
        
        prompt = f"Analyze {top_product['Product Name']} (₱{top_product['Price (PHP)']}). Provide output with headers [LIVE_SELLING] (script with 'budol') and [SOCIAL_CAPTION] (Instagram style with emojis)."
        
        try:
            client = genai.Client(api_key=api_key)
            # Use a verified model name from your own testing if 'gemini-3.5-flash' fails
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            
            full_text = response.text
            live_script = full_text.split("[LIVE_SELLING]")[1].split("[SOCIAL_CAPTION]")[0]
            social_cap = full_text.split("[SOCIAL_CAPTION]")[1]
            
            tab1, tab2 = st.tabs(["🎙️ Live Selling Script", "📱 Social Media Caption"])
            with tab1: st.markdown(live_script)
            with tab2: st.markdown(social_cap)
            
        except Exception as e:
            st.error(f"AI Generation Error: Please ensure you are using a valid model (e.g., gemini-2.0-flash). Details: {e}")
