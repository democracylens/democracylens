import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)
st.set_page_config(page_title="Global Democracy Dashboard", layout="wide")
st.title("Global Democracy Dashboard — MVP")

@st.cache_resource(show_spinner=False)
def get_engine():
    url = f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ.get('DB_PORT','5432')}/{os.environ['DB_NAME']}"
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()
countries = pd.read_sql("select name from countries order by name", engine)
country = st.selectbox("Country", countries['name'].tolist())
q = text('''
    select m.date, m.metric_name, m.metric_value
    from metrics m join countries c on c.id = m.country_id
    where c.name = :country order by m.date asc
''')
df = pd.read_sql(q, engine, params={"country": country})
if not df.empty:
    metric = st.selectbox("Metric", sorted(df.metric_name.unique()))
    sub = df[df.metric_name == metric].copy()
    sub['date'] = pd.to_datetime(sub['date'])
    sub = sub.set_index('date').sort_index()
    st.line_chart(sub['metric_value'])
    st.dataframe(sub.reset_index())
else:
    st.warning("No metrics found. Load sample data first.")
