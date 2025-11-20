import streamlit as st
import gspread
import pandas as pd
import json
from datetime import datetime

# --- CONFIGURATION ---
SHEET_NAME = 'EMG Payments Kitchener'
CREDENTIALS_FILE = 'credentials.json'

# --- CONNECT TO GOOGLE ---
@st.cache_resource
def get_connection():
    try:
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
    worksheet = sh.worksheet("Payments")
    
    # Safe loading method
    data = worksheet.get_all_values()
    headers = data[0]
    rows = data[1:]
    
    # Clean up headers (strip spaces)
    cleaned_headers = [h.strip() for h in headers]
    
    df = pd.DataFrame(rows, columns=cleaned_headers)
    return df

# --- DASHBOARD ---
def main():
    st.set_page_config(page_title="Kitchener Finance", layout="wide")
    
    if st.sidebar.button("🔄 FORCE REFRESH"):
        st.cache_data.clear()
        st.rerun()

    st.title("💰 Kitchener Payments")

    try:
        # Get data directly as DataFrame
        df = get_data()
    except Exception as e:
        st.error(f"Error reading sheet: {e}")
        st.stop()

    if not df.empty:
        # 1. CLEAN DATA
        # Drop empty rows if "Date" is missing
        df = df[df['Date'].astype(str).str.strip() != ""]

        # Convert Date
        df['Date Object'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date Object'])
        
        # Convert Amount
        df['Amount'] = pd.to_numeric(df['Amount'].astype(str).str.replace('$','').str.replace(',',''), errors='coerce')

        # 2. MONTH FILTER
        df['Month_Year'] = df['Date Object'].dt.strftime('%B %Y')
        available_months = sorted(df['Month_Year'].unique(), key=lambda x: datetime.strptime(x, '%B %Y'), reverse=True)
        
        if available_months:
            current_month_str = datetime.now().strftime('%B %Y')
            default_index = available_months.index(current_month_str) if current_month_str in available_months else 0
            
            selected_month = st.sidebar.selectbox("Choose Month", available_months, index=default_index)
            monthly_df = df[df['Month_Year'] == selected_month]

            # 3. METRICS
            total_income = monthly_df['Amount'].sum()
            tripic_total = monthly_df[monthly_df['Doctor'].astype(str).str.contains("Tripic", case=False)]['Amount'].sum()
            cartagena_total = monthly_df[monthly_df['Doctor'].astype(str).str.contains("Cartagena", case=False)]['Amount'].sum()

            st.markdown(f"### 📅 Income for {selected_month}")
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Total Received", f"${total_income:,.2f}")
            m2.metric("👨‍⚕️ Dr. Tripic", f"${tripic_total:,.2f}")
            m3.metric("👩‍⚕️ Dr. Cartagena", f"${cartagena_total:,.2f}")

            st.divider()
            
            # 4. TABLE
            st.subheader("Payment Log")
            display_cols = ["Date", "Sender", "Amount", "Doctor"]
            # Only show cols that exist
            cols_to_show = [c for c in display_cols if c in monthly_df.columns]
            
            st.dataframe(
                monthly_df.sort_values(by="Date Object", ascending=False)[cols_to_show], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("No valid dates found in the sheet.")
    else:
        st.info("Sheet is empty.")

if __name__ == "__main__":
    main()
