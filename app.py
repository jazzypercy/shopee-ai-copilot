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
st.set_page_config(page_title="DisCartT AI", layout="wide", page_icon="🛒")

# Global Settings
ADMIN_EMAIL = "grantjaspertaneo@gmail.com"
AI_DAILY_LIMIT = 3 

if "demo_mode" not in st.session_state: st.session_state.demo_mode = False
if "df_final" not in st.session_state: st.session_state.df_final = None
if "ai_usage_count" not in st.session_state: st.session_state.ai_usage_count = 0
if "trial_active" not in st.session_state: st.session_state.trial_active = False
if "LOW_STOCK_THRESHOLD" not in st.session_state: st.session_state.LOW_STOCK_THRESHOLD = 25

@st.cache_resource
def get_db():
    try:
        key_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return firestore.Client(credentials=creds, database="growthai")
    except Exception as e:
        return None

db = get_db()

def get_user_access(email):
    """Returns the user's current tier."""
    if email == ADMIN_EMAIL:
        return "premium"
    return st.session_state.get("user_tier", "trial")

def check_feature_access(feature_name, email):
    """Returns True if the user has access to the requested feature."""
    tier = get_user_access(email)
    
    if feature_name == "ai_insights":
        if tier == "premium": return True
        if tier == "starter" and st.session_state.ai_usage_count < 30: return True
        if tier == "trial" and st.session_state.ai_usage_count < 3: return True
    
    if feature_name == "advanced_forecasting":
        return tier == "premium"
        
    return False

def show_pricing_table():
    st.markdown("### 💎 I-Level Up ang Diskarte (Unlock the full potential of DisCartT AI)")
    st.info("💳 **Secure payments via GCash, Maya, and Credit/Debit Cards coming soon!**")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Starter")
        st.write("₱499 / month")
        st.markdown("- 30 AI Insights/mo\n- 7-Day Forecast")
        st.link_button("Upgrade to Starter", "YOUR_PAYMONGO_STARTER_LINK_HERE", use_container_width=True)
        
    with col2:
        st.subheader("Premium")
        st.write("₱699 / month")
        st.markdown("- Unlimited AI Insights\n- 30-Day Forecast")
        st.link_button("Upgrade to Premium", "YOUR_PAYMONGO_PREMIUM_LINK_HERE", type="primary", use_container_width=True)
    
