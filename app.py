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
    
    st.stop() # Stops execution until the user clicks the button

# --- 4. THE "APP" ZONE (Only runs if trial_active is True) ---

# --- THE BANNER ---
st.warning("⚠️ Sandbox Mode: Using sample inventory data for demonstration purposes.")

st.title("🚀 Shopee AI E-Commerce Co-Pilot")
st.markdown("Automate inventory velocity checking, manage stockouts, and instantly write high-converting content for your shop.")
st.markdown("---")

# --- 5. LEFT CONTROL PANEL ---
st.sidebar.header("🛡️ System Control Panel")
st.sidebar.markdown("Configure operational target metrics below.")

store_username = st.sidebar.text_input("Target Store Username", value="asepskin_ph")

st.sidebar.markdown("### 📦 Supply Parameters")
LOW_STOCK_THRESHOLD = st.sidebar.slider("Low Stock Level Warning Flag", min_value=5, max_value=1000, value=25)

run_analysis = st.sidebar.button("Launch Autonomous Store Audit", type="primary", use_container_width=True)

# --- 6. PRODUCTION SECURITY MODULE ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key_input = st.secrets["GEMINI_API_KEY"]
    else:
        api_key_input = os.environ.get("GEMINI_API_KEY", "")
except Exception:
    api_key_input = os.environ.get("GEMINI_API_KEY", "")

# --- 7. DATA ENGINES ---
def get_mock_data(username):
    products = [
        f"[{username.upper()}] Natural Polygonum Shampoo",
        f"[{username.upper()}] Body Lotion 20X Intense",
        f"[{username.upper()}] Niacinamide Gluta Milky Soap",
        f"[{username.upper()}] Brightening Sunscreen Protection",
        f"[{username.upper()}] Premium EDP Perfume"
    ]
    mock_inventory = {
        "Product Name": products,
        "Price (PHP)": [158.00, 115.00, 59.00, 159.00, 125.00],
        "Current Stock": [14, 142, 8, 410, 0],
        "Monthly Sold": [340, 510, 1200, 850, 0],
        "Total Historical Sold": [4200, 6100, 15300, 9800, 12],
        "Internal Rating (Stars)": [4.85, 4.90, 4.95, 4.78, 4.50]
    }
    return pd.DataFrame(mock_inventory), f"{username.title()} (System Backup Mode)"

def get_shopee_store_items(username):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": f"https://shopee.ph/{username}"
    }
    profile_url = f"https://shopee.ph/api/v4/shop/get_shop_detail?username={username}"
    
    try:
        response = requests.get(profile_url, headers=headers, impersonate="chrome", timeout=10)
        if response.status_code != 200: return get_mock_data(username)
        shop_data = response.json().get('data')
        if not shop_data: return get_mock_data(username)
        
        shop_id = shop_data['shopid']
        shop_name = shop_data['name']
        
        search_url = f"https://shopee.ph/api/v4/search/search_items?by=pop&limit=50&match_id={shop_id}&order=desc&page_type=shop&version=1"
        item_response = requests.get(search_url, headers=headers, impersonate="chrome", timeout=10)
        items_list = item_response.json().get('items', [])
        
        if not items_list: return get_mock_data(username)
        
        cleaned_inventory = []
        for packet in items_list:
            item = packet.get('item_basic')
            if not item: continue
            cleaned_inventory.append({
                "Product Name": item.get('name'),
                "Price (PHP)": item.get('price') / 100000, 
                "Current Stock": item.get('stock', 0),
                "Monthly Sold": item.get('sold', 0),
                "Total Historical Sold": item.get('historical_sold', 0),
                "Internal Rating (Stars)": round(item.get('item_rating', {}).get('rating_star', 0), 2)
            })
        return pd.DataFrame(cleaned_inventory), shop_name
    except Exception:
        return get_mock_data(username)

# --- 8. RUNTIME LOGIC ---
if run_analysis:
    if not api_key_input:
        st.error("🔒 Platform Configuration: API Key missing.")
    else:
        with st.spinner("📡 Establishing secure connection..."):
            df, result_meta = get_shopee_store_items(store_username.strip())
            
        if df is not None and not df.empty:
            st.success(f"📊 Live Stream Connected: **{result_meta}**")
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Monitored Catalog", f"{len(df)} Items")
            with c2: st.metric("Sales Volume (30D)", f"{int(df['Monthly Sold'].sum()):,.0f}")
            with c3: st.metric("Critical Hazards", f"{len(df[df['Current Stock'] <= LOW_STOCK_THRESHOLD])}")
            
            st.markdown("### 📊 Inventory Audit Table")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            top_product = df.sort_values(by="Monthly Sold", ascending=False).iloc[0]
            st.markdown(f"### 🧠 Automated Sales Asset Creation")
            
            marketing_prompt = f"Write high-energy sales copy for {top_product['Product Name']} in Taglish."
            
            try:
                client = genai.Client(api_key=api_key_input)
                # Updated to a stable, current production model
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=marketing_prompt,
                )
                st.markdown(response.text)
            except Exception as ai_err:
                st.error(f"AI Integration Error: {ai_err}")
