# Deploying the app

Two ways to use the app on your iPhone.

---

## Option A — Instant: same-Wi-Fi (no deploy, 0 min)

When you run `streamlit run app.py` on your Mac, Streamlit prints a **Network URL**
like `http://192.168.x.x:8501`. If your **iPhone is on the same Wi-Fi**, open that
URL in Safari on the phone — the app works immediately.

👉 Tip: in Safari, tap **Share → Add to Home Screen** to get an app-style icon.

Limitation: only works while your Mac is on and on the same network.

---

## Option B — Anywhere: Streamlit Community Cloud (free, ~10 min)

Gives you a public `https://…streamlit.app` URL that works on any phone, anywhere.

### 1. Put the code on GitHub
- Create a free account at **https://github.com**
- Create a **new repository** (Private is fine) — e.g. `lead-intelligence`
- Push this project to it:
  ```bash
  cd "/Users/thinkitive/Desktop/Lead Generation"
  git remote add origin https://github.com/<your-username>/lead-intelligence.git
  git branch -M main
  git push -u origin main
  ```

### 2. Deploy on Streamlit Cloud
- Go to **https://share.streamlit.io** → sign in with GitHub
- **Create app** → pick your repo → set:
  - **Branch:** `main`
  - **Main file path:** `app.py`
- Click **Deploy**. First build takes a few minutes.

### 3. Add your secrets (so it can pull data)
- In the app page → **⋮ → Settings → Secrets**
- Paste (from `.streamlit/secrets.toml.example`), filling in your real token:
  ```toml
  APIFY_API_TOKEN = "apify_api_xxxxxxxxxxxxx"
  DEFAULT_PROVIDER = "apify_gmaps"
  APP_PASSWORD = "choose-a-password"   # recommended — see below
  ```
- Save. The app restarts automatically.

### 4. (Recommended) Protect it with a password
The public URL is open to anyone who has it — and running a search spends your
Apify credit. Setting **`APP_PASSWORD`** in secrets adds a login gate so only you
can generate leads. Without it, leave `APP_PASSWORD` out and the gate is disabled.

### 5. Use it on your iPhone
Open the `https://…streamlit.app` URL in Safari → **Share → Add to Home Screen**.
Now it launches like a native app.

---

## Notes
- **Secrets are never committed** — `.streamlit/secrets.toml` is gitignored; real
  keys live only in Streamlit Cloud's Secrets panel (or your local `.env`).
- **Switching providers** later (Apify ↔ Google) is just the `DEFAULT_PROVIDER`
  secret — no code change.
- **Cost:** the app itself is free to host. Data costs are only your Apify/Google
  usage, which you control via the "Max results per search" slider.