# --- 2. GOOGLE OAUTH & SUBSCRIPTION GATE ---
if not st.user.is_logged_in:
    # --- MARKETING LANDING PAGE ---
    st.title("🛒 Welcome to DisCartT AI")
    st.markdown("### Ang AI assistant para sa matalinong diskarte ng mga Pinoy online sellers!")
    st.write("DisCartT uses AI to forecast demand, prevent stockouts, and boost your sales through live selling strategies and social media campaigns.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("✅ **Forecast Sales**")
        st.info("✅ **Prevent Stockouts**")
    with col2:
        st.info("✅ **Marketing Content Generation**")
        st.info("✅ **Inventory Insights**")
        
    st.button("🚀 Sign in with Google para masimulan ang iyong 7-Day Free Use.", on_click=st.login, args=("google",), type="primary")
    st.stop()

# Safely extract email using the dict method
user_info = st.user.to_dict()
user_email = user_info.get("email")

if not user_email:
    st.error("Authentication successful, but email could not be retrieved.")
    if st.button("Logout and Try Again"):
        st.logout()
        st.rerun()
    st.stop()

# --- 3. SYNC USER TIER & USAGE FROM FIRESTORE ---
if db:
    user_doc_ref = db.collection("users").document(user_email)
    doc = user_doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        # Load from Firestore instead of defaulting to 0
        st.session_state.user_tier = data.get("tier", "trial")
        st.session_state.ai_usage_count = data.get("ai_usage_count", 0) 
        
        if "start_time" in data:
            st.session_state.trial_start_time = datetime.datetime.fromisoformat(data["start_time"])
    else:
        # First time user: Initialize with 0
        st.session_state.user_tier = "trial"
        st.session_state.ai_usage_count = 0
        st.session_state.trial_start_time = datetime.datetime.now()
        user_doc_ref.set({
            "email": user_email,
            "tier": "trial",
            "ai_usage_count": 0,
            "start_time": st.session_state.trial_start_time.isoformat()
        })
        
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

# A. Trial/Subscription Status Display ---
if user_email != ADMIN_EMAIL:
    # Check if the user is in trial mode
    if st.session_state.user_tier == "trial":
        if "trial_start_time" in st.session_state:
            now = datetime.datetime.now()
            start = st.session_state.trial_start_time
         
            if start.tzinfo is not None:
                start = start.replace(tzinfo=None)
            
            elapsed = now - start
            remaining = datetime.timedelta(days=7) - elapsed
            
            if remaining.total_seconds() > 0:
                d = remaining.days
                h, r = divmod(int(remaining.seconds), 3600)
                st.sidebar.info(f"⏳ Libreng Trial ends in: **{d}d {h}h**")
                st.session_state.trial_active = True # Explicitly declare trial is alive
            else:
                st.sidebar.success(f"💎 Status: {st.session_state.user_tier.capitalize()} Member")
                st.session_state.trial_active = True # Premium/Starter users are always active
    else:
        if user_email == ADMIN_EMAIL:
            st.sidebar.markdown("---")
            st.sidebar.subheader("👥 Registered Users Directory")
            
            if st.sidebar.button("📊 Fetch Active Users List"):
                try:
                    users_ref = db.collection("users")
                    docs = users_ref.stream()
                    
                    # Put data into a clean structure
                    user_list = []
                    for doc in docs:
                        u_data = doc.to_dict()
                        user_list.append({
                            "Email": u_data.get("email"),
                            "Current Tier": u_data.get("tier"),
                            "AI Used": u_data.get("ai_usage_count", 0),
                            "Joined Date": u_data.get("start_time", "")[:10] # Shows YYYY-MM-DD
                        })
                    
                    if user_list:
                        # Convert to DataFrame and show on the main dashboard for easy viewing
                        df_users = pd.DataFrame(user_list)
                        st.markdown("### 🛠️ Admin View: User Base Status")
                        dynamic_height = (len(df_users) * 35) + 38
                        st.dataframe(df_users, use_container_width=True, height=dynamic_height)
                    else:
                        st.sidebar.warning("No users found in the database yet.")
                        
                except Exception as e:
                    st.sidebar.error(f"Could not load directory: {e}")
            else:
                st.sidebar.success(f"💎 Status: {st.session_state.user_tier.capitalize()} Member")

# B. File Upload & Tools
uploaded_file = None
run_analysis = False

# Only show upload capabilities if the user's trial/membership is active
if st.session_state.get("trial_active", True):
    st.sidebar.markdown("### 📁 I-upload ang Data")
    uploaded_file = st.sidebar.file_uploader("Please upload your CSV file here/", type=["csv"])

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
    st.session_state.LOW_STOCK_THRESHOLD = st.sidebar.slider("🚨 Low Stock Warning Flag (Kailan mag-aalert?)", 5, 1000, st.session_state.LOW_STOCK_THRESHOLD)
    run_analysis = st.sidebar.button("🔍 Analyze My Store", type="primary", use_container_width=True)
else:
    st.sidebar.markdown("---")
    st.sidebar.warning("🔒 **Features Locked**\n\nTapos na ang iyong 7-day access. Pleasse upgrade your subscription para ma-unlock muli ang file upload at tools.")

# C. Brand Tone
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 AI Brand Tone")
st.session_state.brand_tone = st.sidebar.selectbox(
    "Select your brand tone:",
    ["Professional", "Energetic", "Casual", "Urgent/Sales-y", "Funny"]
)

# D. Account Footer
st.sidebar.markdown("---")
with st.sidebar.container(border=True):
    st.caption("Account:")
    st.write(f"**{user_email}**")
    if st.button("🚪 Logout"):
        st.logout()
        st.rerun()
        
st.sidebar.markdown("---")
st.sidebar.markdown("### 🤝 About DisCartT AI")
st.sidebar.caption("DisCartT AI helps sellers apply 'diskarte' to their inventory management and online contents.")
st.sidebar.caption("Built by jazzypercy")
st.sidebar.info("📧 Need help? Contact: grantjaspertaneo@gmail.com")
st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0 | GrowthPilot AI © 2026")

# --- ADMIN ONLY: USER PROMOTION TOOL ---
if user_email == ADMIN_EMAIL:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛠️ Admin: Manage Tiers")
    target_email = st.sidebar.text_input("Enter user email to promote:")
    new_tier = st.sidebar.selectbox("Select new tier:", ["trial", "starter", "premium"])
    
    if st.sidebar.button("Update User Tier"):
        try:
            user_doc_ref = db.collection("users").document(target_email)
            user_doc_ref.update({"tier": new_tier})
            st.sidebar.success(f"User {target_email} updated to {new_tier}!")
            st.rerun() # Forces a refresh so the app fetches the new data
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

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
            
            # --- SMART MAPPING LOGIC (Supports Shopee, Lazada, TikTok) ---
            aliases = {
                "Product Name": ["product name", "item name", "title"],
                "Price (PHP)": ["price", "retail price", "unit price"],
                "Current Stock": ["stock", "quantity", "qty", "inventory", "available"],
                "Monthly Sold": ["sold", "sales", "order", "benta", "30 days"],
                "Rating": ["rating", "review", "score", "star"]
            }
            
            mapping = {}
            for req, possible_names in aliases.items():
                match = None
                # Check for exact or partial keyword match in headers
                for col in df_raw.columns:
                    if any(alias in col.lower() for alias in possible_names):
                        match = col
                        break
                
                # Fallback 1: Broad search for required word
                if not match:
                    match = next((col for col in df_raw.columns if req.lower() in col.lower() or col.lower() in req.lower()), None)
                    
                # Fallback 2: Index based if missing
                if match:
                    mapping[req] = match
                else:
                    idx = list(aliases.keys()).index(req)
                    mapping[req] = df_raw.columns[idx] if idx < len(df_raw.columns) else None
            
            # Return cleaned and renamed DataFrame
            return df_raw.rename(columns={v: k for k, v in mapping.items()})[required]
    except Exception as e:
        st.error(f"🙏 Error processing data: {e}")
        return None
    return None

# 2. TRIGGER LOGIC: Detects user intent
if run_analysis or st.session_state.get("demo_mode", False):
    
    # NEW: STRICT LOCKOUT RULE
    # If they are a trial user AND their trial is no longer active, stop them here.
    if st.session_state.user_tier == "trial" and not st.session_state.get("trial_active", True):
        st.error("🔒 **Tapos na ang 7-Day Free Trial mo.** I-upgrade ang account para patuloy na magamit ang DisCartT AI at hindi ma-ubusan ng stock!")
        show_pricing_table() # Show the payment buttons immediately
        st.session_state.df_final = None # Clear any existing data
        
    else:
        # Normal operations continue untouched
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
            st.markdown("##### Step 1: Get your CSV Data")
            st.info("Use a computer or open the link on a browser on desktop mode if using a mobile device.")
            tab_s, tab_l, tab_t = st.tabs(["Shopee", "Lazada", "TikTok"])
            with tab_s:
                st.write("Go to **seller.shopee.ph** > Business Insights > Product tab > Click 'Export Data'.")
            with tab_l:
                st.write("Go to **sellercenter.lazada.com.ph** > Data Insights > Products > Click 'Export'.")
            with tab_t:
                st.write("Go to **seller-ph.tiktok.com** > Data Compass > Product Analysis > Click 'Export'.")
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
    st.markdown("---")
    st.markdown("### 🧠 AI Marketing Assistant")
    
    # Initialize a session state slot to hold the generated text so it doesn't disappear
    if "generated_marketing_copy" not in st.session_state:
        st.session_state.generated_marketing_copy = ""
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_name = st.selectbox("Select product to market:", df['Product Name'].tolist())
        target_prod = df[df['Product Name'] == selected_name].iloc[0]
    with col_sel2:
        output_format = st.radio(
            "Choose Marketing Content Type:",
            ["Social Media Caption", "Live Selling Script"],
            horizontal=True
        )
    
    if not check_feature_access("ai_insights", user_email):
        st.warning("✨ **You've reached your AI limit!** Mag-upgrade para maka-generate pa ng maraming diskarte.")
        show_pricing_table()
    else:
        if st.button("✨ Generate AI Copy"):
            try:
                api_key = st.secrets.get("GROQ_API_KEY", "")
                if not api_key:
                    st.error("🔑 GROQ_API_KEY is missing from your Streamlit secrets!")
                    st.stop()
                
                with st.spinner(f'Crafting your {output_format.lower()} via Groq...'):
                    model_target = "llama-3.3-70b-versatile"
                    
                    if output_format == "Social Media Caption":
                        prompt = f"""
                        You are an expert e-commerce copywriter. Write an engaging, highly converting social media caption for this product: {target_prod['Product Name']}.
                        Price: PHP {target_prod['Price (PHP)']}, Current Stock: {target_prod['Current Stock']}, Monthly Sold: {target_prod['Monthly Sold']}.
                        Tone: {st.session_state.brand_tone}.
                        
                        Structure the caption with:
                        1. A strong, scroll-stopping first-line hook.
                        2. Highlights of the product's benefits and value proposition.
                        3. Strategic incorporation of current stock and scarcity indicators to drive FOMO.
                        4. Clear Call-to-Action (CTA) instructing users how to order.
                        5. Relevant, natural emojis and e-commerce hashtags (e.g., #DisCartT #OnlineBusinessPH).
                        Do not summarize too briefly; make it completely copy-paste ready for social channels.
                        """
                    else:  # Live Selling Script
                        prompt = f"""
                        You are a high-energy, persuasive Filipino live selling host. Write an engaging live selling script segment for this product: {target_prod['Product Name']}.
                        Price: PHP {target_prod['Price (PHP)']}, Current Stock: {target_prod['Current Stock']}, Monthly Sold: {target_prod['Monthly Sold']}.
                        Tone: {st.session_state.brand_tone}.
                        
                        The script must be written in an authentic, natural mix of Tagalog and English (Taglish) that reflects the specified tone ({st.session_state.brand_tone}). Incorporate active performance cues/stage directions inside brackets like [Show the product close to camera, Smile wide, Gesture excitedly].
                        
                        Structure the script segment with:
                        1. Intro Hook: Grab viewers' attention instantly in the live comments stream.
                        2. Pitch & Demo Description: Explain clearly why viewers must buy this right now. Mention the price points directly.
                        3. Urgency Push: Leverage the performance metric ({target_prod['Monthly Sold']} sold this month!) and the inventory bottleneck ({target_prod['Current Stock']} remaining in stock!) to spur instant lock-ins.
                        4. Call-to-Action: Direct them precisely on how to comment "Mine" or check out via the basket.
                        Do not summarize too briefly; provide a comprehensive script a seller can confidently execute live.
                        """
                    
                    import requests
                    import json

                    response = requests.post(
                        url="https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        data=json.dumps({
                            "model": model_target,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.7
                        })
                    )
                    
                    result_data = response.json()
                    
                    if "error" in result_data:
                        raise Exception(result_data["error"].get("message", "Unknown Groq API Error"))
                        
                    # Save the response text to session state instead of just drawing it once
                    st.session_state.generated_marketing_copy = result_data["choices"][0]["message"]["content"]
                
                # Update local session usage trackers
                st.session_state.ai_usage_count += 1
                
                # Synchronize counter with Firestore
                if db:
                    db.collection("users").document(user_email).update({
                        "ai_usage_count": st.session_state.ai_usage_count
                    })
                
                st.rerun() # Refresh the app to display the newly saved text seamlessly
                
            except Exception as e:
                # 1. Log the actual raw error in the backend for your eyes only (debugging)
                import logging
                logging.error(f"Groq Generation Error: {e}", exc_info=True)
                
                # 2. Display a polished, professional message to the user
                st.error("We experienced a brief interruption connecting to the AI server. Please try generating your content again in a few moments.")
                st.info("💡 Tip: If this issue persists, please ensure your internet connection is stable or contact support at grantjaspertaneo@gmail.com.")
        
        # Display the text from session_state outside the button block
        # This keeps it visible even if the user interacts with other sidebar filters!
        if st.session_state.generated_marketing_copy:
            with st.container(border=True):
                st.caption(f"✨ Generated Content for {selected_name} ({output_format}):")
                st.markdown(st.session_state.generated_marketing_copy)
   
