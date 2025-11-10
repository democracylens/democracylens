# Democracy Lens - Real-Time Data Implementation Handoff

## Project Context
Democracy Lens is a non-partisan democracy tracking dashboard. We're adding real-time event data (protests, riots, political violence) to complement existing annual democracy indices (Freedom House, World Bank WGI).

---

## What's Been Accomplished ✅

### 1. Database Infrastructure (COMPLETE)
- **Events table created** with full schema for event data
- **Migration applied** successfully: `migrations/001_add_events_table.sql`
- **Country list expanded** from 15 to 50 countries
- **Migration applied**: `migrations/002_expand_countries.sql`
- Database now has 50 countries covering all regions

**Verify:**
```bash
py verify_migration.py
# Should show: Events table exists with 0 events
```

### 2. Data Sources Implemented

#### A. ACLED (Blocked - API Tier Issue)
- **File:** `etl/load_acled.py`
- **Status:** Code complete, but BLOCKED
- **Issue:** Free "Open myACLED" tier doesn't have API access
- **Solution needed:** Request Research tier access (free for non-commercial)
- **Email to send:** data@acleddata.com
- **Account:** democracylens@proton.me / c@fu56LsLyZ7KZ*

**Next steps for ACLED:**
1. Email ACLED requesting Research tier trial
2. Or manually download CSV from https://acleddata.com/data-export-tool/
3. Use `etl/load_acled_csv.py` to import manual downloads

#### B. GDELT (Implemented, Debugging Required)
- **File:** `etl/load_gdelt.py`
- **Status:** 90% complete, inserting 0 events
- **Issue:** Events are filtered and transformed, but all get skipped during insert
- **Progress:** Successfully fetching 13 events from latest GDELT file

**Current behavior:**
```
[INFO] After country filter: 93 events
[INFO] After event type filter: 13 events
[SUCCESS] Total events to process: 13
...
Inserted: 0
Updated: 0
Skipped: 13  ← ALL EVENTS SKIPPED
```

**Debugging needed:**
- Events pass all filters
- Country mapping appears correct (50 countries now in DB)
- `transform_gdelt_event()` returns None for all events
- Need to debug why transformation fails

**Debug command:**
```bash
py etl/load_gdelt.py
# Look for [DEBUG] lines showing why events are skipped
```

### 3. Dashboard Updated (COMPLETE)
- **File:** `app.py`
- **"Democracy Pulse" section added** (lines 123-221)
- Displays recent events (30/90 day toggle)
- Event metrics, timeline, expandable details
- Gracefully handles empty state

---

## Current Blocker 🚧

**GDELT events not inserting into database**

All 13 events are being skipped. The `transform_gdelt_event()` function is returning `None` for every event.

**Possible causes:**
1. **Country name mismatch** - COUNTRY_CODES maps to wrong names
2. **Date parsing failure** - GDELT date format issue
3. **Missing required field** - event_id, latitude, or other field is invalid

**Files to investigate:**
- `etl/load_gdelt.py` lines 187-230 (transform_gdelt_event function)
- Specifically line 193: `if not country_name or country_name not in country_cache:`

---

## Next Steps (Priority Order)

### 🔥 IMMEDIATE: Fix GDELT Event Insertion

**Step 1: Add detailed debug logging**
```python
# In transform_gdelt_event() function, add after line 191:
print(f"[DEBUG] Country: code={country_code}, name={country_name}, in_cache={country_name in country_cache}")
print(f"[DEBUG] Date: {date_str}, EventRoot: {event_root_code}, EventID: {row.get('GLOBALEVENTID')}")
```

**Step 2: Run and analyze**
```bash
py etl/load_gdelt.py
```

**Step 3: Fix the issue**
Likely fixes:
- Country name mismatch → Update COUNTRY_CODES mapping
- Date parsing → Check GDELT date format (should be YYYYMMDD)
- Event ID format → Verify GLOBALEVENTID exists

**Step 4: Verify success**
```bash
py etl/load_gdelt.py
# Should see: Inserted: 13 (or similar)

py verify_migration.py
# Should show: Events table exists with 13 events
```

### 🎯 THEN: Test Dashboard

```bash
streamlit run app.py
```

Navigate to a country (try United States, United Kingdom, or India - high activity countries).

Scroll down to "Democracy Pulse" section - should show events!

### 📧 PARALLEL: Request ACLED Research Tier

**Email template:**
```
To: data@acleddata.com
Subject: Research Tier Trial Request for Democracy Data Project

Hi ACLED Team,

I'm working on a non-commercial democracy tracking project called
"Democracy Lens" that visualizes democracy indicators for public
civic awareness.

I've created an Open myACLED account (democracylens@proton.me) and
would like to request a Research tier trial to access event-level
data via API for 50 countries.

Project details:
- Public dashboard tracking democracy metrics
- Non-partisan, factual data presentation
- Combining ACLED events with Freedom House/World Bank indices
- Weekly API calls for recent protest/riot data

Could you please review my request for Research tier access?

Thank you,
[Your name]
```

### 🚀 THEN: Finalize Deployment

