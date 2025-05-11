import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

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

def load_bond_data(file_path):
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Standardize column names (handle different Excel formats)
        df.columns = df.columns.str.strip()
        
        # Convert relevant columns to proper types
        if 'Redemption Date' in df.columns:
            df['Redemption Date'] = pd.to_datetime(df['Redemption Date'])
        if 'Call/Put Date' in df.columns:
            df['Call/Put Date'] = pd.to_datetime(df['Call/Put Date'], errors='coerce')
        
        # Calculate residual tenure if not present
        if 'Residual Tenure' not in df.columns and 'Redemption Date' in df.columns:
            today = datetime.now()
            df['Residual Tenure'] = (df['Redemption Date'] - today).apply(
                lambda x: f"{round(x.days/365, 1)} years" if pd.notnull(x) else "N/A"
            )
        
        return df
    
    except Exception as e:
        st.error(f"Error loading Excel file: {str(e)}")
        return pd.DataFrame()

def calculate_returns(investment_amount, coupon_rate, frequency, years):
    """Calculate bond returns based on investment parameters"""
    periods = years * frequency
    periodic_rate = coupon_rate / frequency
    future_value = investment_amount * (1 + periodic_rate) ** periods
    return future_value

def display_bond_metrics(selected_bond):
    """Display key metrics for the selected bond"""
    metrics = st.container()
    
    col1, col2, col3 = metrics.columns(3)
    
    with col1:
        st.metric("Coupon Rate", f"{selected_bond['Coupon']}%")
        st.metric("Offer Yield", f"{selected_bond['Offer Yield']}%")
    
    with col2:
        st.metric("Credit Rating", selected_bond['Credit Rating'])
        st.metric("Residual Tenure", selected_bond['Residual Tenure'])
    
    with col3:
        st.metric("Interest Frequency", selected_bond['Interest Payment Frequency'])
        secured_status = "🛡️ Secured" if selected_bond['Secured / Unsecured'] == 'Secured' else "⚠️ Unsecured"
        st.metric("Security", secured_status)

def main():
    set_custom_styles()
    st.title("📊 Bond Investment Dashboard with USDINR Hedge")
    st.markdown("""
        <div class="highlight-box">
            Analyze bond investments and calculate optimal USDINR futures hedge ratios to protect against currency risk.
        </div>
    """, unsafe_allow_html=True)
    
    # File upload
    st.sidebar.header("Data Import")
    uploaded_file = st.sidebar.file_uploader("Upload BB Inventory Excel File", type=["xlsx"])
    
    if uploaded_file is None:
        st.warning("Please upload the 'BB Inventory_29-04-2025.xlsx' file to proceed")
        st.stop()
    
    # Load data
    bonds_df = load_bond_data(uploaded_file)
    
    if bonds_df.empty:
        st.error("Failed to load bond data. Please check the file format.")
        st.stop()
    
    # Show raw data option
    if st.sidebar.checkbox("Show Raw Data"):
        st.subheader("Raw Bond Data")
        st.dataframe(bonds_df)
    
    # Sidebar filters
    st.sidebar.header("Filter Bonds")
    
    # Dynamic filters based on available columns
    if 'Secured / Unsecured' in bonds_df.columns:
    secured_filter = st.sidebar.selectbox(
        "Security Type", 
        ['All'] + sorted(bonds_df['Secured / Unsecured'].dropna().unique().tolist())
    )
