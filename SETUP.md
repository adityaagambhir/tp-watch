# PayPal Trustpilot Recovery Tracker — Setup Guide

Live dashboard with daily auto-refresh. No servers, no cost.

---

## How it works

```
GitHub Actions (cron 08:00 UTC daily)
   └─► fetch_scores.py   → scrapes Trustpilot for FR / ES / UK / IT
        └─► commits updated data.json to the repo
             └─► GitHub Pages serves index.html + data.json
                  └─► Your team opens the URL → always fresh data
```

---

## Step 1 — Create a GitHub repository

1. Go to [github.com/new](https://github.com/new)
2. Name it `paypal-trustpilot-tracker` (or anything you like)
3. Set visibility: **Public** (required for free GitHub Pages)  
   _For a private repo, use Vercel — see Option B below._
4. Click **Create repository**

---

## Step 2 — Upload all files

Upload everything in this folder to the root of your new repo:

```
paypal-trustpilot-tracker/
├── index.html
├── data.json
├── fetch_scores.py
├── requirements.txt
└── .github/
    └── workflows/
        └── daily-fetch.yml
```

The easiest way: drag-and-drop all files into the GitHub web UI, or use git:

```bash
git clone https://github.com/YOUR_USERNAME/paypal-trustpilot-tracker
cp -r /path/to/these/files/* paypal-trustpilot-tracker/
cd paypal-trustpilot-tracker
git add .
git commit -m "Initial commit"
git push
```

---

## Step 3 — Enable GitHub Pages

1. In your repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** / root (`/`)
4. Click **Save**

Your dashboard is now live at:
```
https://YOUR_USERNAME.github.io/paypal-trustpilot-tracker/
```
_(takes ~2 minutes to go live the first time)_

---

## Step 4 — Test the fetcher manually

Before waiting for the 8 AM cron, trigger it now:

1. Go to your repo → **Actions** tab
2. Click **Daily Trustpilot Score Fetch** in the left sidebar
3. Click **Run workflow** → **Run workflow** (green button)
4. Watch the logs — you should see ✅ for each locale
5. Refresh your dashboard URL — `data.json` will have today's data

---

## Daily schedule

The cron runs at **08:00 UTC** every day:
- 09:00 CET (winter)  
- 10:00 CEST (summer)

To change the time, edit `.github/workflows/daily-fetch.yml`:
```yaml
- cron: "0 8 * * *"   # ← change 8 to your preferred UTC hour
```

---

## Italy note ⚠️

Italy's Trustpilot page (`paypal.com/it`) is JavaScript-rendered, which means Python's `requests` library may not be able to read it. The script will attempt to fetch it, but if it fails:

1. Manually check [trustpilot.com/review/paypal.com/it](https://www.trustpilot.com/review/paypal.com/it)
2. Edit `data.json` directly in GitHub — add a new entry to `locales.it.data`:
   ```json
   {"date": "2026-05-01", "score": 3.8, "reviews": 14, "reviews_per_day": 1}
   ```
3. Commit the change — GitHub Pages will update automatically

---

## Option B — Private repo via Vercel (free)

If you need a private repository:

1. Push the files to a **private** GitHub repo
2. Go to [vercel.com](https://vercel.com) → **Add New Project**
3. Import your GitHub repo
4. Framework: **Other** (static site)
5. Deploy — Vercel gives you a URL like `https://paypal-trustpilot-tracker.vercel.app`
6. GitHub Actions still handles the daily cron (Actions work on private repos, free tier = 2000 min/month)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Dashboard shows "Could not load data.json" when opened locally | Open via a local server: `python3 -m http.server 8000`, then visit `localhost:8000` |
| GitHub Action fails with 403 | Check that `permissions: contents: write` is in `daily-fetch.yml` |
| Scores not updating | Check Actions logs for HTTP errors; Trustpilot may have changed their page structure |
| Italy always null | Expected — page is JS-rendered, update manually in `data.json` |
