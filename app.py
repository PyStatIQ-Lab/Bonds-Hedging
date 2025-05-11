import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Sample bond data
def load_sample_data():
    data = {
        'ISIN': ['IN1234567890', 'IN9876543210', 'IN4567890123', 'IN3210987654'],
        'Issuer Name': ['ABC Corporation', 'XYZ Limited', 'National Bonds', 'Global Finance'],
        'Coupon': [7.5, 8.25, 6.75, 9.0],
        'Redemption Date': ['2025-12-31', '2026-06-30', '2027-03-15', '2028-09-30'],
        'Call/Put Date': ['', '2025-12-31', '', '2027-09-30'],
        'Face Value': [1000, 1000, 1000, 1000],
        'Residual Tenure': ['1.5 years', '2 years', '3.5 years', '5 years'],
        'Secured / Unsecured': ['Secured', 'Unsecured', 'Secured', 'Unsecured'],
        'Special Feature': ['Callable', 'Puttable', '', 'Callable'],
        'Total Tradable Qty': [50000, 75000, 100000, 25000],
        'Total Tradable FV': [50000000, 75000000, 100000000, 25000000],
        'Offer Yield': [7.8, 8.5, 7.2, 9.5],
        'Credit Rating': ['AA', 'A', 'AAA', 'BBB'],
        'Outlook': ['Stable', 'Positive', 'Stable', 'Negative'],
        'Interest Payment Frequency': ['Quarterly', 'Semi-Annual', 'Annual', 'Monthly'],
        'Principal Redemption': ['Bullet', 'Amortizing', 'Bullet', 'Bullet']
    }
    return pd.DataFrame(data)

