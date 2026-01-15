# Vercel Deployment Guide

## Overview

This application consists of:
- **Frontend**: Next.js app (deployed to Vercel)
- **Backend**: FastAPI app (must be deployed separately)

## Frontend Deployment (Vercel)

### Prerequisites
1. Vercel account
2. GitHub repository connected to Vercel

### Steps

1. **Set Environment Variables in Vercel**:
   - Go to your Vercel project settings
   - Navigate to "Environment Variables"
   - Add: `NEXT_PUBLIC_API_URL` = `https://your-backend-url.com`
   - Make sure to set it for Production, Preview, and Development environments

2. **Deploy**:
   - Push to your main branch (auto-deploys)
   - Or use Vercel CLI: `vercel --prod`

### Configuration Files
- `vercel.json`: Configured for Next.js framework
- `next.config.ts`: Handles API routing (development only)

## Backend Deployment Options

Since Vercel doesn't support long-running FastAPI applications, deploy the backend separately:

### Option 1: Railway (Recommended for Quick Setup)
1. Create account at [railway.app](https://railway.app)
2. Create new project
3. Connect your GitHub repo
4. Add Python service
5. Set root directory to `backend/`
6. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Add environment variables:
   - `SQLALCHEMY_DATABASE_URL` (Railway provides PostgreSQL)
8. Deploy

### Option 2: Render
1. Create account at [render.com](https://render.com)
2. Create new Web Service
3. Connect GitHub repo
4. Settings:
   - Build Command: `cd backend && pip install -r requirements.txt`
   - Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Environment: Python 3
5. Add PostgreSQL database (optional, or use SQLite for testing)
6. Deploy

### Option 3: Fly.io
1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. In `backend/` directory: `fly launch`
3. Follow prompts
4. Deploy: `fly deploy`

### Option 4: DigitalOcean App Platform / AWS / GCP
- Similar setup to above options
- Use containerized deployment with Docker

## Local Development

1. **Start Backend**:
   ```bash
   cd backend
   python -m uvicorn main:app --reload --port 8000
   ```

2. **Start Frontend**:
   ```bash
   npm run dev
   ```

3. **Access**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Troubleshooting

### Build Errors
- Check that all dependencies are in `package.json`
- Ensure TypeScript errors are handled (currently ignored in config)

### API Connection Issues
- Verify `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Check CORS settings in `backend/main.py`
- Ensure backend is accessible from the internet

### Database Issues
- For production, use PostgreSQL instead of SQLite
- Update `SQLALCHEMY_DATABASE_URL` in backend environment
- Run migrations if needed

## Current Status

✅ Frontend builds successfully
✅ Vercel configuration fixed
✅ Backend production-ready with fixes applied
⚠️ Backend needs separate deployment
⚠️ Environment variables need to be configured

## Backend Configuration (Updated)

The backend has been updated with production-ready fixes:
- ✅ Environment variable support
- ✅ PostgreSQL configuration
- ✅ Connection pooling
- ✅ Error handling
- ✅ Health check endpoint
- ✅ CORS configuration

### Required Backend Environment Variables

Set these in your backend deployment platform (Railway, Render, etc.):

```bash
SQLALCHEMY_DATABASE_URL=postgresql://user:password@host:5432/dbname
CORS_ORIGINS=https://your-frontend-domain.vercel.app,https://yourdomain.com
```

See `backend/env.example` for all available options.
