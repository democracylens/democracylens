"""
ETL script to load GDELT (Global Database of Events, Language, and Tone) data.

GDELT is a free, open global event database updated every 15 minutes.
No registration or API key required.

More info: https://www.gdeltproject.org/
"""

import os
import requests
import pandas as pd
import io
import zipfile
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv(override=True)

# Database connection with SSL
engine = create_engine(
    f"postgresql+psycopg2://{os.environ['DB_ADMIN_USER']}:{os.environ['DB_ADMIN_PW']}@"
    f"{os.environ['DB_HOST']}:{os.environ.get('DB_PORT','5432')}/{os.environ['DB_NAME']}"
    f"?sslmode=require",
    pool_pre_ping=True,
)

# GDELT configuration
GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
GDELT_BASE_URL = "http://data.gdeltproject.org/gdeltv2/"

# Country codes (FIPS 10-4 standard used by GDELT)
# Mapped to all 50 countries in database
COUNTRY_CODES = {
    # Original 15 countries
    "US": "United States",
    "UK": "United Kingdom",
    "GM": "Germany",
    "FR": "France",
    "JA": "Japan",
    "CA": "Canada",
    "AS": "Australia",
    "KS": "South Korea",
    "DA": "Denmark",
    "FI": "Finland",
    "NO": "Norway",
    "SW": "Sweden",
    "SZ": "Switzerland",
    "NL": "Netherlands",
    "NZ": "New Zealand",

    # Latin America (7 countries)
    "BR": "Brazil",
    "MX": "Mexico",
    "AR": "Argentina",
    "CI": "Chile",
    "CO": "Colombia",
    "PE": "Peru",
    "VE": "Venezuela",

    # Asia-Pacific (7 countries)
    "IN": "India",
    "ID": "Indonesia",
    "RP": "Philippines",
    "TH": "Thailand",
    "MY": "Malaysia",
    "TW": "Taiwan",
    "SN": "Singapore",

    # Eastern Europe (5 countries)
    "PL": "Poland",
    "EZ": "Czech Republic",
    "HU": "Hungary",
    "RO": "Romania",
    "UP": "Ukraine",

    # Middle East & North Africa (4 countries)
    "IS": "Israel",
    "TU": "Turkey",
    "TS": "Tunisia",
    "EG": "Egypt",

    # Sub-Saharan Africa (5 countries)
    "SF": "South Africa",
    "NI": "Nigeria",
    "KE": "Kenya",
    "GH": "Ghana",
    "ET": "Ethiopia",

    # Western Europe additional (7 countries)
    "SP": "Spain",
    "IT": "Italy",
    "PO": "Portugal",
    "BE": "Belgium",
    "AU": "Austria",
    "EI": "Ireland",
    "GR": "Greece",
}

# CAMEO event root codes for democracy-relevant events
# See: https://www.gdeltproject.org/data/lookups/CAMEO.eventcodes.txt
# EventRootCode is column 28, values 1-20
DEMOCRACY_EVENT_ROOT_CODES = {
    # Cooperation events (democracy-relevant)
    1: "Make public statement",
    2: "Appeal",
    8: "Yield",
    9: "Investigate",

    # Conflict events (protests, threats, violence)
    10: "Demand",
    11: "Disapprove",
    12: "Reject",
    13: "Threaten",
    14: "Protest",
    15: "Exhibit force posture",
    16: "Reduce relations",
    17: "Coerce",
    18: "Assault",
    19: "Fight",
    20: "Engage in unconventional mass violence",
}

# Number of days to fetch (GDELT files are available for last ~18 months)
DAYS_BACK = int(os.getenv("GDELT_DAYS_BACK", "7"))  # Default to last 7 days


def get_latest_gdelt_files():
    """Get URLs for recent GDELT event files (15-minute updates)."""
    print("[INFO] Fetching GDELT file list...")

    # Get the last update file which lists most recent files
    try:
        response = requests.get(GDELT_LAST_UPDATE_URL, timeout=30)
        if response.status_code != 200:
            print(f"[ERROR] Could not fetch GDELT update list")
            return []

        # Parse last update file (format: size md5 url)
        lines = response.text.strip().split('\n')
        files = []

        for line in lines:
            parts = line.split()
            if len(parts) >= 3 and 'export.CSV.zip' in parts[2]:
                url = parts[2]
                # Extract timestamp from URL
                filename = url.split('/')[-1]
                timestamp = filename.replace('.export.CSV.zip', '')
                files.append((timestamp, url))

        print(f"[INFO] Found latest GDELT file: {files[0][1] if files else 'None'}")

        # For now, just use the single most recent file
        # (fetching multiple 15-min files would be hundreds of files for 7 days)
        return files[:1] if files else []

    except Exception as e:
        print(f"[ERROR] Failed to get GDELT file list: {e}")
        return []


