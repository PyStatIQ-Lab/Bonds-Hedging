import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import os

# ======================
# SETUP & CONFIGURATION
# ======================
def set_custom_styles():
    st.markdown("""
        <style>
            .main {background-color: #f5f5f5;}
            .header-style {font-size:20px; color: #2e86c1;}
            .positive {color: #27ae60;}
            .negative {color: #e74c3c;}
            .highlight-box {
                background-color: #ebf5fb;
                border-radius: 5px;
                padding: 15px;
                margin: 10px 0px;
            }
            .stSelectbox, .stSlider, .stNumberInput {
                margin-bottom: 15px;
            }
        </style>
    """, unsafe_allow_html=True)

# ======================
# DATA LOADING
# ======================
def load_bond_data():
    try:
        file_path = "BB Inventory_29-04-2025.xlsx"
        if not os.path.exists(file_path):
            st.error(f"File not found: {os.path.abspath(file_path)}")
            return pd.DataFrame()
        
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        
        # Date conversions
        date_cols = ['Redemption Date', 'Call/Put Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Calculate residual tenure
        if 'Redemption Date' in df.columns:
            today = datetime.now()
            df['Residual Tenure'] = ((df['Redemption Date'] - today).dt.days / 365).round(1)
        
        return df
    
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame()

# ======================
# FINANCIAL CALCULATIONS
# ======================
def calculate_bond_returns(investment_amount, coupon_rate, frequency, years):
    """Calculate future value of bond investment"""
    periods = years * frequency
    periodic_rate = (coupon_rate / 100) / frequency
    return investment_amount * (1 + periodic_rate) ** periods

def calculate_hedge(investment_amount, usdinr_rate, exit_rate, future_value):
    """
    Calculate USDINR futures hedge requirements
    
    Returns:
    {
        'investment_usd': USD equivalent,
        'contracts_needed': Number of futures contracts,
        'futures_pl': P&L from futures position (INR),
        'hedged_value': Final portfolio value (INR),
        'hedged_usd': Final USD value after hedge
    }
    """
    investment_usd = investment_amount / usdinr_rate
    contract_size = 1000  # $1,000 per contract
    point_value = 1000    # ₹1,000 per point per contract
    
    contracts_needed = round(investment_usd / contract_size)
    futures_pl = (exit_rate - usdinr_rate) * point_value * contracts_needed
    hedged_value = future_value + futures_pl
    hedged_usd = hedged_value / exit_rate
    
    return {
        'investment_usd': investment_usd,
        'contracts_needed': contracts_needed,
        'futures_pl': futures_pl,
        'hedged_value': hedged_value,
        'hedged_usd': hedged_usd,
        'effective_rate': investment_amount / hedged_usd
    }

# ======================
# DASHBOARD COMPONENTS
# ======================
def display_bond_metrics(bond):
    """Show key bond characteristics"""
    cols = st.columns(3)
    with cols[0]:
        st.metric("Coupon", f"{bond['Coupon']}%")
        st.metric("Yield", f"{bond.get('Offer Yield', 0)}%")
    with cols[1]:
        st.metric("Rating", bond.get('Credit Rating', 'N/A'))
        st.metric("Tenure", f"{bond.get('Residual Tenure', 'N/A')} yrs")
    with cols[2]:
        st.metric("Frequency", bond.get('Interest Payment Frequency', 'N/A'))
        st.metric("Security", "🛡️ Secured" if bond.get('Secured / Unsecured') == 'Secured' else "⚠️ Unsecured")

def show_hedge_effectiveness(usdinr_rate, exit_rate, future_value, contracts_needed):
    """Interactive hedge effectiveness chart"""
    rate_range = np.linspace(usdinr_rate*0.8, usdinr_rate*1.2, 20)
    
    unhedged = [future_value/r for r in rate_range]
    hedged = [(future_value + (r-usdinr_rate)*1000*contracts_needed)/r for r in rate_range]
    
    fig = px.line(
        x=rate_range, y=[unhedged, hedged],
        labels={'x': 'USDINR Rate', 'y': 'Portfolio Value (USD)'},
        title='Hedge Effectiveness Across Exchange Rates'
    )
    fig.update_traces(name='Unhedged', selector={'name': 'wide_variable_0'})
    fig.update_traces(name='Hedged', selector={'name': 'wide_variable_1'})
    fig.add_vline(x=usdinr_rate, line_dash="dash", line_color="green")
    st.plotly_chart(fig, use_container_width=True)

# ======================
# MAIN APPLICATION
# ======================
def main():
    set_custom_styles()
    st.title("💰 Bond Investment Dashboard with USDINR Hedge")
    
    # Load data
    bonds_df = load_bond_data()
    if bonds_df.empty:
        st.error("No data loaded. Please check the Excel file.")
        st.stop()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    secured_filter = st.sidebar.selectbox(
        "Security Type",
        ['All'] + sorted(bonds_df['Secured / Unsecured'].dropna().unique().tolist())
    )
    rating_filter = st.sidebar.multiselect(
        "Credit Rating",
        sorted(bonds_df['Credit Rating'].dropna().unique())
    )
    yield_range = st.sidebar.slider(
        "Yield Range (%)",
        min_value=float(bonds_df['Offer Yield'].min()),
        max_value=float(bonds_df['Offer Yield'].max()),
        value=(float(bonds_df['Offer Yield'].min()), float(bonds_df['Offer Yield'].max()))
    )
    
    # Apply filters
    filtered_bonds = bonds_df.copy()
    if secured_filter != 'All':
        filtered_bonds = filtered_bonds[filtered_bonds['Secured / Unsecured'] == secured_filter]
    if rating_filter:
        filtered_bonds = filtered_bonds[filtered_bonds['Credit Rating'].isin(rating_filter)]
    filtered_bonds = filtered_bonds[
        (filtered_bonds['Offer Yield'] >= yield_range[0]) & 
        (filtered_bonds['Offer Yield'] <= yield_range[1])
    ]
    
    # Bond selection
    st.header("📋 Available Bonds")
    if len(filtered_bonds) == 0:
        st.warning("No bonds match criteria")
        return
    
    st.dataframe(filtered_bonds.style.format({
        'Coupon': '{:.2f}%',
        'Offer Yield': '{:.2f}%',
        'Face Value': '₹{:,}'
    }), height=400)
    
    # Investment calculator
    st.header("🧮 Investment Calculator")
    selected_bond = filtered_bonds.iloc[0]  # Default to first bond
    
    if len(filtered_bonds) > 1:
        selected_isin = st.selectbox("Select Bond", filtered_bonds['ISIN'])
        selected_bond = filtered_bonds[filtered_bonds['ISIN'] == selected_isin].iloc[0]
    
    display_bond_metrics(selected_bond)
    
    # Investment parameters
    cols = st.columns(2)
    with cols[0]:
        investment = st.number_input("Investment (₹)", min_value=10000, value=1000000, step=10000)
        usdinr_entry = st.number_input("Current USDINR", min_value=70.0, max_value=100.0, value=85.0, step=0.1)
    with cols[1]:
        horizon = st.selectbox("Horizon (Years)", [1, 2, 3, 4, 5], index=2)
        usdinr_exit = st.number_input("Expected Exit USDINR", min_value=70.0, max_value=100.0, 
                                    value=85.0*1.05, step=0.1)
    
    # Calculations
    freq_map = {'Monthly':12, 'Quarterly':4, 'Semi-Annual':2, 'Annual':1}
    freq = freq_map.get(selected_bond.get('Interest Payment Frequency', 'Annual'), 1)
    
    future_value = calculate_bond_returns(
        investment_amount=investment,
        coupon_rate=selected_bond['Coupon'],
        frequency=freq,
        years=horizon
    )
    
    hedge = calculate_hedge(
        investment_amount=investment,
        usdinr_rate=usdinr_entry,
        exit_rate=usdinr_exit,
        future_value=future_value
    )
    
    # Results display
    st.header("📊 Results")
    
    tab1, tab2, tab3 = st.tabs(["INR Returns", "USD Returns", "Hedge Analysis"])
    
    with tab1:
        st.subheader("Local Currency (INR)")
        cols = st.columns(2)
        cols[0].metric("Initial", f"₹{investment:,.2f}")
        cols[0].metric("Final", f"₹{future_value:,.2f}")
        cols[1].metric("Total Return", f"₹{future_value - investment:,.2f}")
        cols[1].metric("Annualized", f"{(future_value/investment)**(1/horizon)-1:.2%}")
    
    with tab2:
        st.subheader("USD Returns")
        cols = st.columns(2)
        cols[0].metric("Initial", f"${hedge['investment_usd']:,.2f}")
        cols[0].metric("Unhedged Final", f"${future_value/usdinr_exit:,.2f}")
        cols[1].metric("Hedged Final", f"${hedge['hedged_usd']:,.2f}")
        cols[1].metric("Effective Rate", f"{hedge['effective_rate']:.2f}")
    
    with tab3:
        st.subheader("USDINR Hedge Details")
        st.markdown("""
            **Hedge Strategy:**  
            - Each futures contract = $1,000 notional  
            - 1 point move = ₹1,000 P&L per contract  
            - Long futures hedge INR depreciation risk
        """)
        
        cols = st.columns(2)
        cols[0].metric("Contracts Needed", hedge['contracts_needed'])
        cols[0].metric("Futures P&L", f"₹{hedge['futures_pl']:,.2f}")
        cols[1].metric("Hedged Value (₹)", f"₹{hedge['hedged_value']:,.2f}")
        cols[1].metric("Hedged Value ($)", f"${hedge['hedged_usd']:,.2f}")
        
        show_hedge_effectiveness(
            usdinr_rate=usdinr_entry,
            exit_rate=usdinr_exit,
            future_value=future_value,
            contracts_needed=hedge['contracts_needed']
        )

if __name__ == "__main__":
    main()
