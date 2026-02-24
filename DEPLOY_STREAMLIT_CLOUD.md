# Deploy DinDin Quant Bot to Streamlit Cloud

Your dashboard can run **in the cloud** instead of localhost. After deployment:
- Access from any device (phone, laptop, tablet)
- No need to keep your computer on
- Data fetched live from yfinance (US & Taiwan stocks)
- Auto-updates when you push to GitHub

---

## Prerequisites

1. **GitHub account** – [Sign up](https://github.com/join) if needed
2. **Code on GitHub** – Push your project first

---

## Step 1: Push to GitHub (if not already)

```bash
cd /Users/dindin/Desktop/DinDin_Quant_Bot

# If new repo
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/DinDin_Quant_Bot.git
git push -u origin main

# If already on GitHub, just push latest
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push
```

> **Important:** Ensure `data/us_stocks.yaml` and `data/taiwan_stocks.yaml` are committed. The `data/database/` folder is gitignored (OK – the app fetches from yfinance when empty).

---

## Step 2: Deploy on Streamlit Community Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io)**
2. Click **Sign in with GitHub** and authorize
3. Click **"New app"** (or **"Create app"**)
4. Fill in:
   - **Repository:** `YOUR_USERNAME/DinDin_Quant_Bot`
   - **Branch:** `main`
   - **Main file path:** `src/presentation/dashboard/app.py`
5. (Optional) Set a **custom subdomain**, e.g. `dindin-quant-bot`
6. Click **Deploy**

---

## Step 3: Wait for Build

- First deploy can take **3–8 minutes** (installing dependencies)
- You can follow progress in the logs on the right
- When it finishes, you’ll get a URL like:  
  `https://YOUR_APP.streamlit.app`

---

## Step 4: Use Your Cloud Dashboard

- Open the URL in any browser
- Select Taiwan or US market
- Pick a stock – data comes from yfinance on demand
- No local database needed; each session fetches fresh data

---

## Optional: Secrets (Shioaji for Taiwan)

If you want **Shioaji** for Taiwan stock updates on the cloud:

1. In Streamlit Cloud → your app → **Settings**
2. Open **Secrets**
3. Add in TOML format:

```toml
SHIOAJI_API_KEY = "your-api-key"
SHIOAJI_SECRET_KEY = "your-secret-key"
SHIOAJI_PERSON_ID = "your-person-id"
SHIOAJI_SIMULATION = "true"
```

The dashboard works without Shioaji – yfinance provides data for both markets.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check logs; ensure `requirements.txt` has valid deps |
| "Module not found" | Confirm main file path is `src/presentation/dashboard/app.py` |
| Empty stock list | First load may be slow; ensure `data/*.yaml` are committed |
| Timeout | Streamlit Cloud has usage limits; restart the app if needed |

---

## Limits (Free Tier)

- 1 GB RAM per app
- Apps sleep after ~24 hours of inactivity (wake on next visit)
- Good for monitoring and backtesting

---

## Summary

| Before (localhost) | After (Streamlit Cloud) |
|-------------------|------------------------|
| Computer must stay on | Works from anywhere |
| Need internet on your Mac | Runs in the cloud |
| Only you can access | Shareable URL |

**Deploy URL:** [share.streamlit.io](https://share.streamlit.io)
