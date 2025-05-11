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
        
        # Calculate residual tenure if redemption date exists
        if 'Redemption Date' in df.columns:
            today = datetime.now()
            df['Residual Tenure (Years)'] = ((df['Redemption Date'] - today).dt.days / 365).round(1)
        
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

def calculate_returns(investment_amount, coupon_rate, frequency, years):
    """Calculate bond returns based on investment parameters"""
    periods = years * frequency
    periodic_rate = coupon_rate / frequency / 100  # Convert percentage to decimal
    future_value = investment_amount * (1 + periodic_rate) ** periods
    return future_value

def display_bond_metrics(selected_bond):
    """Display key metrics for the selected bond"""
    metrics = st.container()
    
    col1, col2, col3 = metrics.columns(3)
    
    with col1:
        st.metric("Coupon Rate", f"{selected_bond['Coupon']:.2f}%")
        st.metric("Offer Yield", f"{selected_bond.get('Offer Yield', 0):.2f}%")
    
    with col2:
        st.metric("Credit Rating", selected_bond.get('Credit Rating', 'N/A'))
        st.metric("Residual Tenure", 
                 f"{selected_bond.get('Residual Tenure (Years)', 'N/A')} years")
    
    with col3:
        st.metric("Interest Frequency", selected_bond.get('Interest Payment Frequency', 'N/A'))
        secured_status = "🛡️ Secured" if selected_bond.get('Secured / Unsecured') == 'Secured' else "⚠️ Unsecured"
        st.metric("Security", secured_status)

