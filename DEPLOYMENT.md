# Tesseract Deployment Guide

This guide explains how to deploy Tesseract for production.

---

## Architecture Overview

Tesseract consists of two primary components:

| Component | Technology | Best Hosting Platform | Why |
| :--- | :--- | :--- | :--- |
| **Frontend UI** (`apps/web`) | Next.js 15, React 19, Tailwind CSS | **Vercel** | Native Next.js support, global Edge CDN, instant preview deployments. |
| **Backend API + OCR** (`apps/api`) | FastAPI, Python 3.11, Tesseract OCR, Poppler | **Docker / Railway / Render / Fly.io / VPS** | **Requires OS-level C-binaries** (`tesseract-ocr`, `tesseract-ocr-hin`, `pdftoppm`) and persistent file storage for evidence files. |
| **Database** | PostgreSQL + Neo4j | **Supabase / Neon / Railway / Neo4j AuraDB** | Managed cloud databases. |

> [!NOTE]
> **Why can't the Backend/OCR run directly on Vercel?**
> Vercel Serverless Functions have a read-only filesystem (with an ephemeral `/tmp` that gets cleared), strict 50MB–250MB size caps, and **do not support installing native Linux packages via `apt` (like `tesseract-ocr` and `poppler-utils`)**. Therefore, the backend runs in a Docker container on Render, Railway, Fly.io, or any cloud VPS.

---

## 1. Deploy the Backend (Docker on Railway / Render / Fly.io / VPS)

### Option A: Railway (Recommended — 1-click Docker + PostgreSQL)

1. Go to [railway.app](https://railway.app) and create a new project.
2. Add a **PostgreSQL** database service.
3. Add a **GitHub Repo** service:
   - Select your Tesseract repository.
   - Set **Dockerfile Path** to `Dockerfile` (or `apps/api/Dockerfile`).
   - Set **Environment Variables**:
     ```env
     DATABASE_URL=${{Postgres.DATABASE_URL}}
     JWT_SECRET=your-production-jwt-secret
     DEMO_PASSWORD=your-secure-demo-password
     CORS_ORIGINS=*
     TESSERACT_LANG=eng+hin
     ```
4. Railway will automatically build the container (installing `tesseract-ocr` and `poppler-utils`), apply migrations, and start FastAPI.
5. Generate a domain (e.g. `https://tesseract-api-production.up.railway.app`).

---

### Option B: Render (Web Service + Managed Postgres)

1. Go to [render.com](https://render.com) and create a **PostgreSQL** database. Copy the internal database connection string.
2. Create a new **Web Service**:
   - Connect your GitHub repository.
   - **Environment**: `Docker`
   - **Dockerfile Path**: `./Dockerfile`
   - Set **Environment Variables**:
     ```env
     DATABASE_URL=postgresql+psycopg://... (your Render Postgres connection string)
     JWT_SECRET=your-production-jwt-secret
     DEMO_PASSWORD=your-secure-demo-password
     CORS_ORIGINS=*
     ```
3. Render builds and deploys the container with full OCR and PDF extraction support.
4. Copy the public URL (e.g. `https://tesseract-api.onrender.com`).

---

## 2. Deploy the Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) and click **Add New Project**.
2. Import your GitHub repository.
3. Configure the Project Settings:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click "Edit" and choose `apps/web`.
   - **Build Command**: `next build` (or leave default)
   - **Output Directory**: `.next` (default)
4. Add the Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://your-backend-api.up.railway.app` (the backend URL from Step 1, without trailing slash)
5. Click **Deploy**.

---

## 3. Local Docker Compose Deployment (Self-Hosted / VPS)

To run the entire stack on an Ubuntu VPS or single server:

```bash
# 1. Clone repository
git clone https://github.com/your-org/tesseract.git
cd tesseract

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Start PostgreSQL and Neo4j
docker compose -f infrastructure/docker-compose.yml up -d

# 4. Build and start API
docker build -t tesseract-api .
docker run -d --name tesseract-api --network host \
  -e DATABASE_URL="postgresql+psycopg://tesseract:tesseract@localhost:5433/tesseract" \
  -v $(pwd)/storage/evidence:/app/storage/evidence \
  tesseract-api

# 5. Build and start Web UI
cd apps/web
npm install
npm run build
npm run start
```

---

## Verification & Health Check

1. Backend Health Check:
   ```bash
   curl https://your-backend-api/health
   # Response: {"status":"ok"}
   ```
2. Open your Vercel URL: `https://tesseract.vercel.app`
3. Sign in with Investigator ID: `INV-017` and password: `<DEMO_PASSWORD>`.
4. Upload `Live-Field-Verification.pdf` to test live OCR extraction.
