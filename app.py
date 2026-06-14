import streamlit as st
import pandas as pd
import os
from google import genai

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="AI E-Commerce Co-Pilot", layout="wide", page_icon="🛍️")

# --- 2. SESSION STATE (The Trial Gate) ---
if "trial_active" not in st.session_state:
    st.session_state.trial_active = False

if not st.session_state.trial_active:
    st.title("Welcome to Shopee AI Copilot")
    st.info("Experience the future of inventory management.")
    if st.button("Start 14-Day Free Trial"):
        st.session_state.trial_active = True
        st.rerun()
    st.stop()

# --- 3. THE APP ZONE ---
st.warning("⚠️ Sandbox Mode: Using sample inventory data.")
st.title("🚀 Shopee AI E-Commerce Co-Pilot")
st.markdown("Automate inventory velocity checking and instantly generate sales content.")
st.markdown("---")

# --- 4. CONTROL PANEL ---
st.sidebar.header("🛡️ System Control Panel")
store_username = st.sidebar.text_input("Target Store Username", value="asepskin_ph")
run_analysis = st.sidebar.button("Launch Autonomous Store Audit", type="primary", use_container_width=True)

# --- 5. DATA ENGINE (Expanded to 10 items) ---
def get_mock_data(username):
    products = [f"[{username.upper()}] {item}" for item in [
        "Natural Polygonum Shampoo", "Body Lotion 20X", "Niacinamide Soap", 
        "Brightening Sunscreen", "Premium EDP Perfume", "Collagen Serum", 
        "Vitamin C Toner", "Hair Growth Oil", "Aloe Vera Gel", "Matte Lipstick"
    ]]
    return pd.DataFrame({
        "Product Name": products,
        "Price (PHP)": [158.0, 115.0, 59.0, 159.0, 125.0, 299.0, 89.0, 199.0, 75.0, 249.0],
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
    
    top_prod = df.sort_values(by="Monthly Sold", ascending=False).iloc[0]
    st.markdown(f"### 🧠 Automated Assets for: *{top_prod['Product Name']}*")
    
    # --- GRACEFUL AI CALL ---
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    ai_success = False
    
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Analyze {top_prod['Product Name']}. Output as: [LIVE_SELLING] (script) and [SOCIAL_CAPTION] (Instagram caption)."
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            
            full_text = response.text
            tab1, tab2 = st.tabs(["🎙️ Live Selling", "📱 Social Caption"])
            with tab1: st.markdown(full_text.split("[LIVE_SELLING]")[1].split("[SOCIAL_CAPTION]")[0])
            with tab2: st.markdown(full_text.split("[SOCIAL_CAPTION]")[1])
            ai_success = True
        except Exception as e:
            st.warning("AI Service limited (Quota reached). Using fallback template.")
    
    if not ai_success:
        st.info("💡 **Fallback Template:**")
        st.markdown(f"**Check out {top_prod['Product Name']}!** Limited stocks. Mine na before it's gone! #Budol #ShopeePH")