def main():
    set_custom_styles()
    st.title("📊 Bond Investment Dashboard with USDINR Hedge")
    st.markdown("""
        <div class="highlight-box">
            Analyze bond investments and calculate optimal USDINR futures hedge ratios to protect against currency risk.
        </div>
    """, unsafe_allow_html=True)
    
    # Load data automatically from root directory
    st.sidebar.header("Data Source")
    st.sidebar.write(f"Loading from: BB Inventory_29-04-2025.xlsx")
    
    bonds_df = load_bond_data()
    
    if bonds_df.empty:
        st.error("No bond data loaded. Please ensure the Excel file exists in the root directory.")
        st.stop()
    
    # Show raw data option
    if st.sidebar.checkbox("Show Raw Data"):
        st.subheader("Raw Bond Data")
        st.dataframe(bonds_df)
    
    # Sidebar filters
    st.sidebar.header("Filter Bonds")
    
    # Security type filter
    secured_options = ['All'] + sorted(bonds_df['Secured / Unsecured'].dropna().unique().tolist())
    secured_filter = st.sidebar.selectbox("Security Type", secured_options)
    
    # Credit rating filter
    credit_rating_options = sorted(bonds_df['Credit Rating'].dropna().unique())
    credit_rating_filter = st.sidebar.multiselect("Credit Rating", credit_rating_options)
    
    # Interest frequency filter
    interest_freq_options = sorted(bonds_df['Interest Payment Frequency'].dropna().unique())
    interest_freq_filter = st.sidebar.multiselect("Interest Frequency", interest_freq_options)
    
    # Yield range filter
    min_yield = float(bonds_df['Offer Yield'].min())
    max_yield = float(bonds_df['Offer Yield'].max())
    yield_range = st.sidebar.slider(
        "Yield Range (%)",
        min_value=min_yield,
        max_value=max_yield,
        value=(min_yield, max_yield)
    )
    
    # Apply filters
    filtered_bonds = bonds_df.copy()
    
    if secured_filter != 'All':
        filtered_bonds = filtered_bonds[filtered_bonds['Secured / Unsecured'] == secured_filter]
    
    if credit_rating_filter:
        filtered_bonds = filtered_bonds[filtered_bonds['Credit Rating'].isin(credit_rating_filter)]
    
    if interest_freq_filter:
        filtered_bonds = filtered_bonds[filtered_bonds['Interest Payment Frequency'].isin(interest_freq_filter)]
    
    filtered_bonds = filtered_bonds[
        (filtered_bonds['Offer Yield'] >= yield_range[0]) & 
        (filtered_bonds['Offer Yield'] <= yield_range[1])
    ]
    
    # Display filtered bonds
    st.header("📋 Available Bonds")
    
    if len(filtered_bonds) == 0:
        st.warning("No bonds match your criteria. Please adjust your filters.")
        return
    
    # Market overview
    st.subheader("📈 Market Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Bonds", len(filtered_bonds))
    with col2:
        st.metric("Average Yield", f"{filtered_bonds['Offer Yield'].mean():.2f}%")
    with col3:
        secured_count = len(filtered_bonds[filtered_bonds['Secured / Unsecured'] == 'Secured'])
        st.metric("Secured Bonds", secured_count)
    
    # Visualizations
    st.subheader("📊 Market Visualizations")
    tab1, tab2 = st.tabs(["Credit Ratings", "Yield Distribution"])
    
    with tab1:
        rating_dist = filtered_bonds['Credit Rating'].value_counts().reset_index()
        fig = px.bar(rating_dist, x='Credit Rating', y='count', 
                     title='Credit Rating Distribution')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = px.box(filtered_bonds, x='Credit Rating', y='Offer Yield', 
                     title='Yield Distribution by Credit Rating')
        st.plotly_chart(fig, use_container_width=True)
    
    # Investment calculator
    st.header("💰 Investment Calculator")
    selected_isin = st.selectbox("Select Bond ISIN", filtered_bonds['ISIN'].unique())
    selected_bond = filtered_bonds[filtered_bonds['ISIN'] == selected_isin].iloc[0]
    
    display_bond_metrics(selected_bond)
    
    # Investment parameters
    st.subheader("Investment Parameters")
    col1, col2 = st.columns(2)
    
    with col1:
        investment_amount = st.number_input("Amount to Invest (INR)", 
                                          min_value=10000, 
                                          step=10000, 
                                          value=1000000)
        usdinr_rate = st.number_input("Current USDINR Rate", 
                                     min_value=70.0, 
                                     max_value=100.0, 
                                     value=85.0, 
                                     step=0.1)
    
    with col2:
        investment_period = st.selectbox("Investment Horizon (Years)", [1, 2, 3, 4, 5], index=2)
        exit_usdinr_rate = st.number_input("Expected Exit USDINR Rate", 
                                          min_value=70.0, 
                                          max_value=100.0, 
                                          value=85.0 * 1.05, 
                                          step=0.1)
    
    # Calculate returns
    frequency_map = {'Monthly': 12, 'Quarterly': 4, 'Semi-Annual': 2, 'Annual': 1}
    frequency = frequency_map.get(selected_bond.get('Interest Payment Frequency', 'Annual'), 1)
    coupon_rate = selected_bond['Coupon']
    
    future_value = calculate_returns(investment_amount, coupon_rate, frequency, investment_period)
    investment_usd = investment_amount / usdinr_rate
    unhedged_usd_value = future_value / exit_usdinr_rate
    
    # Hedge calculation
    contract_size = 1000  # USDINR futures contract size
    required_contracts = round(investment_usd / contract_size)
    futures_pl = (exit_usdinr_rate - usdinr_rate) * contract_size * required_contracts
    net_inr = future_value + futures_pl
    net_usd = net_inr / exit_usdinr_rate
    
    # Display results
    st.header("📈 Investment Results")
    
    results_tab1, results_tab2, results_tab3 = st.tabs(["INR Returns", "USD Returns", "Hedge Analysis"])
    
    with results_tab1:
        st.subheader("INR Returns")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Initial Investment", f"₹{investment_amount:,.2f}")
            st.metric("Projected Value", f"₹{future_value:,.2f}")
        with col2:
            st.metric("Total Return", f"₹{future_value - investment_amount:,.2f}",
                     delta=f"{((future_value/investment_amount)-1)*100:.2f}%")
            st.metric("Annualized Return", f"{((future_value/investment_amount)**(1/investment_period)-1)*100:.2f}%")
    
    with results_tab2:
        st.subheader("USD Returns (Unhedged)")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Initial Investment", f"${investment_usd:,.2f}")
            st.metric("Projected Value", f"${unhedged_usd_value:,.2f}")
        with col2:
            st.metric("Total Return", f"${unhedged_usd_value - investment_usd:,.2f}",
                     delta=f"{((unhedged_usd_value/investment_usd)-1)*100:.2f}%")
            st.metric("Annualized Return", f"{((unhedged_usd_value/investment_usd)**(1/investment_period)-1)*100:.2f}%")
    
    with results_tab3:
        st.subheader("USDINR Futures Hedge")
        st.markdown("""
        **Hedge Strategy:**  
        When investing in INR bonds with USD, you're naturally short USD/long INR.  
        To hedge, go long USDINR futures to offset currency risk.
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Contracts Needed", required_contracts)
            st.metric("Futures P&L", f"₹{futures_pl:,.2f}")
        with col2:
            st.metric("Hedged USD Value", f"${net_usd:,.2f}")
            st.metric("Effective USDINR Rate", f"{investment_amount/net_usd:.2f}")
        
        # Hedge effectiveness chart
        rate_changes = np.linspace(usdinr_rate*0.8, usdinr_rate*1.2, 20)
        unhedged_values = future_value / rate_changes
        hedged_values = [(future_value + (r-usdinr_rate)*contract_size*required_contracts)/r for r in rate_changes]
        
        fig = px.line(
            x=rate_changes, y=[unhedged_values, hedged_values],
            labels={'x': 'USDINR Rate', 'y': 'Portfolio Value (USD)'},
            title='Hedge Effectiveness Across Exchange Rates'
        )
        fig.update_traces(name='Unhedged', selector={'name': 'wide_variable_0'})
        fig.update_traces(name='Hedged', selector={'name': 'wide_variable_1'})
        fig.add_vline(x=usdinr_rate, line_dash="dash", line_color="green")
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
