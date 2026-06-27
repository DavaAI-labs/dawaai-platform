# DavaAI — Production Deployment Guide
## Supporting 100+ Pharmacies

This guide deploys DavaAI so that **any number of shopkeepers can register and use it independently** — each pharmacy gets its own isolated data, inventory, and billing.

---

## Architecture Overview

```
[Shopkeeper's browser]
        │
        ▼
[Frontend — Vercel / Netlify]     ← React app, free CDN hosting
        │ HTTPS
        ▼
[Backend — Railway / Render]      ← FastAPI, OCR, AI matching
        │ REST API
        ▼
[Supabase — PostgreSQL + Auth]    ← All data, isolated per pharmacy
        │
        ▼
[Google Vision + Claude AI]       ← Prescription reading (per-scan cost)
```

**Multi-tenancy:** Every pharmacy registers with their own account. Row-Level Security in Supabase ensures Pharmacy A can **never** see Pharmacy B's data.

---

## Step 1 — Supabase Setup (5 min, free)

1. Go to https://supabase.com → **New project**
2. Choose a region close to India (e.g. `ap-south-1` Mumbai)
3. **SQL Editor → New query** → paste the contents of `supabase/schema.sql` → **Run**
4. Go to **Authentication → Email** → turn OFF "Confirm email" for easier onboarding (or leave ON for security)
5. Go to **Settings → API** and copy:

| Value | Used in |
|-------|---------|
| Project URL | `SUPABASE_URL` (backend) + `REACT_APP_SUPABASE_URL` (frontend) |
| `anon` public key | `REACT_APP_SUPABASE_ANON_KEY` (frontend only) |
| `service_role` key | `SUPABASE_SERVICE_KEY` (backend only — keep secret!) |

---

## Step 2 — Deploy Backend (Railway — recommended)

Railway gives you a free-ish tier and auto-deploys from GitHub.

### 2a. Push to GitHub
```bash
git init
git add .
git commit -m "DavaAI production"
git remote add origin https://github.com/YOUR_USERNAME/dawaai
git push -u origin main
```

### 2b. Railway deployment
1. Go to https://railway.app → **New Project → Deploy from GitHub**
2. Select your repo → Railway auto-detects the Dockerfile ✅
3. Go to **Variables** tab → add these:

```
SUPABASE_URL              = https://xxxx.supabase.co
SUPABASE_SERVICE_KEY      = eyJ...  (service_role key)
GOOGLE_VISION_API_KEY     = AIza...
ANTHROPIC_API_KEY         = sk-ant-...
ALLOWED_ORIGINS           = https://your-frontend.vercel.app
```

4. Click **Deploy** → Railway gives you a URL like `https://dawaai-backend-production.up.railway.app`
5. Test: open `https://your-backend.railway.app/health` → should return `{"status":"ok"}`

### Alternative: Render.com
1. Go to https://render.com → **New Web Service → Connect GitHub**
2. Set **Build Command:** `pip install -r backend/requirements.txt`
3. Set **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add the same environment variables as above
5. Free tier sleeps after 15min inactivity — upgrade to $7/mo Starter to avoid cold starts

---

## Step 3 — Deploy Frontend (Vercel — recommended)

1. Go to https://vercel.com → **Add New Project → Import from GitHub**
2. Set **Root Directory** to `frontend`
3. Set **Framework Preset** to `Create React App`
4. Add environment variables:

```
REACT_APP_SUPABASE_URL      = https://xxxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY = eyJ...  (anon/public key)
REACT_APP_API_URL           = https://your-backend.railway.app/api
```

5. Click **Deploy** → get URL like `https://dawaai.vercel.app`
6. Go back to Railway → update `ALLOWED_ORIGINS` to this Vercel URL

---

## Step 4 — Test End-to-End

1. Open your Vercel URL
2. Click **Register Pharmacy** → fill in pharmacy details → create account
3. Login → go to **Inventory** → add a medicine
4. Go to **Scan** → upload a prescription photo → verify OCR works
5. Go to **Barcode** → scan a barcode → verify lookup works

---

## Step 5 — Get API Keys

### Google Vision API (for prescription OCR)
1. Go to https://console.cloud.google.com
2. Create a project → **APIs & Services → Enable APIs**
3. Search for "Cloud Vision API" → Enable
4. **Credentials → Create Credentials → API Key**
5. Restrict key to "Cloud Vision API" only (security best practice)
6. Cost: ~$1.50 per 1,000 prescription scans

### Anthropic API (for AI medicine name correction)
1. Go to https://console.anthropic.com
2. **API Keys → Create Key**
3. Cost: ~$0.001 per prescription scan (very cheap, uses Claude Haiku)

---

## Scaling & Costs (for 100 pharmacies)

| Service | Free Tier | Paid (est. for 100 shops) |
|---------|-----------|--------------------------|
| Supabase | 500MB DB, 50k auth users | Free tier handles 100 shops easily |
| Railway backend | $5/mo hobby | $5–20/mo based on usage |
| Vercel frontend | Unlimited static | Free forever |
| Google Vision | 1,000 units/mo free | $1.50 per 1,000 scans |
| Anthropic Claude | Pay per use | ~$0.001 per scan |

**Estimated total cost for 100 pharmacies doing ~50 scans/day each:**
- Railway: ~$10/mo
- Google Vision: ~$2.25/mo (1,500 scans/day)
- Anthropic: ~$1.50/mo
- **Total: ~$15/mo** ✅

---

## Onboarding Shopkeepers

Send each shopkeeper this:

```
DavaAI — Smart Pharmacy Platform
Website: https://your-app.vercel.app

To get started:
1. Open the website on your phone or computer
2. Click "Register Pharmacy"
3. Fill in your pharmacy name, your name, phone, address, and drug license number
4. Create a login email and password
5. You're in! Start adding your medicines to Inventory.

Support: [your contact]
```

Each pharmacy's data is completely separate — they can only see their own inventory, bills, and scans.

---

## Troubleshooting

**Backend not starting?**
- Check Railway logs → usually a missing env variable
- Make sure `SUPABASE_URL` does not have a trailing slash

**Frontend can't connect to backend?**
- Verify `REACT_APP_API_URL` points to your Railway URL (not localhost)
- Check `ALLOWED_ORIGINS` in Railway includes your Vercel URL exactly

**"Confirm email" blocking registration?**
- Go to Supabase → Authentication → Email → disable "Confirm email"
- Or instruct shopkeepers to check their email first

**OCR returns empty?**
- Google Vision API key might not be set or restricted incorrectly
- Test the key at: https://console.cloud.google.com/apis/api/vision.googleapis.com

**Prescription scan working but no matches?**
- The pharmacy's inventory must have medicines added first
- The fuzzy match runs against *that pharmacy's* inventory only

---

## Security Checklist

- [ ] `service_role` key is ONLY in backend env vars (never in frontend)
- [ ] `ALLOWED_ORIGINS` is set to your exact frontend URL (not `*`)
- [ ] Supabase Row Level Security is enabled (the schema.sql enables it)
- [ ] `.env` is in `.gitignore` (already set up)
- [ ] Google Vision API key is restricted to Vision API only

---

## Local Development

```bash
# 1. Clone and set up environment
cp .env.example .env
# Fill in your .env values

# 2. Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm start
# Opens http://localhost:3000
```

Or with Docker:
```bash
docker-compose up --build
```
