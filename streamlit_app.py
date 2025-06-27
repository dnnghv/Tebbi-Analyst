#!/usr/bin/env python3
"""
Main Streamlit application file for Tebbi Analytics Dashboard
"""

import streamlit as st
from views.analytics import analytics_page
from views.odoo_leads import odoo_lead_page

# Page config
st.set_page_config(
    page_title="Tebbi Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Hide Streamlit default sidebar titles */
    section[data-testid="stSidebar"] > div:first-child > div:first-child > div:first-child > div:first-child {
        display: none;
    }
    section[data-testid="stSidebar"] > div:first-child > div:first-child > div:first-child > div:nth-child(2) {
        display: none;
    }
    /* Hide the horizontal line after page titles */
    section[data-testid="stSidebar"] > div:first-child > div:first-child > div:first-child > div:nth-child(3) {
        display: none;
    }

    /* Existing styles */
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        border-left: 5px solid #1f77b4;
    }
    .conversation-msg {
        margin: 10px 0;
        padding: 10px;
        border-radius: 8px;
    }
    .user-msg {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .ai-msg {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    .date-filter {
        background-color: #e8f5e8;
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #4caf50;
    }
    .welcome-box {
        background-color: #fff3cd;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        border-left: 4px solid #ffc107;
    }
    .success-box {
        background-color: #d4edda;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main function to run the Streamlit app"""
    page = st.sidebar.radio("Chọn trang:", ["Analytics", "Odoo Leads"])
    
    if page == "Analytics":
        analytics_page()
    elif page == "Odoo Leads":
        odoo_lead_page()

if __name__ == "__main__":
    main() 