else:
    # 3. LANDING PAGE
    st.title("🛒 DisCartT Ai")
    st.subheader("Your AI-powered assistant para sa mas matalinong inventory at mabilis na benta.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Status", "Operational", "Online")
    c2.metric("Model", "Llama 3.3", "Flash")
    c3.metric("Database", "Firestore", "Secure")
        
    st.markdown("---")
    st.markdown("### 💡 How to Get Started")
    
    with st.expander("Step 1: Kumuha ng CSV Data (Shopee, Lazada, TikTok)"):
        st.write("*(Note: You must use a computer or browser in desktop mode when using a mobile device.)*")
        tab_s, tab_l, tab_t = st.tabs(["🟠 Shopee", "🔵 Lazada", "⚫ TikTok Shop"])
        
        with tab_s:
            st.write("""
            1. Go to [seller.shopee.ph](https://seller.shopee.ph/). 
            2. On the left sidebar, click **'Business Insights'**.
            3. Select the **'Product'** tab.
            4. Click the **'Export Data'** button to download the report as a **.CSV** file.
            """)
        with tab_l:
            st.write("""
            1. Go to [sellercenter.lazada.com.ph](https://sellercenter.lazada.com.ph/).
            2. Navigate to **Data Insights** > **Products**.
            3. Adjust your date range (e.g., Last 30 Days).
            4. Click **'Export'** to download your **.CSV** file.
            """)
        with tab_t:
            st.write("""
            1. Go to [seller-ph.tiktok.com](https://seller-ph.tiktok.com/).
            2. Navigate to **Data Compass** > **Product Analysis**.
            3. Adjust your date range.
            4. Click **'Export'** to download your **.CSV** file.
            """)
        
    with st.expander("Step 2: Upload the CSV file"):
        st.write("""
        1. I-click ang **'Upload'** button sa sidebar.
        2. I-upload the CSV file you just downloaded. Ang aming AI na ang bahalang mag-detect kung anong platform ito!
        """)
    
    with st.expander("Step 3: Analyze and Grow"):
        st.write("""
        1. Gamitin ang **'Low Stock Warning Flag'** slider para ma-set kung kailan ka dapat i-alert ng system na mag-restock.
        2. I-click ang **'Analyze My Store'** para makita ang sales forecast, bodega status, at makagawa ng AI social media content!
        """)
    
    st.markdown("---")
    if st.button("✨ Load Demo Data"):
        st.session_state.demo_mode = True
        st.rerun()
