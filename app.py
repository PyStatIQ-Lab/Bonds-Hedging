import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import os

# Custom styling
def set_custom_styles():
    st.markdown("""
        <style>
            .main {background-color: #f5f5f5;}
            .st-bb {background-color: white;}
            .st-at {background-color: #f0f2f6;}
            .st-ax {color: black;}
            .header-style {font-size:20px; color: #2e86c1;}
            .subheader-style {font-size:16px; color: #3498db;}
            .positive {color: #27ae60;}
            .negative {color: #e74c3c;}
            .highlight-box {
                background-color: #ebf5fb;
                border-radius: 5px;
                padding: 15px;
                margin: 10px 0px;
            }
            .stMetric {border: 1px solid #d3d3d3; border-radius: 5px; padding: 10px;}
        </style>
    """, unsafe_allow_html=True)

def load_bond_data():
    try:
        # Look for the Excel file in the root directory
        file_path = "BB Inventory_29-04-2025.xlsx"
        
        if not os.path.exists(file_path):
            st.error(f"Excel file not found at: {os.path.abspath(file_path)}")
            return pd.DataFrame()
        
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Standardize column names
        df.columns = df.columns.str.strip()
        
        # Convert date columns
        date_columns = ['Redemption Date', 'Call/Put Date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Calculate residual tenure in years if redemption date exists
        if 'Redemption Date' in df.columns:
            today = datetime.now()
            df['Residual Tenure (Years)'] = ((df['Redemption Date'] - today).dt.days / 365).round(2)
        
        # Ensure required columns exist
        required_columns = ['ISIN', 'Issuer Name', 'Coupon', 'Offer Yield', 
                           'Secured / Unsecured', 'Credit Rating', 'Interest Payment Frequency']
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = None  # Add missing columns with None values
        
        return df
    
    except Exception as e:
        st.error(f"Error loading Excel file: {str(e)}")
        return pd.DataFrame()

def calculate_1year_return(investment_amount, yield_rate):
    """Calculate 1-year return based on yield"""
    return investment_amount * (1 + yield_rate/100)

def calculate_hedge(investment_inr, usdinr_rate, lot_size=1000):
    """Calculate USDINR hedge requirements"""
    investment_usd = investment_inr / usdinr_rate
    required_lots = round(investment_usd / lot_size)
    hedge_notional = required_lots * lot_size * usdinr_rate
    return investment_usd, required_lots, hedge_notional

def main():
    set_custom_styles()
    st.title("📊 1-Year Bond Returns with USDINR Hedge")
    st.markdown("""
        <div class="highlight-box">
            Calculate 1-year bond returns and hedge currency exposure with USDINR futures
        </div>
    """, unsafe_allow_html=True)
    
    # Load data
    bonds_df = load_bond_data()
    
    if bonds_df.empty:
        st.error("No bond data loaded. Please ensure the Excel file exists in the root directory.")
        st.stop()
    
    # Sidebar filters and inputs
    st.sidebar.header("Investment Parameters")
    investment_amount = st.sidebar.number_input("Investment Amount (INR)", 
                                              min_value=10000, 
                                              step=10000, 
                                              value=1000000)
    
    usdinr_rate = st.sidebar.number_input("Current USDINR Rate", 
                                         min_value=70.0, 
                                         max_value=100.0, 
                                         value=85.0, 
                                         step=0.1)
    
    exit_usdinr_rate = st.sidebar.number_input("Expected 1-Year USDINR Rate", 
                                             min_value=70.0, 
                                             max_value=100.0, 
                                             value=85.0 * 1.05,  # Default 5% depreciation
                                             step=0.1)
    
    # Filter bonds with >1 year residual tenure
    if 'Residual Tenure (Years)' in bonds_df.columns:
        bonds_df = bonds_df[bonds_df['Residual Tenure (Years)'] >= 1]
    
    # Display bond table with key metrics
    st.header("Available Bonds (1+ Year Tenure)")
    
    # Create display columns
    display_columns = ['ISIN', 'Issuer Name', 'Coupon', 'Offer Yield', 
                      'Credit Rating', 'Secured / Unsecured', 'Residual Tenure (Years)']
    
    # Filter available columns
    available_columns = [col for col in display_columns if col in bonds_df.columns]
    st.dataframe(bonds_df[available_columns], height=400)
    
    # Bond selection - only show ISINs that exist in filtered dataframe
    valid_isins = bonds_df['ISIN'].unique()
    if len(valid_isins) == 0:
        st.error("No bonds available with >1 year tenure. Please adjust your filters.")
        st.stop()
    
    selected_isin = st.selectbox("Select Bond by ISIN", valid_isins)
    
    # Get selected bond with error handling
    selected_bond_df = bonds_df[bonds_df['ISIN'] == selected_isin]
    if len(selected_bond_df) == 0:
        st.error("Selected bond not found in filtered data.")
        st.stop()
    
    selected_bond = selected_bond_df.iloc[0].to_dict()
    
    # Display bond details
    st.header("Bond Details")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Issuer", selected_bond.get('Issuer Name', 'N/A'))
        st.metric("Coupon Rate", f"{selected_bond.get('Coupon', 0):.2f}%")
        st.metric("Credit Rating", selected_bond.get('Credit Rating', 'N/A'))
    
    with col2:
        st.metric("Offer Yield", f"{selected_bond.get('Offer Yield', 0):.2f}%")
        st.metric("Residual Tenure", f"{selected_bond.get('Residual Tenure (Years)', 'N/A')} years")
        st.metric("Security", selected_bond.get('Secured / Unsecured', 'N/A'))
    
    # Calculate 1-year returns
    st.header("1-Year Return Projection")
    
    if 'Offer Yield' in selected_bond and pd.notna(selected_bond['Offer Yield']):
        yield_rate = selected_bond['Offer Yield']
        future_value = calculate_1year_return(investment_amount, yield_rate)
        return_inr = future_value - investment_amount
        return_pct = (return_inr / investment_amount) * 100
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Initial Investment", f"₹{investment_amount:,.2f}")
            st.metric("Projected Value (1 Year)", f"₹{future_value:,.2f}")
        
        with col2:
            st.metric("Total Return", f"₹{return_inr:,.2f}")
            st.metric("Return Percentage", f"{return_pct:.2f}%")
    else:
        st.warning("Yield information not available for selected bond")
        future_value = investment_amount  # Default to no return if yield not available
    
    # USDINR Hedge Calculation
    st.header("USDINR Hedge Calculation")
    st.markdown("""
    **Hedge Strategy:**  
    When investing in INR bonds with USD, you're naturally short USD/long INR.  
    To hedge, go long USDINR futures to offset currency risk.
    """)
    
    investment_usd, required_lots, hedge_notional = calculate_hedge(investment_amount, usdinr_rate)
    
    # Calculate currency impact
    unhedged_usd_value = future_value / exit_usdinr_rate
    currency_gain_loss = (unhedged_usd_value - investment_usd)
    
    # Hedged scenario
    futures_pl = (exit_usdinr_rate - usdinr_rate) * 1000 * required_lots
    hedged_inr_value = future_value + futures_pl
    hedged_usd_value = hedged_inr_value / exit_usdinr_rate
    hedge_effectiveness = ((hedged_usd_value - investment_usd) / investment_usd) * 100
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Investment in USD", f"${investment_usd:,.2f}")
        st.metric("Futures Contracts Needed", required_lots)
        st.metric("Hedge Notional (INR)", f"₹{hedge_notional:,.2f}")
    
    with col2:
        st.metric("Unhedged USD Value", f"${unhedged_usd_value:,.2f}", 
                 delta=f"{currency_gain_loss:,.2f} USD")
        st.metric("Hedged USD Value", f"${hedged_usd_value:,.2f}", 
                 delta=f"{hedge_effectiveness:.2f}%")
        st.metric("Currency Move Impact", 
                 f"{(exit_usdinr_rate/usdinr_rate-1)*100:.2f}%",
                 delta_color="inverse")
    
    # Hedge effectiveness visualization
    st.subheader("Hedge Effectiveness Across Exchange Rates")
    rate_changes = np.linspace(usdinr_rate*0.9, usdinr_rate*1.1, 20)
    unhedged_values = future_value / rate_changes
    hedged_values = [(future_value + (r-usdinr_rate)*1000*required_lots)/r for r in rate_changes]
    
    fig = px.line(
        x=rate_changes, y=[unhedged_values, hedged_values],
        labels={'x': 'USDINR Rate', 'y': 'Portfolio Value (USD)'},
        title='Portfolio Value Under Different USDINR Scenarios'
    )
    fig.update_traces(name='Unhedged', selector={'name': 'wide_variable_0'})
    fig.update_traces(name='Hedged', selector={'name': 'wide_variable_1'})
    fig.add_vline(x=usdinr_rate, line_dash="dash", line_color="green", 
                 annotation_text="Current Rate", annotation_position="top right")
    st.plotly_chart(fig, use_container_width=True)
