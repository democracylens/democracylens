# Democracy Lens Deployment Checklist

This checklist guides you through deploying Democracy Lens to production.

## Pre-Deployment Setup

### 1. Neon Database Setup

- [x] Create a Neon account at [neon.tech](https://neon.tech) (can use GitHub OAuth)
- [x] Create a new project called "democracylens"
- [x] Choose region: AWS US East 1 (or closest to your target audience)
- [x] Select Postgres version: 17 (latest)
- [x] Disable Neon Auth (not needed for this project)
- [x] Wait for project to provision (~30 seconds)
- [x] In Connection Details, turn OFF "Connection pooling" toggle
- [x] Copy the connection string
- [x] Note down:
  - Host: `ep-odd-boat-ahc72i13.c-3.us-east-1.aws.neon.tech`
  - Database: `neondb`
  - User: `neondb_owner`
  - Port: `5432`
  - Password: (from connection string)

**Why Neon over Supabase**: Neon provides IPv4 support on the free tier, which ensures compatibility with GitHub Actions, Streamlit Cloud, and local IPv4-only networks. Supabase's free tier is IPv6-only, which causes connectivity issues with many cloud platforms.

### 2. Initialize Database

**Using Python Scripts (Works with Neon's IPv4 support)**

- [x] Copy `.env.example` to `.env`
- [x] Fill in Neon database credentials in `.env`:
  - `DB_HOST`: Neon hostname (from connection string)
  - `DB_PORT`: `5432`
  - `DB_NAME`: `neondb` (or your chosen database name)
  - `DB_USER`: `neondb_owner` (from connection string)
  - `DB_PASSWORD`: (from connection string)
  - `DB_ADMIN_USER`: Same as `DB_USER`
  - `DB_ADMIN_PW`: Same as `DB_PASSWORD`
- [x] Run: `python init_db.py` (or apply `schema.sql` manually)
- [x] Verify: Should see 15 countries seeded
- [x] Run: `python etl/load_freedom_house.py`
- [x] Verify: Should see 90-150 metrics inserted/updated

### 3. Test Locally

**Note**: With Neon's IPv4 support, local testing works from any network.

- [x] Run: `streamlit run app.py`
- [x] Open: http://localhost:8501
- [x] Test: Select different countries
- [x] Test: View different metrics
- [x] Verify: Charts display correctly
- [x] Verify: Raw data table shows correct values

## GitHub Setup

### 4. Create GitHub Repository

- [x] Create new repository (use project account, not personal)
- [x] Name: `democracylens`
- [x] Description: "Non-partisan democracy data dashboard"
- [x] Public repository
- [x] Don't initialize with README (we already have one)

### 5. Configure Git Identity

```bash
git config user.name "Democracy Lens Project"
git config user.email "noreply@democracylens.com"
git config commit.template .gitmessage
```

### 6. Push Code to GitHub

```bash
git remote add origin https://github.com/democracylens/democracylens.git
git branch -M main
git push -u origin main
```

### 7. Configure GitHub Secrets

Go to: Repository → Settings → Secrets and variables → Actions

Add these secrets:
- [x] `DB_HOST` - Your Neon hostname (e.g., `ep-xxx-xxx.c-3.us-east-1.aws.neon.tech`)
- [x] `DB_PORT` - `5432`
- [x] `DB_NAME` - `neondb` (or your chosen database name)
- [x] `DB_ADMIN_USER` - `neondb_owner` (from Neon connection string)
- [x] `DB_ADMIN_PW` - Your Neon database password (from connection string)

**Note**: Neon provides IPv4 connectivity, ensuring GitHub Actions can reliably connect from any runner region.

### 8. Verify GitHub Actions

- [x] Go to Actions tab
- [x] Manually trigger "Nightly ETL" workflow
- [x] Verify: Workflow completes successfully
- [x] Check: Logs show data inserted/updated

## Streamlit Cloud Deployment

### 9. Deploy to Streamlit Cloud

- [x] Go to [share.streamlit.io](https://share.streamlit.io)
- [x] Sign in with GitHub (use project account)
- [x] Click "New app"
- [x] Select your repository: `democracylens`
- [x] Main file path: `app.py`
- [x] Click "Advanced settings"
- [x] Set Python version: 3.11

### 10. Configure Streamlit Secrets

In the "Secrets" section, add:

```toml
DB_HOST = "ep-odd-boat-ahc72i13.c-3.us-east-1.aws.neon.tech"
DB_PORT = "5432"
DB_NAME = "neondb"
DB_USER = "neondb_owner"
DB_PASSWORD = "npg_gfA3SlbKezM7"
```

**Note**: Neon's IPv4 support ensures reliable connectivity from Streamlit Cloud's infrastructure.

- [x] Save secrets
- [x] Click "Deploy"
- [x] Wait 2-3 minutes for deployment

### 11. Verify Deployment

- [x] Open the Streamlit URL (e.g., `democracylens.streamlit.app`)
- [x] Test: App loads successfully
- [x] Test: Countries dropdown populates
- [x] Test: Metrics display correctly
- [x] Test: Charts render properly
- [x] Check: Data source attribution shows
- [x] Check: Last updated date shows

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