def download_and_parse_gdelt_file(file_url):
    """Download and parse a GDELT CSV file."""
    try:
        print(f"[INFO] Downloading: {file_url}")
        response = requests.get(file_url, timeout=120)

        if response.status_code != 200:
            print(f"[WARNING] File not found: {file_url}")
            return None

        # GDELT files are zipped
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content) as zf:
            # Get first file in zip
            filename = zf.namelist()[0]
            with zf.open(filename) as f:
                # GDELT uses tab-delimited format
                # Column names: http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
                df = pd.read_csv(
                    f,
                    sep='\t',
                    header=None,
                    low_memory=False,
                    names=[
                        'GLOBALEVENTID', 'SQLDATE', 'MonthYear', 'Year', 'FractionDate',
                        'Actor1Code', 'Actor1Name', 'Actor1CountryCode', 'Actor1KnownGroupCode',
                        'Actor1EthnicCode', 'Actor1Religion1Code', 'Actor1Religion2Code',
                        'Actor1Type1Code', 'Actor1Type2Code', 'Actor1Type3Code',
                        'Actor2Code', 'Actor2Name', 'Actor2CountryCode', 'Actor2KnownGroupCode',
                        'Actor2EthnicCode', 'Actor2Religion1Code', 'Actor2Religion2Code',
                        'Actor2Type1Code', 'Actor2Type2Code', 'Actor2Type3Code',
                        'IsRootEvent', 'EventCode', 'EventBaseCode', 'EventRootCode',
                        'QuadClass', 'GoldsteinScale', 'NumMentions', 'NumSources', 'NumArticles',
                        'AvgTone', 'Actor1Geo_Type', 'Actor1Geo_FullName', 'Actor1Geo_CountryCode',
                        'Actor1Geo_ADM1Code', 'Actor1Geo_ADM2Code', 'Actor1Geo_Lat', 'Actor1Geo_Long', 'Actor1Geo_FeatureID',
                        'Actor2Geo_Type', 'Actor2Geo_FullName', 'Actor2Geo_CountryCode',
                        'Actor2Geo_ADM1Code', 'Actor2Geo_ADM2Code', 'Actor2Geo_Lat', 'Actor2Geo_Long', 'Actor2Geo_FeatureID',
                        'ActionGeo_Type', 'ActionGeo_FullName', 'ActionGeo_CountryCode',
                        'ActionGeo_ADM1Code', 'ActionGeo_ADM2Code', 'ActionGeo_Lat', 'ActionGeo_Long', 'ActionGeo_FeatureID',
                        'DATEADDED', 'SOURCEURL'
                    ]
                )

                print(f"[SUCCESS] Parsed {len(df)} events from file")
                return df

    except Exception as e:
        print(f"[WARNING] Error downloading/parsing {file_url}: {e}")
        return None


def filter_gdelt_events(df):
    """Filter GDELT events to democracy-relevant events in tracked countries."""
    if df is None or df.empty:
        return pd.DataFrame()

    print(f"[INFO] Filtering events...")

    # Filter by country
    country_mask = df['ActionGeo_CountryCode'].isin(COUNTRY_CODES.keys())
    df_filtered = df[country_mask].copy()
    print(f"[INFO] After country filter: {len(df_filtered)} events")

    # Filter by event type (democracy-relevant)
    # EventRootCode is already a single digit (1-20) in the data
    event_mask = df_filtered['EventRootCode'].isin(DEMOCRACY_EVENT_ROOT_CODES.keys())
    df_filtered = df_filtered[event_mask].copy()
    print(f"[INFO] After event type filter: {len(df_filtered)} events")

    return df_filtered


