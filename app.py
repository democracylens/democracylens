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
    """Create database connection with connection pooling and SSL."""
    # Use st.secrets for Streamlit Cloud, fallback to os.environ for local dev
    def get_secret(key, default=None):
        try:
            return st.secrets.get(key, os.environ.get(key, default))
        except:
            return os.environ.get(key, default)

    url = (
        f"postgresql+psycopg2://{get_secret('DB_USER')}:{get_secret('DB_PASSWORD')}"
        f"@{get_secret('DB_HOST')}:{get_secret('DB_PORT', '5432')}/{get_secret('DB_NAME')}"
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

        # Democracy Pulse - Recent Events Section
        st.divider()
        st.subheader(f"📊 Democracy Pulse — {country}")
        st.caption("Real-time democracy events from the last 90 days")

        # Load recent events for this country
        events_query = text("""
            SELECT
                e.event_date,
                e.event_type,
                e.sub_event_type,
                e.disorder_type,
                e.fatalities,
                e.notes,
                e.location_name,
                e.source
            FROM events e
            JOIN countries c ON c.id = e.country_id
            WHERE c.name = :country
            AND e.event_date >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY e.event_date DESC
        """)

        try:
            events_df = pd.read_sql(events_query, engine, params={"country": country})

            if not events_df.empty:
                # Event summary metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    total_events = len(events_df)
                    st.metric("Total Events", total_events)

                with col2:
                    protests = len(events_df[events_df.event_type == "Protests"])
                    st.metric("Protests", protests)

                with col3:
                    riots = len(events_df[events_df.event_type == "Riots"])
                    st.metric("Riots", riots)

                with col4:
                    total_fatalities = events_df.fatalities.sum()
                    st.metric("Total Fatalities", int(total_fatalities))

                # Event type breakdown
                st.markdown("#### Event Type Breakdown")
                event_counts = events_df.groupby('event_type').size().reset_index(name='count')
                event_counts = event_counts.sort_values('count', ascending=False)
                st.bar_chart(event_counts.set_index('event_type')['count'])

                # Recent events timeline
                st.markdown("#### Recent Events Timeline")

                # Time period selector
                time_period = st.radio(
                    "Select time period",
                    ["Last 30 days", "Last 90 days"],
                    horizontal=True
                )

                days = 30 if time_period == "Last 30 days" else 90
                filtered_events = events_df[
                    pd.to_datetime(events_df.event_date) >=
                    pd.Timestamp.now() - pd.Timedelta(days=days)
                ]

                if not filtered_events.empty:
                    # Display events as expandable list
                    for idx, event in filtered_events.iterrows():
                        event_date = pd.to_datetime(event.event_date).strftime("%Y-%m-%d")
                        event_type = event.event_type
                        location = event.location_name or "Unknown location"
                        fatalities = f" ({int(event.fatalities)} fatalities)" if event.fatalities > 0 else ""

                        with st.expander(f"{event_date} • {event_type} • {location}{fatalities}"):
                            st.write(f"**Type:** {event.event_type}")
                            if event.sub_event_type:
                                st.write(f"**Sub-type:** {event.sub_event_type}")
                            if event.disorder_type:
                                st.write(f"**Disorder Type:** {event.disorder_type}")
                            st.write(f"**Location:** {location}")
                            if event.fatalities > 0:
                                st.write(f"**Fatalities:** {int(event.fatalities)}")
                            if event.notes:
                                st.write(f"**Details:** {event.notes}")
                            st.caption(f"Source: {event.source}")
                else:
                    st.info(f"No events recorded in the last {days} days")

            else:
                st.info(f"No recent events available for {country}.")

        except Exception as e:
            # Events table might not exist yet
            st.info("Real-time event tracking coming soon. Run database migration to enable.")
            st.caption("Migration: `python migrations/apply_migration.py 001_add_events_table.sql`")

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
    <p>Data sources: Freedom House • World Bank WGI</p>
    <p>This dashboard presents factual data without political commentary or advocacy.</p>
</div>
""", unsafe_allow_html=True)