else:    
        secured_filter = 'All'
    
    if 'Credit Rating' in bonds_df.columns:
        credit_rating_filter = st.sidebar.multiselect(
            "Credit Rating", 
            sorted(bonds_df['Credit Rating'].dropna().unique()))
    else:
        credit_rating_filter = []
    
    if 'Interest Payment Frequency' in bonds_df.columns:
        interest_freq_filter = st.sidebar.multiselect(
            "Interest Frequency", 
            sorted(bonds_df['Interest Payment Frequency'].dropna().unique()))
    else:
        interest_freq_filter = []
    
    # Yield range filter if available
    if 'Offer Yield' in bonds_df.columns:
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
    
    if 'Offer Yield' in bonds_df.columns:
        filtered_bonds = filtered_bonds[
            (filtered_bonds['Offer Yield'] >= yield_range[0]) & 
            (filtered_bonds['Offer Yield'] <= yield_range[1])
        ]
    
    # Display filtered bonds
    st.header("📋 Available Bonds")
    
    if len(filtered_bonds) == 0:
        st.warning("No bonds match your criteria. Please adjust your filters.")
        return
    
    # Show summary statistics
    st.subheader("📈 Market Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Bonds", len(filtered_bonds))
    
    with col2:
        avg_yield = filtered_bonds['Offer Yield'].mean() if 'Offer Yield' in filtered_bonds.columns else 0
        st.metric("Average Yield", f"{avg_yield:.2f}%")
    
    with col3:
        st.metric("Secured Bonds", 
                 len(filtered_bonds[filtered_bonds['Secured / Unsecured'] == 'Secured']) if 'Secured / Unsecured' in filtered_bonds.columns else "N/A")
    
    # Visualizations
    viz_col1, viz_col2 = st.columns(2)
    
    with viz_col1:
        if 'Credit Rating' in filtered_bonds.columns:
            rating_dist = filtered_bonds['Credit Rating'].value_counts().reset_index()
            rating_dist.columns = ['Credit Rating', 'Count']
            fig = px.bar(rating_dist, x='Credit Rating', y='Count', 
                         title='Credit Rating Distribution', color='Credit Rating')
            st.plotly_chart(fig, use_container_width=True)
    
    with viz_col2:
        if 'Offer Yield' in filtered_bonds.columns and 'Credit Rating' in filtered_bonds.columns:
            fig = px.box(filtered_bonds, x='Credit Rating', y='Offer Yield', 
                         title='Yield Distribution by Credit Rating')
            st.plotly_chart(fig, use_container_width=True)
    
    # Detailed bond table with sortable columns
    st.subheader("🔍 Bond Details")
    st.dataframe(filtered_bonds.style.format({
        'Coupon': '{:.2f}%',
        'Offer Yield': '{:.2f}%',
        'Face Value': '₹{:,}'
    }), height=400)
    
    # Investment section
    st.header("💰 Investment Calculator")
    selected_isin = st.selectbox("Select Bond ISIN", filtered_bonds['ISIN'].unique())
    
    selected_bond = filtered_bonds[filtered_bonds['ISIN'] == selected_isin].iloc[0]
    
    # Display bond metrics
    display_bond_metrics(selected_bond)
    
    # Investment parameters
    st.subheader("Investment Parameters")
    col1, col2 = st.columns(2)
    
    with col1:
        investment_amount = st.number_input("Amount to Invest (INR)", 
                                          min_value=10000, 
                                          step=10000, 
                                          value=1000000,
                                          format="%d")
        
        usdinr_rate = st.number_input("Current USDINR Rate", 
                                     min_value=70.0, 
                                     max_value=100.0, 
                                     value=85.0, 
                                     step=0.1)
    
    with col2:
        investment_period = st.selectbox("Investment Horizon (Years)", 
                                       [1, 2, 3, 4, 5], 
                                       index=2)
        
        exit_usdinr_rate = st.number_input("Expected Exit USDINR Rate", 
                                          min_value=70.0, 
                                          max_value=100.0, 
                                          value=usdinr_rate * 1.05, 
                                          step=0.1,
                                          help="Projected USDINR rate at end of investment period")
    
    # Calculate returns
    frequency_map = {
        'Monthly': 12,
        'Quarterly': 4,
        'Semi-Annual': 2,
        'Annual': 1
    }
    frequency = frequency_map.get(selected_bond.get('Interest Payment Frequency', 'Annual'), 1)
    coupon_rate = selected_bond['Coupon'] / 100
    
    future_value = calculate_returns(investment_amount, coupon_rate, frequency, investment_period)
    investment_usd = investment_amount / usdinr_rate
    unhedged_usd_value = future_value / exit_usdinr_rate
    
    # Hedge calculation
    contract_size = 1000  # USDINR futures are typically 1000 USD per contract
    required_contracts = round(investment_usd / contract_size)
    futures_pl = (exit_usdinr_rate - usdinr_rate) * contract_size * required_contracts
    net_inr = future_value + futures_pl
    net_usd = net_inr / exit_usdinr_rate
    
    # Display results
    st.header("📊 Investment Results")
    
    tab1, tab2, tab3 = st.tabs(["INR Returns", "USD Returns", "Hedge Analysis"])
    
    with tab1:
        st.subheader("Local Currency (INR) Returns")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Initial Investment", f"₹{investment_amount:,.2f}")
            st.metric("Projected Value", f"₹{future_value:,.2f}")
        
        with col2:
            total_return = future_value - investment_amount
            return_class = "positive" if total_return >= 0 else "negative"
            st.metric("Total Return", 
                     f"₹{total_return:,.2f}", 
                     delta=f"{((future_value/investment_amount)-1)*100:.2f}%")
            
            annualized_return = ((future_value / investment_amount) ** (1/investment_period) - 1) * 100
            st.metric("Annualized Return", 
                     f"{annualized_return:.2f}%")
    
    with tab2:
        st.subheader("USD Returns")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Initial Investment", f"${investment_usd:,.2f}")
            st.metric("Unhedged Value", f"${unhedged_usd_value:,.2f}")
        
        with col2:
            usd_return = unhedged_usd_value - investment_usd
            return_class = "positive" if usd_return >= 0 else "negative"
            st.metric("Unhedged Return", 
                     f"${usd_return:,.2f}", 
                     delta=f"{((unhedged_usd_value/investment_usd)-1)*100:.2f}%",
                     delta_color="off")
            
            usd_annualized = ((unhedged_usd_value / investment_usd) ** (1/investment_period) - 1) * 100
            st.metric("Unhedged Annualized", 
                     f"{usd_annualized:.2f}%")
    
    with tab3:
        st.subheader("USDINR Futures Hedge")
        st.markdown("""
            **Hedge Strategy:**  
            When investing in INR assets with USD, you're naturally short USD/long INR.  
            To hedge, go long USDINR futures to offset currency risk.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Futures Contracts Needed", required_contracts)
            st.metric("Contract Size", "$1,000")
        
        with col2:
            st.metric("Futures P&L", f"₹{futures_pl:,.2f}")
            st.metric("Hedged USD Value", f"${net_usd:,.2f}")
        
        # Scenario comparison
        st.subheader("Scenario Comparison")
        comparison_data = {
            'Scenario': ['Unhedged', 'Hedged'],
            'Final USD Value': [unhedged_usd_value, net_usd],
            'Total Return (USD)': [unhedged_usd_value - investment_usd, net_usd - investment_usd],
            'Annualized Return': [
                ((unhedged_usd_value / investment_usd) ** (1/investment_period) - 1) * 100,
                ((net_usd / investment_usd) ** (1/investment_period) - 1) * 100
            ]
        }
        
        st.dataframe(pd.DataFrame(comparison_data).style.format({
            'Final USD Value': '${:,.2f}',
            'Total Return (USD)': '${:,.2f}',
            'Annualized Return': '{:.2f}%'
        }))
        
        # Hedge effectiveness visualization
        rate_changes = np.linspace(usdinr_rate * 0.8, usdinr_rate * 1.2, 20)
        unhedged_values = future_value / rate_changes
        hedged_values = [(future_value + (r - usdinr_rate) * contract_size * required_contracts) / r for r in rate_changes]
        
        fig = px.line(
            x=rate_changes, 
            y=[unhedged_values, hedged_values],
            labels={'x': 'USDINR Rate at Exit', 'y': 'Portfolio Value (USD)', 'value': 'Scenario'},
            title='Hedge Effectiveness Across Exchange Rates'
        )
        fig.update_traces(name='Unhedged', selector={'name': 'wide_variable_0'})
        fig.update_traces(name='Hedged', selector={'name': 'wide_variable_1'})
        fig.add_vline(x=usdinr_rate, line_dash="dash", line_color="green", 
                     annotation_text="Entry Rate", annotation_position="top right")
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
