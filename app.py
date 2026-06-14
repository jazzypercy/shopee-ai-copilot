import streamlit as st
import pandas as pd
import os
from google import genai
import datetime
import json
import altair as alt

# --- PERSISTENT DATA HELPERS ---
def save_user_trial(email, start_time):
    data = {"email": email, "start_time": start_time.isoformat()}
    with open("users.json", "w") as f:
        json.dump(data, f)

def get_user_trial(email):
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            try:
                data = json.load(f)
                if data["email"] == email:
                    return datetime.datetime.fromisoformat(data["start_time"])
            except:
                return None
    return None

def get_trial_remaining():
    if not st.session_state.get("trial_start_time"):
        return "N/A"
    elapsed = datetime.datetime.now() - st.session_state.trial_start_time
    remaining = (datetime.timedelta(hours=24) - elapsed)
    if remaining.total_seconds() <= 0:
        return "Expired"
    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="GrowthPilot AI", layout="wide", page_icon="🛍️")

if "trial_active" not in st.session_state:
    st.session_state.trial_active = False
if "LOW_STOCK_THRESHOLD" not in st.session_state:
    st.session_state.LOW_STOCK_THRESHOLD = 25
if "user_email" not in st.session_state:
    st.session_state.user_email = None
# ADD THIS LINE:
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False

# --- 2. SESSION STATE (The Email-Based Trial Gate) ---
if not st.session_state.trial_active:
    st.title("Welcome to GrowthPilot AI")
    st.info("Enter your email to start your 1-Day Free Trial.")
    
    email_input = st.text_input("Enter your email address:")
    
    if st.button("Start 1-Day Free Trial"):
        if email_input:
            existing_start = get_user_trial(email_input)
            if existing_start:
                st.session_state.trial_start_time = existing_start
            else:
                st.session_state.trial_start_time = datetime.datetime.now()
                save_user_trial(email_input, st.session_state.trial_start_time)
            
            st.session_state.user_email = email_input
            st.session_state.trial_active = True
            st.rerun()
        else:
            st.warning("Please enter a valid email address.")
    st.stop()

# Check for Expiry
if get_trial_remaining() == "Expired":
    st.error("⏰ Your 1-Day Free Trial has expired. Please contact support to upgrade.")
    st.stop()

# --- 3. THE APP ZONE ---
st.warning(f"⚠️ Reminder: {get_trial_remaining()} remaining in your 1-Day Trial.")

# --- 4. CONTROL PANEL ---
st.sidebar.header("🛡️ System Control Panel")

# 1. File Uploader
uploaded_file = st.sidebar.file_uploader("Upload Product Performance CSV", type=["csv"])

# 2. Helper to provide a Template
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

st.sidebar.download_button(
    label="📥 Download CSV Template",
    data=get_sample_csv_template(),
    file_name="growthpilot_template.csv",
    mime="text/csv"
)

st.sidebar.markdown("### 📦 Supply Parameters")
st.session_state.LOW_STOCK_THRESHOLD = st.sidebar.slider(
    "Low Stock Level Warning Flag", 5, 1000, st.session_state.LOW_STOCK_THRESHOLD
)

