import streamlit as st
import gspread
import pandas as pd
import json
from datetime import datetime

# --- CONFIGURATION ---
SHEET_NAME = 'EMG Payments Kitchener'
# We use the same credentials file as before
CREDENTIALS_FILE = 'credentials.json'

# --- CONNECT TO GOOGLE ---
@st.cache_resource
def get_connection():
    try:
        # Check if we are on the Cloud (Secrets) or Local (File)
        if "gcp_json" in st.secrets:
            creds_dict = json.loads(st.secrets["gcp_json"])
            gc = gspread.service_account_from_dict(creds_dict)
        else:
            gc = gspread.service_account(filename=CREDENTIALS_FILE)
        return gc
    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.stop()

def get_data():
    gc = get_connection()
    sh = gc.open(SHEET_NAME)
    # Look at the "Payments" tab
    worksheet = sh.worksheet("Payments")
    return worksheet.get_all_records()

# --- DASHBOARD ---
def main():
    st.set_page_config(page_title="Kitchener Finance", layout="wide")
    
    # Sidebar Refresh
    if st.sidebar.button("🔄 FORCE REFRESH"):
        st.cache_data.clear()
        st.rerun()

    st.title("💰 Kitchener Payments")

    try:
        data = get_data()
        df = pd.DataFrame(data)
    except:
        st.info("No data found yet. Waiting for the robot...")
        st.stop()

    if not df.empty:
        # 1. CLEAN DATA
        # Convert Date column to real dates
        df['Date Object'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date Object'])
        
        # Convert Amount column to numbers (Remove $ and ,)
        df['Amount'] = pd.to_numeric(df['Amount'].astype(str).str.replace('$','').str.replace(',',''), errors='coerce')

        # 2. MONTH FILTER
        df['Month_Year'] = df['Date Object'].dt.strftime('%B %Y')
        available_months = sorted(df['Month_Year'].unique(), key=lambda x: datetime.strptime(x, '%B %Y'), reverse=True)
        
        # Default to current month if available
        current_month_str = datetime.now().strftime('%B %Y')
        default_index = available_months.index(current_month_str) if current_month_str in available_months else 0
        
        selected_month = st.sidebar.selectbox("Choose Month", available_months, index=default_index)
        
        # Filter data for that month
        monthly_df = df[df['Month_Year'] == selected_month]

        # 3. CALCULATE METRICS
        total_income = monthly_df['Amount'].sum()
        
        # Calculate Split
        tripic_total = monthly_df[monthly_df['Doctor'].astype(str).str.contains("Tripic", case=False)]['Amount'].sum()
        cartagena_total = monthly_df[monthly_df['Doctor'].astype(str).str.contains("Cartagena", case=False)]['Amount'].sum()

        # 4. DISPLAY METRICS
        st.markdown(f"### 📅 Income for {selected_month}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Total Received", f"${total_income:,.2f}")
        m2.metric("👨‍⚕️ Dr. Tripic", f"${tripic_total:,.2f}")
        m3.metric("👩‍⚕️ Dr. Cartagena", f"${cartagena_total:,.2f}")

        st.divider()
        
        # 5. DISPLAY TABLE
        st.subheader("Payment Log")
        # Show specific columns
        display_cols = ["Date", "Sender", "Amount", "Doctor"]
        st.dataframe(
            monthly_df.sort_values(by="Date Object", ascending=False)[display_cols], 
            use_container_width=True, 
            hide_index=True
        )
        
    else:
        st.info("Sheet is empty.")

if __name__ == "__main__":
    main()