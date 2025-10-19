import os, pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv(override=True)

engine = create_engine(
    f"postgresql+psycopg2://{os.environ['DB_ADMIN_USER']}:{os.environ['DB_ADMIN_PW']}@{os.environ['DB_HOST']}:{os.environ.get('DB_PORT','5432')}/{os.environ['DB_NAME']}",
    pool_pre_ping=True,
)

sample = os.path.join(os.path.dirname(__file__), "data", "freedom_house_sample.csv")
df = pd.read_csv(sample)
with engine.begin() as cxn:
    for _, row in df.iterrows():
        cxn.execute(
            "INSERT INTO metrics (country_id, metric_name, metric_value, source, date) VALUES (1, %s, %s, %s, %s)",
            (row.metric_name, row.metric_value, "Freedom House (sample)", row.date),
        )
print("Loaded sample metrics.")