def transform_gdelt_event(row, country_cache):
    """Transform GDELT event to our database schema."""

    # Get country code and map to name
    country_code = row.get('ActionGeo_CountryCode', '')
    country_name = COUNTRY_CODES.get(country_code)

    if not country_name or country_name not in country_cache:
        return None

    country_id = country_cache[country_name]

    # Get event type from EventRootCode (single digit 1-20)
    event_root_code = int(row.get('EventRootCode', 0))
    event_type = DEMOCRACY_EVENT_ROOT_CODES.get(event_root_code, "Unknown")
    event_code = str(row.get('EventCode', ''))

    # Parse date (GDELT format: YYYYMMDD)
    date_str = str(row.get('SQLDATE', ''))
    try:
        # Handle case where SQLDATE might be a float (pandas issue)
        if '.' in date_str:
            # If it's a float, try to convert to int first
            date_str = str(int(float(date_str)))
        event_date = datetime.strptime(date_str, '%Y%m%d').date()
    except:
        return None

    # Build event record
    try:
        transformed = {
            "event_id": f"GDELT-{row.get('GLOBALEVENTID', '')}",
            "country_id": country_id,
            "event_date": event_date,
            "event_type": event_type,
            "sub_event_type": f"CAMEO {event_root_code}",
            "disorder_type": "Political event",
            "actor1": row.get('Actor1Name'),
            "actor2": row.get('Actor2Name'),
            "fatalities": 0,  # GDELT doesn't directly track fatalities
            "notes": f"Goldstein Scale: {row.get('GoldsteinScale', 'N/A')}, Tone: {row.get('AvgTone', 'N/A')}, Mentions: {row.get('NumMentions', 0)}",
            "location_name": row.get('ActionGeo_FullName'),
            "admin1": None,
            "admin2": None,
            "admin3": None,
            "latitude": float(row.get('ActionGeo_Lat')) if pd.notna(row.get('ActionGeo_Lat')) else None,
            "longitude": float(row.get('ActionGeo_Long')) if pd.notna(row.get('ActionGeo_Long')) else None,
            "source": "GDELT",
            "source_url": row.get('SOURCEURL'),
        }

        return transformed

    except Exception as e:
        print(f"[WARNING] Error transforming GDELT event: {e}")
        return None


# Main execution
print("=" * 60)
print("GDELT ETL - Democracy Events Loader")
print("=" * 60)
print(f"Fetching last {DAYS_BACK} days of events")

try:
    # Get list of files to download
    files = get_latest_gdelt_files()

    all_events = []

    # Download and parse each file
    for date_str, file_url in files:
        df = download_and_parse_gdelt_file(file_url)
        if df is not None and not df.empty:
            # Filter to relevant events
            df_filtered = filter_gdelt_events(df)
            if not df_filtered.empty:
                all_events.append(df_filtered)

    if not all_events:
        print("\n[WARNING] No GDELT events found")
        exit(0)

    # Combine all events
    events_df = pd.concat(all_events, ignore_index=True)
    print(f"\n[SUCCESS] Total events to process: {len(events_df)}")

    # Load into database
    print("\n[INFO] Loading events into database...")
    stats = defaultdict(int)
    errors = []

    with engine.begin() as conn:
        # Build country cache
        country_cache = {}
        result = conn.execute(text("SELECT id, name FROM countries"))
        for row in result:
            country_cache[row.name] = row.id

        print(f"[INFO] Found {len(country_cache)} countries in database")

        # Process each event
        for idx, raw_row in events_df.iterrows():
            try:
                event = transform_gdelt_event(raw_row, country_cache)
                if not event:
                    stats["skipped"] += 1
                    continue

                # Check if exists
                check_result = conn.execute(
                    text("SELECT id FROM events WHERE event_id = :event_id"),
                    {"event_id": event["event_id"]}
                )
                existing = check_result.fetchone()

                if existing:
                    stats["updated"] += 1
                else:
                    # Insert new event
                    conn.execute(
                        text("""
                            INSERT INTO events (
                                event_id, country_id, event_date, event_type,
                                sub_event_type, disorder_type, actor1, actor2,
                                fatalities, notes, location_name, admin1, admin2,
                                admin3, latitude, longitude, source, source_url
                            ) VALUES (
                                :event_id, :country_id, :event_date, :event_type,
                                :sub_event_type, :disorder_type, :actor1, :actor2,
                                :fatalities, :notes, :location_name, :admin1, :admin2,
                                :admin3, :latitude, :longitude, :source, :source_url
                            )
                        """),
                        event
                    )
                    stats["inserted"] += 1

            except Exception as e:
                errors.append(f"Event {idx}: {str(e)}")
                stats["errors"] += 1

        print("[SUCCESS] Transaction committed")

    # Print summary
    print("\n" + "=" * 60)
    print("ETL Summary")
    print("=" * 60)
    print(f"  Inserted: {stats['inserted']}")
    print(f"  Updated:  {stats['updated']}")
    print(f"  Skipped:  {stats['skipped']}")
    print(f"  Errors:   {stats['errors']}")

    if stats["inserted"] > 0 or stats["updated"] > 0:
        print("\n[SUCCESS] GDELT ETL completed successfully")
    else:
        print("\n[WARNING] No data was inserted or updated")

except Exception as e:
    print(f"\n[ERROR] ETL failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("=" * 60)