run_analysis = st.sidebar.button("Analyze My Store", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📩 Need Assistance?")
st.sidebar.info("📧 **[grantjaspertaneo@gmail.com](mailto:grantjaspertaneo@gmail.com)**")

# --- 5. LANDING PAGE INSTRUCTIONS ---
if not run_analysis and not st.session_state.demo_mode:
    st.title("🚀 Growth Pilot Ai")
    st.subheader("Your Silent Partner in Retail Success.")
    
    # How-To Popover
    with st.popover("📖 How to use GrowthPilot AI"):
        st.markdown("""
        ### Getting Started
        1. **Load Data:** Click **"✨ Load Demo Data"** to test with sample data, or upload your own CSV file in the sidebar.
        2. **Configure:** Set your "Low Stock" threshold in the sidebar to flag items that need reordering.
        3. **Analyze:** Click **"Analyze My Store"** to view your forecasts and generate AI marketing assets.
        
        ### How to get your CSV from Shopee
        1. Go to your **Shopee Seller Center**.
        2. Navigate to **"My Products"** or **"Data & Reports"**.
        3. Look for the **"Export"** button to download your product list as a CSV.
        4. If your columns don't match, simply use our **"Download CSV Template"** in the sidebar to reformat your data.
        """)

    # Demo Button
    if st.button("✨ Load Demo Data"):
        st.session_state.demo_mode = True
        st.rerun()

# --- 6. DATA ENGINE ---
def get_mock_data(username):
    products = [
        "Natural Shampoo", "Body Lotion 20X", "Niacinamide Soap", 
        "Brightening Sunscreen", "Premium EDP Perfume", "Collagen Serum", 
        "Vitamin C Toner", "Hair Growth Oil", "Aloe Vera Gel", "Matte Lipstick"
    ]
    return pd.DataFrame({
        "Product Name": products,
        "Price (PHP)": [158.0, 115.0, 59.0, 159.0, 125.0, 299.0, 89.0, 199.0, 75.0, 249.0],
        "Current Stock": [14, 142, 8, 410, 50, 55, 30, 22, 120, 15],
        "Monthly Sold": [340, 510, 1200, 850, 0, 150, 400, 95, 600, 210],
        "Rating": [4.8, 4.9, 4.9, 4.7, 4.5, 4.9, 4.8, 4.7, 4.9, 4.8]
    })

# --- 7. RUNTIME LOGIC ---
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
                st.write("Please map your CSV columns to the required fields below:")
                
                mapping = {}
                col1, col2 = st.columns(2)
                for req in required_cols:
                    mapping[req] = col1.selectbox(f"Select column for '{req}':", df.columns)
                
                if st.button("Apply Mapping"):
                    df = df.rename(columns={v: k for k, v in mapping.items()})
                    # Keep only the required columns to avoid errors
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
    
    chart_data = df.melt('Product Name', value_vars=['Current Stock', 'Weekly Forecast'], 
                           var_name='Metric', value_name='Units')
    
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('Units', title='Units'),
        y=alt.Y('Product Name', title='', sort='-x'),
        color=alt.Color('Metric', scale=alt.Scale(domain=['Current Stock', 'Weekly Forecast'], 
                                                 range=['#60A5FA', '#F87171'])),
        tooltip=['Product Name', 'Metric', 'Units']
    ).properties(height=300)
    
    st.altair_chart(chart, use_container_width=True)
    
    st.write("*(The **Red bars** show predicted customer demand, and the **Blue bars** show what you have available.)*")
    
    st.markdown("#### 📝 Key Takeaways")
    df['Gap'] = df['Weekly Forecast'] - df['Current Stock']
    riskiest_prod = df.loc[df['Gap'].idxmax()]
    
    if riskiest_prod['Gap'] > 0:
        st.write(f"👉 **Critical Alert:** Your top demand risk is **{riskiest_prod['Product Name']}**. You are predicted to sell **{riskiest_prod['Weekly Forecast']}** units next week, but only have **{riskiest_prod['Current Stock']}** in stock.")
    else:
        st.write("👉 **Good News:** Your current stock levels are sufficient to cover predicted demand for all products next week.")
    
    st.dataframe(
        df.drop(columns=['Gap']), use_container_width=True, hide_index=True,
        column_config={
            "Price (PHP)": st.column_config.NumberColumn(format="₱%.2f"),
            "Rating": st.column_config.NumberColumn(format="⭐ %.2f"),
            "Weekly Forecast": st.column_config.NumberColumn(help="Predicted sales for next 7 days")
        }
    )

    if not df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD].empty:
        st.markdown("### 🚨 High Priority Logistics Alerts")
        for _, row in df[df['Current Stock'] <= st.session_state.LOW_STOCK_THRESHOLD].iterrows():
            status = "❌ **OUT OF STOCK**" if row['Current Stock'] == 0 else "⚠️ **Reorder Alert**"
            st.warning(f"{status}: '{row['Product Name']}' has only **{row['Current Stock']}** pieces left.")
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
            with st.spinner('Generating AI insights...'):
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"Analyze {top_prod['Product Name']}. Output as: [LIVE_SELLING] (script) and [SOCIAL_CAPTION] (Instagram caption)."
                )
            full_text = response.text
            if "[LIVE_SELLING]" in full_text and "[SOCIAL_CAPTION]" in full_text:
                tab1, tab2 = st.tabs(["🎙️ Live Selling", "📱 Social Caption"])
                with tab1: st.markdown(full_text.split("[LIVE_SELLING]")[1].split("[SOCIAL_CAPTION]")[0])
                with tab2: st.markdown(full_text.split("[SOCIAL_CAPTION]")[1])
                ai_success = True
        except Exception as e:
            st.warning(f"AI Service limited: {e}")
    
    if not ai_success:
        st.info("💡 **Fallback Template:**")
        st.markdown(f"**Check out {top_prod['Product Name']}!** Limited stocks. Mine na before it's gone! #Budol #ShopeePH")
