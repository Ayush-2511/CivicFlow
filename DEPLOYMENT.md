# CivicFlow Deployment Guide

CivicFlow is built as a unified, production-ready application. When deployed, FastAPI automatically serves the compiled React frontend, REST endpoints, and Edge-TTS audio streams from a single unified port, eliminating CORS issues.

---

## Pre-Deployment Checklist

Before deploying, ensure you have:
1. **Groq API Key**: Obtain a free key from [console.groq.com/keys](https://console.groq.com/keys).
2. **GitHub Repository**: Push your code to GitHub:
   ```bash
   git add .
   git commit -m "feat: prepare production deployment configuration"
   git push origin main
   ```

---

## Option 1: Render.com (Recommended — 100% Free & Easiest)

Render automatically detects the multi-stage [Dockerfile](file:///d:/Ayushh/Antigravity/CivicFlow/Dockerfile), builds the frontend, and runs the FastAPI backend on one free web service.

### Step-by-Step:
1. Go to **[dashboard.render.com](https://dashboard.render.com/)** and sign in with GitHub.
2. Click **New +** → **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your `CivicFlow` repository.
4. Fill in the service details:
   - **Name**: `civicflow` (or your choice)
   - **Region**: Oregon (US West) or Frankfurt (EU)
   - **Environment / Runtime**: **Docker** (Render automatically picks up `Dockerfile`)
   - **Instance Type**: **Free**
5. Under **Environment Variables**, click **Add Environment Variable**:
   | Key | Value | Notes |
   |---|---|---|
   | `GROQ_API_KEY` | `gsk_...` | *Your Groq API key* |
   | `GROQ_MODEL_FAST` | `qwen/qwen3.8-27b` | Fast inference model |
   | `GROQ_MODEL_STRONG` | `openai/gpt-oss-120b` | Structured reasoning model |
   | `APP_ENV` | `production` | Production mode |
6. Click **Create Web Service**.
7. In ~2 minutes, your live URL will be ready:
   `https://civicflow.onrender.com`

---

## Option 2: Railway.app (Ultra-Fast 60-Second Deploy)

1. Go to **[railway.com](https://railway.com/)** and log in with GitHub.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select your `CivicFlow` repository.
4. Click **Add Variables** and configure:
   - `GROQ_API_KEY`: `gsk_...`
   - `GROQ_MODEL_FAST`: `qwen/qwen3.8-27b`
   - `GROQ_MODEL_STRONG`: `openai/gpt-oss-120b`
5. Go to **Settings** → **Networking** → Click **Generate Domain**.
6. Railway builds the Docker image and gives you a public `.up.railway.app` URL.

---

## Option 3: Docker & Self-Hosted VPS (AWS, GCP, DigitalOcean, Hetzner)

If you have a Linux VPS or want to run a local production container:

### Using Docker Compose:
```bash
# 1. Clone repository
git clone https://github.com/<your-username>/CivicFlow.git
cd CivicFlow

# 2. Configure .env with your Groq key
cp .env.example .env
# Edit .env and paste your GROQ_API_KEY

# 3. Start the container in background
docker compose up -d --build
```
Your service will be live at `http://localhost:8000` (or `http://<your-vps-ip>:8000`).

---

## Option 4: Split Deployment (Vercel Frontend + Render Backend)

If you prefer hosting the React app on **Vercel** and the backend on **Render/Railway**:

### 1. Deploy Backend to Render:
- Set up a Python Web Service on Render running:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- Note your backend URL (e.g., `https://civicflow-api.onrender.com`).

### 2. Deploy Frontend to Vercel:
- In Vercel, import the `frontend/` directory of your repo.
- Framework Preset: **Vite**
- In `frontend/vite.config.ts`, ensure proxy points to your live backend URL, or deploy with environment variable:
  - `VITE_API_BASE_URL` = `https://civicflow-api.onrender.com`

---

## Verifying Your Live Deployment

Once deployed, test your live instance:
1. **Health Check**: Open `https://<your-deployed-url>/health`
   - Expected: `{"status": "healthy", "service": "CivicFlow", "environment": "production"}`
2. **Interactive UI**: Open `https://<your-deployed-url>/`
   - Verify the modern CivicFlow dashboard loads.
   - Click one of the verified demo policy sources (e.g., *PM-KISAN Operational Guidelines*).
   - Verify the live extraction progress counter, clause citations, and audio player function properly.