def main():
    st.title("Bond Investment Calculator with USDINR Hedge")
    
    # Load sample data
    bonds_df = load_sample_data()
    
    # Convert dates to datetime
    bonds_df['Redemption Date'] = pd.to_datetime(bonds_df['Redemption Date'])
    
    # Sidebar filters
    st.sidebar.header("Filter Bonds")
    
    secured_filter = st.sidebar.selectbox("Secured/Unsecured", ['All', 'Secured', 'Unsecured'])
    credit_rating_filter = st.sidebar.multiselect("Credit Rating", sorted(bonds_df['Credit Rating'].unique()))
    interest_freq_filter = st.sidebar.multiselect("Interest Payment Frequency", 
                                                sorted(bonds_df['Interest Payment Frequency'].unique()))
    
    # Yield range filter
    min_yield, max_yield = st.sidebar.slider(
        "Offer Yield Range (%)",
        min_value=float(bonds_df['Offer Yield'].min()),
        max_value=float(bonds_df['Offer Yield'].max()),
        value=(float(bonds_df['Offer Yield'].min()), float(bonds_df['Offer Yield'].max()))
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
        (filtered_bonds['Offer Yield'] >= min_yield) & 
        (filtered_bonds['Offer Yield'] <= max_yield)
    ]
    
    # Display filtered bonds
    st.header("Available Bonds")
    st.dataframe(filtered_bonds)
    
    if len(filtered_bonds) == 0:
        st.warning("No bonds match your criteria. Please adjust your filters.")
        return
    
    # Investment details
    st.header("Investment Details")
    selected_isin = st.selectbox("Select Bond ISIN", filtered_bonds['ISIN'])
    
    selected_bond = filtered_bonds[filtered_bonds['ISIN'] == selected_isin].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Bond Details")
        st.write(f"**Issuer:** {selected_bond['Issuer Name']}")
        st.write(f"**Coupon:** {selected_bond['Coupon']}%")
        st.write(f"**Offer Yield:** {selected_bond['Offer Yield']}%")
        st.write(f"**Credit Rating:** {selected_bond['Credit Rating']}")
        st.write(f"**Interest Frequency:** {selected_bond['Interest Payment Frequency']}")
        st.write(f"**Secured/Unsecured:** {selected_bond['Secured / Unsecured']}")
    
    with col2:
        st.subheader("Investment Amount")
        investment_amount = st.number_input("Amount to Invest (INR)", min_value=10000, step=10000, value=1000000)
        
        usdinr_rate = st.number_input("Current USDINR Rate", min_value=70.0, max_value=100.0, value=85.0, step=0.1)
        
        investment_usd = investment_amount / usdinr_rate
        st.write(f"**Investment Amount in USD:** ${investment_usd:,.2f}")
        
        investment_period = st.selectbox("Investment Horizon (Years)", [1, 2, 3, 4, 5], index=2)
    
    # Calculate returns
    coupon_rate = selected_bond['Coupon'] / 100
    frequency_map = {
        'Monthly': 12,
        'Quarterly': 4,
        'Semi-Annual': 2,
        'Annual': 1
    }
    frequency = frequency_map.get(selected_bond['Interest Payment Frequency'], 1)
    
    periods = investment_period * frequency
    periodic_rate = coupon_rate / frequency
    
    # Future value calculation
    future_value = investment_amount * (1 + periodic_rate) ** periods
    
    # Display returns
    st.header("Projected Returns")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("INR Returns")
        st.write(f"**Initial Investment:** ₹{investment_amount:,.2f}")
        st.write(f"**Projected Value after {investment_period} years:** ₹{future_value:,.2f}")
        st.write(f"**Total Return:** ₹{future_value - investment_amount:,.2f}")
        st.write(f"**Annualized Return:** {((future_value / investment_amount) ** (1/investment_period) - 1) * 100:.2f}%")
    
    with col2:
        st.subheader("USD Returns (Unhedged)")
        st.write(f"**Initial Investment:** ${investment_usd:,.2f}")
        
        # Assume USDINR rate changes
        exit_usdinr_rate = st.number_input("Expected Exit USDINR Rate", min_value=70.0, max_value=100.0, 
                                         value=usdinr_rate * 1.05, step=0.1)
        
        unhedged_usd_value = future_value / exit_usdinr_rate
        st.write(f"**Unhedged USD Value:** ${unhedged_usd_value:,.2f}")
        st.write(f"**Unhedged Return:** ${unhedged_usd_value - investment_usd:,.2f}")
        st.write(f"**Unhedged Annualized Return:** {((unhedged_usd_value / investment_usd) ** (1/investment_period) - 1) * 100:.2f}%")
    
    # Hedge calculation
    st.header("USDINR Futures Hedge")
    
    st.markdown("""
    **Hedge Rationale:**  
    When you invest in INR assets (bonds) using USD, you're short USD and long INR by nature.  
    To hedge, you want to go long USDINR futures.
    """)
    
    # USDINR futures contract details
    contract_size = 1000  # USDINR futures are typically 1000 USD per contract
    required_contracts = round(investment_usd / contract_size)
    
    st.write(f"**USDINR Futures Contract Size:** $1,000")
    st.write(f"**Number of Contracts Needed:** {required_contracts}")
    
    # Hedge scenario analysis
    st.subheader("Hedged Scenario Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**At Entry**")
        st.write(f"- Investment in INR: ₹{investment_amount:,.2f}")
        st.write(f"- USDINR Rate: {usdinr_rate}")
        st.write(f"- Long {required_contracts} USDINR Futures @ {usdinr_rate}")
    
    with col2:
        st.write("**At Exit**")
        st.write(f"- Bond Value in INR: ₹{future_value:,.2f}")
        st.write(f"- USDINR Rate: {exit_usdinr_rate}")
        
        # Futures P&L calculation
        futures_pl = (exit_usdinr_rate - usdinr_rate) * contract_size * required_contracts
        st.write(f"- Long Futures P&L: ₹{futures_pl:,.2f}")
        
        # Net position
        net_inr = future_value + futures_pl
        net_usd = net_inr / exit_usdinr_rate
        st.write(f"- Net INR = Bond + Futures: ₹{net_inr:,.2f}")
        st.write(f"- Net USD after hedge: ${net_usd:,.2f}")
    
    # Comparison
    st.subheader("Comparison")
    
    comparison_data = {
        'Metric': ['Final Value (USD)', 'Return (USD)', 'Annualized Return'],
        'Unhedged': [
            f"${unhedged_usd_value:,.2f}",
            f"${unhedged_usd_value - investment_usd:,.2f}",
            f"{((unhedged_usd_value / investment_usd) ** (1/investment_period) - 1) * 100:.2f}%"
        ],
        'Hedged': [
            f"${net_usd:,.2f}",
            f"${net_usd - investment_usd:,.2f}",
            f"{((net_usd / investment_usd) ** (1/investment_period) - 1) * 100:.2f}%"
        ]
    }
    
    st.table(pd.DataFrame(comparison_data))
    
    # Explanation
    st.markdown("""
    **Key Takeaways:**
    - The hedge protects against INR depreciation (USDINR rate going up)
    - If INR depreciates (USDINR rises), the futures gain offsets the currency loss
    - If INR appreciates (USDINR falls), the futures loss reduces the currency gain
    - The hedge aims to lock in the original USDINR rate for your investment
    """)

if __name__ == "__main__":
    main()
