"""
Democracy Lens - A non-partisan democracy data dashboard
"""

import os
from datetime import datetime
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Page configuration
st.set_page_config(
    page_title="Democracy Lens",
    page_icon="🌍",
    layout="wide"
)

# Header
st.title("🌍 Democracy Lens")
st.markdown("""
A public, non-partisan dashboard tracking democracy and governance indicators worldwide.
Explore data from Freedom House, V-Dem, and other authoritative sources.
""")
st.divider()


@st.cache_resource(show_spinner=False)
def get_engine():
    """Create database connection with connection pooling (SSL for Supabase)."""
    url = (
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ.get('DB_PORT','5432')}/{os.environ['DB_NAME']}"
        f"?sslmode=require"
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=3600, show_spinner=False)
def get_last_updated(_engine):
    """Get the most recent data update timestamp."""
    try:
        result = pd.read_sql(
            "SELECT MAX(date) as last_date FROM metrics",
            _engine
        )
        if not result.empty and result.last_date[0] is not None:
            return pd.to_datetime(result.last_date[0])
    except Exception:
        pass
    return None


# Initialize database connection
try:
    engine = get_engine()

    # Get last update timestamp
    last_updated = get_last_updated(engine)

    # Load countries
    countries = pd.read_sql("SELECT name FROM countries ORDER BY name", engine)

    if countries.empty:
        st.error("No countries found in database. Please run `python init_db.py` to initialize.")
        st.stop()

    # Country selector
    col1, col2 = st.columns([3, 1])
    with col1:
        country = st.selectbox("Select Country", countries['name'].tolist())
    with col2:
        if last_updated:
            st.metric("Data Through", last_updated.strftime("%Y"))

    # Load metrics for selected country
    query = text("""
        SELECT m.date, m.metric_name, m.metric_value, m.source
        FROM metrics m
        JOIN countries c ON c.id = m.country_id
        WHERE c.name = :country
        ORDER BY m.date ASC
    """)
    df = pd.read_sql(query, engine, params={"country": country})

    if not df.empty:
        # Metric selector
        available_metrics = sorted(df.metric_name.unique())
        metric = st.selectbox("Select Metric", available_metrics)

        # Filter data for selected metric
        metric_data = df[df.metric_name == metric].copy()
        metric_data['date'] = pd.to_datetime(metric_data['date'])
        metric_data = metric_data.sort_values('date')

        # Display chart
        st.subheader(f"{metric} — {country}")

        chart_data = metric_data.set_index('date')[['metric_value']]
        st.line_chart(chart_data, use_container_width=True)

        # Display data table
        with st.expander("View Raw Data"):
            display_df = metric_data[['date', 'metric_value', 'source']].copy()
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Show data source
        sources = metric_data['source'].unique()
        if len(sources) == 1:
            st.caption(f"Data source: {sources[0]}")

    else:
        st.warning(f"No data available for {country}. Please run the ETL script to load data.")
        st.code("python etl/load_freedom_house.py", language="bash")

except Exception as e:
    st.error(f"Database connection error. Please check your environment configuration.")
    st.exception(e)
    st.stop()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p><strong>Democracy Lens Project</strong> • Non-partisan democracy data visualization</p>
    <p>Data sources: Freedom House • Additional sources in development</p>
    <p>This dashboard presents factual data without political commentary or advocacy.</p>
</div>
""", unsafe_allow_html=True)
