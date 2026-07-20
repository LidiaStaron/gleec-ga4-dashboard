# GA4 Live Dashboard

Pulls GA4 metrics on a schedule via GitHub Actions and displays them on a
GitHub Pages site — no login required for viewers.

## One-time setup

1. **Create the repo on GitHub** (if you haven't already) and push these files to it.

2. **Add two repository secrets**
   Repo → Settings → Secrets and variables → Actions → New repository secret

   - `GA4_SERVICE_ACCOUNT_KEY` — paste the **entire contents** of your service
     account JSON key file (the one downloaded from Google Cloud Console).
   - `GA4_PROPERTY_ID` — the numeric GA4 property ID you want to track
     (e.g. `435670861` for "Gleec Coin - GA4"). Find this in GA4 → Admin →
     Property details.

3. **Enable GitHub Pages**
   Repo → Settings → Pages → Source: **Deploy from a branch** → Branch: `main`
   → folder: `/ (root)` → Save.

   GitHub will give you a URL like:
   `https://YOUR_USERNAME.github.io/YOUR_REPO/`

   That's the link to share with your manager.

4. **Trigger the first run manually**
   Repo → Actions tab → "Update GA4 Dashboard" → Run workflow.
   After it finishes (~30 seconds), refresh the Pages URL — you should see
   real data.

## After that

The Action re-runs automatically every hour (see the `cron` schedule in
`.github/workflows/update-dashboard.yml` — edit that line to change the
frequency). Each run fetches fresh GA4 data and commits it to `data/latest.json`,
which the dashboard page reads on every page load.

## Local testing (optional)

```bash
export GOOGLE_APPLICATION_CREDS="/path/to/service-account.json"
export GA4_PROPERTY_ID="435670861"
pip install -r requirements.txt
python fetch_ga4_data.py
```

Then open `index.html` in a browser (or run `python -m http.server` and visit
`localhost:8000`) to preview it with real data before pushing.
