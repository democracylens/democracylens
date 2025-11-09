# Democracy Lens Deployment Checklist

This checklist guides you through deploying Democracy Lens to production.

## Pre-Deployment Setup

### 1. Supabase Database Setup

- [x] Create a Supabase account at [supabase.com](https://supabase.com) (use project email, not personal)
- [x] Create a new project called "democracylens"
- [x] Choose region: US East (or closest to your target audience)
- [x] Set a strong database password (save this securely!)
- [x] Wait for project to provision (~2 minutes)
- [x] Go to Settings → Database → Connection string
- [x] Copy the URI connection string
- [x] Note down:
  - Host: `db.mgnvookdlrxklhiczxjw.supabase.co`
  - Database: `postgres`
  - User: `postgres`
  - Port: `6543` (Session Pooler - IPv4 compatible) or `5432` (Direct - IPv6 only)
  - Password: (saved securely)

**IMPORTANT - IPv6 Requirement**: Supabase database connections require IPv6. If your local network is IPv4-only, you won't be able to connect directly from your machine. Use **Option A** (SQL Editor) below instead.

### 2. Initialize Database

**Option A: Using Supabase SQL Editor (Recommended if IPv4-only network)**

- [x] Copy `.env.example` to `.env`
- [x] Fill in Supabase database credentials in `.env`
  - Use `DB_PORT=6543` for Session Pooler (though IPv4 compatibility still requires IPv6 DNS)
- [x] Open Supabase SQL Editor: Settings → SQL Editor → New query
- [x] Run the complete initialization script from `supabase_init.sql`:
  - Creates `countries` and `metrics` tables
  - Creates performance indexes
  - Seeds 15 countries
  - Creates read-only user `app_read`
- [x] Verify: Check query results show 15 countries created
- [x] Run the data loading script from `load_sample_data.sql`:
  - Inserts 150 Freedom House metrics
- [x] Verify: Check query results show metrics loaded successfully

**Option B: Using Python Scripts Locally (Requires IPv6 connectivity)**

- [ ] Copy `.env.example` to `.env`
- [ ] Fill in Supabase database credentials in `.env`
- [ ] Run: `python init_db.py`
- [ ] Verify: Should see 15 countries seeded
- [ ] Run: `python etl/load_freedom_house.py`
- [ ] Verify: Should see 150 metrics inserted

### 3. Test Locally

**Note**: Local testing requires IPv6 connectivity. If you used Option A above (SQL Editor), skip local testing and proceed directly to cloud deployment (Step 9).

- [ ] Run: `streamlit run app.py`
- [ ] Open: http://localhost:8501
- [ ] Test: Select different countries
- [ ] Test: View different metrics
- [ ] Verify: Charts display correctly
- [ ] Verify: Raw data table shows correct values

## GitHub Setup

### 4. Create GitHub Repository

- [ ] Create new repository (use project account, not personal)
- [ ] Name: `democracylens`
- [ ] Description: "Non-partisan democracy data dashboard"
- [ ] Public repository
- [ ] Don't initialize with README (we already have one)

### 5. Configure Git Identity

```bash
git config user.name "Democracy Lens Project"
git config user.email "noreply@democracylens.com"
git config commit.template .gitmessage
```

### 6. Push Code to GitHub

```bash
git remote add origin https://github.com/your-org/democracylens.git
git branch -M main
git push -u origin main
```

### 7. Configure GitHub Secrets

Go to: Repository → Settings → Secrets and variables → Actions

Add these secrets:
- [ ] `DB_HOST` - Your Supabase hostname (e.g., `db.mgnvookdlrxklhiczxjw.supabase.co`)
- [ ] `DB_PORT` - `5432` (GitHub Actions has IPv6, so use Direct connection for better performance)
- [ ] `DB_NAME` - `postgres`
- [ ] `DB_ADMIN_USER` - `postgres`
- [ ] `DB_ADMIN_PW` - Your Supabase database password

**Note**: GitHub Actions runners have IPv6 connectivity, so they can use port `5432` (Direct connection) for better performance.

### 8. Verify GitHub Actions

- [ ] Go to Actions tab
- [ ] Manually trigger "ETL Workflow"
- [ ] Verify: Workflow completes successfully
- [ ] Check: Logs show data inserted/updated

## Streamlit Cloud Deployment

### 9. Deploy to Streamlit Cloud

- [ ] Go to [share.streamlit.io](https://share.streamlit.io)
- [ ] Sign in with GitHub (use project account)
- [ ] Click "New app"
- [ ] Select your repository: `democracylens`
- [ ] Main file path: `app.py`
- [ ] Click "Advanced settings"

### 10. Configure Streamlit Secrets

In the "Secrets" section, add:

```toml
DB_HOST = "db.mgnvookdlrxklhiczxjw.supabase.co"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "app_read"
DB_PASSWORD = "SecureReadOnlyPass2024!"
```

**Note**: Streamlit Cloud has IPv6 connectivity, so use port `5432` (Direct connection) for better performance.

- [ ] Save secrets
- [ ] Click "Deploy"
- [ ] Wait 2-3 minutes for deployment

### 11. Verify Deployment

- [ ] Open the Streamlit URL (e.g., `democracylens.streamlit.app`)
- [ ] Test: App loads successfully
- [ ] Test: Countries dropdown populates
- [ ] Test: Metrics display correctly
- [ ] Test: Charts render properly
- [ ] Check: Footer displays correctly
- [ ] Check: Last updated date shows

## Domain Configuration

### 12. Register Domain (Optional)

- [ ] Register `democracylens.com` with WHOIS privacy enabled
- [ ] Use project email for registration
- [ ] Enable domain privacy/protection
- [ ] Verify: Personal info is hidden in WHOIS lookup

### 13. Connect Custom Domain

In Streamlit Cloud:
- [ ] Go to: App settings → General → Custom domain
- [ ] Add domain: `democracylens.com`
- [ ] Note the CNAME records provided

In your domain registrar:
- [ ] Add CNAME record as instructed by Streamlit
- [ ] Wait for DNS propagation (5-60 minutes)
- [ ] Verify: `democracylens.com` loads the app

### 14. Configure SSL

- [ ] Streamlit automatically provisions SSL certificate
- [ ] Verify: Site loads with `https://`
- [ ] Check: No SSL warnings in browser

## Post-Deployment Verification

### 15. Test All Features

- [ ] Visit: https://democracylens.com
- [ ] Test: All countries load
- [ ] Test: All metrics display
- [ ] Test: Charts are interactive
- [ ] Test: Data table expands
- [ ] Mobile: Test responsive layout
- [ ] Mobile: Check readability

### 16. Monitor ETL Workflow

- [ ] Go to: GitHub Actions
- [ ] Wait for: Next scheduled run (3:17 AM UTC)
- [ ] Verify: Workflow completes successfully
- [ ] Check: No errors in logs
- [ ] Verify: Data updates reflect in app

### 17. Security Verification

- [ ] Verify: App uses read-only database user
- [ ] Check: No credentials in code
- [ ] Check: `.env` file is gitignored
- [ ] Verify: No personal info in commits
- [ ] Check: WHOIS privacy is active (if domain registered)

## Maintenance Setup

### 18. Set Up Monitoring (Optional)

Free monitoring options:
- [ ] GitHub: Enable email notifications for failed Actions
- [ ] Supabase: Monitor database usage in dashboard (Settings → Usage)
- [ ] Streamlit: Check app health in dashboard

### 19. Document Credentials

Store securely (use password manager):
- [ ] Supabase database credentials
- [ ] GitHub repository access
- [ ] Streamlit Cloud login
- [ ] Domain registrar login (if applicable)
- [ ] Project email credentials

### 20. Create Backup Plan

- [ ] Document: How to restore from Supabase backup (automatic daily backups on free tier)
- [ ] Document: How to export data using Supabase SQL Editor
- [ ] Document: How to redeploy app if deleted
- [ ] Document: Emergency contact procedures

## Troubleshooting

### Cannot Connect to Supabase Locally (IPv4/IPv6 Issue)

**Symptoms:**
- `could not translate host name to address` error
- DNS resolution fails for `db.*.supabase.co`
- `ping` to Supabase host fails
- Connection timeout errors

**Root Cause**: Supabase database connections require IPv6. If your local network is IPv4-only, you cannot connect directly.

**Solutions:**
1. **Use Supabase SQL Editor** for database management (recommended)
   - Run `supabase_init.sql` to initialize schema
   - Run `load_sample_data.sql` to load data
   - All database operations can be done via web interface
2. **Deploy to cloud** where IPv6 is available
   - GitHub Actions has IPv6 ✓
   - Streamlit Cloud has IPv6 ✓
3. **Enable IPv6** on your network (if available from ISP)
   - Contact your ISP for IPv6 support
   - Configure router for IPv6
4. **Use IPv6 tunnel service** (advanced)
   - Hurricane Electric Tunnel Broker
   - Other IPv6 tunnel providers

**Testing IPv6 connectivity:**
```bash
# Windows
ping -6 2001:4860:4860::8888

# Check if Supabase host resolves to IPv4
nslookup -type=A db.mgnvookdlrxklhiczxjw.supabase.co
```

### App Won't Load
- Check Streamlit Cloud logs
- Verify database connection string
- Check that secrets are configured correctly
- Verify Supabase project is active (not paused)
- Check Supabase dashboard for any service issues
- Ensure `DB_PORT = "5432"` in Streamlit secrets (not 6543)

### ETL Fails
- Check GitHub Actions logs
- Verify GitHub secrets are set
- Ensure `DB_PORT` is set to `5432` for GitHub Actions (has IPv6)
- Check Supabase database storage (free tier: 500 MB)
- Verify database user has write permissions
- If IPv4-only locally, use Supabase SQL Editor to test queries

### No Data in App
- Use Supabase SQL Editor to check data:
  - `SELECT COUNT(*) FROM countries;` (should show 15)
  - `SELECT COUNT(*) FROM metrics;` (should show 150+)
- Re-run `supabase_init.sql` if tables are missing
- Re-run `load_sample_data.sql` if data is missing
- Check Supabase Table Editor to inspect data visually

### Domain Not Working
- Wait for DNS propagation (up to 48 hours)
- Verify CNAME record is correct
- Check domain registrar settings
- Try clearing DNS cache locally

## Success Criteria

- ✅ App is live at democracylens.com (or Streamlit URL)
- ✅ All countries and metrics display correctly
- ✅ ETL runs automatically every night
- ✅ No personal information is exposed
- ✅ Site loads quickly (< 3 seconds)
- ✅ Mobile-friendly and responsive
- ✅ HTTPS enabled and working

## Next Steps

After successful deployment:

1. **Monitor**: Check app daily for first week
2. **Iterate**: Add more data sources as planned
3. **Share**: Announce on relevant platforms (when ready)
4. **Maintain**: Keep data updated via nightly ETL
5. **Expand**: Add features per roadmap

---

## Lessons Learned

### Session Date: 2025-01-09

**Key Findings:**

1. **IPv6 Requirement is Critical**
   - Supabase database connections require IPv6 DNS resolution
   - Port 6543 (Session Pooler) does NOT solve IPv4-only network issues
   - IPv4-only networks cannot connect to Supabase databases at all
   - Solution: Use Supabase SQL Editor for all local database operations

2. **SQL Editor as Primary Tool**
   - Created `supabase_init.sql` for complete database initialization
   - Created `load_sample_data.sql` for data loading
   - SQL Editor approach works universally, regardless of network configuration
   - Recommend SQL Editor as primary method in documentation

3. **Type Casting in PostgreSQL**
   - Date strings must be explicitly cast with `::DATE` in VALUES clauses
   - UNION queries require consistent types across all branches (use `::text`)
   - PostgreSQL is strict about type matching

4. **Emoji Encoding Issues**
   - Windows console (cp1252) cannot display Unicode emojis in Python scripts
   - Replaced emojis with `[INFO]`, `[SUCCESS]`, `[ERROR]`, `[WARNING]` tags
   - Consider this for cross-platform compatibility

5. **Cloud-First Architecture Works**
   - Local development limitations don't impact cloud deployment
   - GitHub Actions (IPv6) ✓
   - Streamlit Cloud (IPv6) ✓
   - This validates the zero-cost, cloud-first architecture

6. **Environment Configuration**
   - `.env` file created and configured
   - Port 6543 documented but note IPv6 DNS still required
   - Read-only user (`app_read`) successfully created
   - Credentials documented securely

**Completed Setup:**
- ✅ Supabase project created: `democracylens`
- ✅ Database schema initialized via SQL Editor
- ✅ 15 countries seeded
- ✅ Read-only user `app_read` created
- ✅ 150 Freedom House metrics loaded (2015-2024)
- ✅ `.env` file configured with credentials
- ✅ IPv6 limitation documented and workaround provided

**Next Steps:**
- Deploy to Streamlit Cloud (has IPv6)
- Configure GitHub Actions (has IPv6)
- Test end-to-end workflow in cloud environment

---

**Deployment Date**: _____________

**Deployed By**: Democracy Lens Project

**Status**: ⬜ Not Started | 🔄 In Progress (Database Setup Complete) | ⬜ Complete