1. **Update GitHub Actions secrets:**
   - Go to repository Settings → Secrets
   - Add: `ACLED_EMAIL`, `ACLED_PASSWORD` (if Research tier approved)

2. **Update documentation:**
   - Mark GDELT as primary data source in README
   - Update footer in `app.py` to mention GDELT

3. **Test weekly automation:**
   - Manually trigger GitHub Actions workflow
   - Verify events load correctly

---

## Key Files Reference

### Database
- **Schema:** `schema.sql` (events table lines 19-50)
- **Migrations:** `migrations/001_add_events_table.sql`, `migrations/002_expand_countries.sql`
- **Migration tool:** `migrations/apply_migration.py`

### ETL Scripts
- **GDELT (primary):** `etl/load_gdelt.py` ← FIX THIS FIRST
- **ACLED API:** `etl/load_acled.py` (blocked on tier)
- **ACLED CSV:** `etl/load_acled_csv.py` (manual import)
- **Documentation:** `etl/README.md`

### Dashboard
- **Main app:** `app.py` (Democracy Pulse: lines 123-221)

### Configuration
- **Environment:** `.env` (has ACLED credentials)
- **Example:** `.env.example` (updated with ACLED vars)

### Documentation
- **Implementation guide:** `IMPLEMENTATION_SUMMARY.md`
- **Deployment status:** `DEPLOYMENT_STATUS.md`
- **This handoff:** `HANDOFF.md`

---

## Database State

**Current countries (50 total):**
- Original 15: US, UK, Germany, France, Japan, Canada, Australia, South Korea, Denmark, Finland, Norway, Sweden, Switzerland, Netherlands, New Zealand
- Latin America (7): Brazil, Mexico, Argentina, Chile, Colombia, Peru, Venezuela
- Asia-Pacific (7): India, Indonesia, Philippines, Thailand, Malaysia, Taiwan, Singapore
- Eastern Europe (5): Poland, Czech Republic, Hungary, Romania, Ukraine
- MENA (4): Israel, Turkey, Tunisia, Egypt
- Africa (5): South Africa, Nigeria, Kenya, Ghana, Ethiopia
- Western Europe (7): Spain, Italy, Portugal, Belgium, Austria, Ireland, Greece

**Query to verify:**
```sql
SELECT COUNT(*) FROM countries;  -- Should return 50
SELECT COUNT(*) FROM events;     -- Currently 0, should have data after fix
```

---

## Environment Variables

```bash
# Database (already configured)
DB_HOST=ep-odd-boat-ahc72i13.c-3.us-east-1.aws.neon.tech
DB_PORT=5432
DB_NAME=neondb
DB_USER=neondb_owner
DB_ADMIN_USER=neondb_owner

# ACLED (configured but tier-blocked)
ACLED_EMAIL=democracylens@proton.me
ACLED_PASSWORD=c@fu56LsLyZ7KZ*
ACLED_DAYS_BACK=90

# GDELT (no config needed - public data)
GDELT_DAYS_BACK=7
```

---

## Testing Commands

```bash
# Verify database
py verify_migration.py

# Test GDELT (needs fixing)
py etl/load_gdelt.py

# Test ACLED CSV import (manual)
# First download CSV from https://acleddata.com/data-export-tool/
# Save to: etl/data/acled_export.csv
py etl/load_acled_csv.py

# Test dashboard
streamlit run app.py
```

---

## Success Criteria

✅ GDELT ETL inserts events into database (not just skipping)
✅ `py verify_migration.py` shows > 0 events
✅ Dashboard "Democracy Pulse" section displays events
✅ Events visible for high-activity countries (US, India, Brazil, Turkey)
✅ Weekly GitHub Actions workflow configured and tested

---

## Known Issues

1. **GDELT transform returning None** - All events skipped, needs debugging
2. **ACLED API 403** - Free tier doesn't have API access, needs Research tier or manual CSV
3. **System date is Nov 9, 2025** - Some GDELT files might not exist for future dates (use latest available)

---

## Quick Start for New Session

```bash
# 1. Check current state
py verify_migration.py

# 2. Debug GDELT
py etl/load_gdelt.py

# 3. If GDELT works, test dashboard
streamlit run app.py

# 4. Verify events appear in dashboard
# Navigate to: United States → scroll to Democracy Pulse
```

---

## Questions to Answer

1. Why is `transform_gdelt_event()` returning None for all events?
2. Are country names in COUNTRY_CODES exact matches to database?
3. Is GDELT date format parsing correctly?
4. Should we prioritize ACLED Research tier request or stick with GDELT?

---

## Contact & Credentials

**ACLED Account:**
- Email: democracylens@proton.me
- Password: c@fu56LsLyZ7KZ*
- Tier: Open myACLED (free, no API access)
- Upgrade needed: Research tier (email data@acleddata.com)

**Database:**
- Provider: Neon PostgreSQL
- Tier: Free (512MB)
- Status: Healthy, migrations applied

---

**Last updated:** November 9, 2025
**Status:** GDELT implementation 90% complete, needs debugging on transform/insert
**Blocker:** All GDELT events being skipped during database insert
**Next action:** Debug `transform_gdelt_event()` function to fix None returns
