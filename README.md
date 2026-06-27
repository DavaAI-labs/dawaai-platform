# DavaAI v3 — Setup Guide

## What's new in v3
- ✅ Multi-pharmacy login (each pharmacy has its own account)
- ✅ Inventory management (stock, expiry, MRP, purchase price, margin, supplier)
- ✅ Two-stage expiry alerts (🔴 < 1 month, 🟡 < 3 months)
- ✅ Low stock alerts per medicine
- ✅ AI-powered prescription transcription (Claude fixes bad handwriting before fuzzy matching)
- ✅ Fuzzy match against YOUR inventory (not a generic list)
- ✅ Supabase backend (scalable PostgreSQL + auth)

---

## Step 1 — Set up Supabase (5 minutes)

1. Go to https://supabase.com → Create account → New project
2. Once created, go to **SQL Editor** → New query
3. Paste the entire contents of `supabase/schema.sql` and click **Run**
4. Go to **Settings → API** and copy:
   - Project URL → `REACT_APP_SUPABASE_URL`
   - `anon` public key → `REACT_APP_SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_KEY` (backend only, keep secret)

---

## Step 2 — Configure environment variables

**Frontend** — create `frontend/.env`:
```
REACT_APP_SUPABASE_URL=https://xxxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJ...
```

**Backend** — create `backend/.env`:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
GOOGLE_VISION_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Step 3 — Run locally

**Backend:**
```powershell
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend (new terminal):**
```powershell
cd frontend
npm install
npm start
```

Open http://localhost:3000 → Register your pharmacy → Start using.

---

## Step 4 — Deploy to Vercel (frontend)

1. Push to GitHub
2. Connect repo to Vercel
3. Set environment variables in Vercel dashboard:
   - `REACT_APP_SUPABASE_URL`
   - `REACT_APP_SUPABASE_ANON_KEY`

**Backend:** Deploy to Railway or Render (free tier):
- Set all backend `.env` variables in the platform dashboard
- Entry point: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## New files in this version

```
frontend/src/
  context/AuthContext.tsx    ← session + pharmacy state for whole app
  pages/AuthPage.tsx         ← login + register (creates pharmacy)
  pages/HomePage.tsx         ← updated with auth header + inventory link
  pages/InventoryPage.tsx    ← full inventory CRUD with alerts
  services/supabase.ts       ← all Supabase queries

backend/
  services/ocr_service.py    ← upgraded: Claude AI handwriting fix
  api/routes.py              ← updated: matches against Supabase inventory

supabase/
  schema.sql                 ← run once in Supabase SQL editor
```

---

## How the upgraded OCR works

**Before (v2):** OCR text → fuzzy match against static CSV

**Now (v3):**
1. Google Vision OCR → raw messy text
2. **Claude AI** reads the raw text and corrects spelling errors, abbreviations, merged words (e.g. "Pantoprozole 40mg Tab OD" → `{corrected_name: "Pantoprazole", strength: "40 mg", frequency: "OD"}`)
3. Fuzzy match corrected name against **your pharmacy's actual inventory**
4. If score ≥ 80 → auto-picked, shown in green
5. If score 55–79 → auto-picked but **flagged for review** (shown in yellow)
6. If score < 55 → no match, chemist types manually

This dramatically improves accuracy for bad handwriting.