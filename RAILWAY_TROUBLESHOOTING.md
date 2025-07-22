# 🚨 Railway Deployment Troubleshooting Guide

## Common Issues & Solutions

### ❌ Issue 1: Wrong Requirements File
**Problem**: Railway found `streamlit` dependencies instead of `fastapi`
**Solution**: ✅ FIXED - Updated requirements.txt with FastAPI dependencies

### ❌ Issue 2: Missing Environment Variables
**Problem**: `GOOGLE_API_KEY` not set in Railway
**Solution**: 
1. Go to Railway project settings
2. Click "Variables" tab
3. Add: `GOOGLE_API_KEY = AIzaSyD2Ilkx4fg9rgW_Jt6Eksvptqq6VW8J55c`

### ❌ Issue 3: Wrong Start Command
**Problem**: Railway doesn't know how to start your app
**Solution**: ✅ READY - Procfile contains: `web: uvicorn api:app --host 0.0.0.0 --port $PORT`

### ❌ Issue 4: Python Version Issues
**Problem**: Railway using wrong Python version
**Solution**: ✅ READY - runtime.txt specifies `python-3.11.0`

### ❌ Issue 5: Port Configuration
**Problem**: App not binding to Railway's dynamic port
**Solution**: ✅ READY - Using `$PORT` environment variable

## 🔧 Step-by-Step Railway Deployment

### Method 1: Redeploy Existing Project
1. Go to your Railway dashboard
2. Find your failed project
3. Click "Deployments" tab
4. Click "Redeploy" on latest deployment
5. Wait for build to complete

### Method 2: Create New Project
1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `aryan8434/insurance-policy-assistant`
5. Add environment variable:
   - Key: `GOOGLE_API_KEY`
   - Value: `AIzaSyD2Ilkx4fg9rgW_Jt6Eksvptqq6VW8J55c`
6. Deploy!

## 📋 Deployment Checklist

- [x] **Correct requirements.txt** (FastAPI dependencies)
- [x] **Procfile exists** (uvicorn start command)
- [x] **runtime.txt exists** (Python 3.11.0)
- [x] **Code on GitHub** (latest version pushed)
- [ ] **Environment variable set** (GOOGLE_API_KEY in Railway)
- [ ] **Deployment initiated** (Railway build process)

## 🎯 Expected Railway Build Process

1. **Source Code**: Railway pulls from GitHub
2. **Python Setup**: Installs Python 3.11.0
3. **Dependencies**: Installs packages from requirements.txt
4. **Environment**: Sets GOOGLE_API_KEY variable
5. **Start Command**: Runs `uvicorn api:app --host 0.0.0.0 --port $PORT`
6. **Health Check**: Verifies app responds on assigned port
7. **Success**: Provides public URL

## 🚨 If Still Failing

Check Railway build logs for specific error messages:
- **Module not found**: Missing dependency in requirements.txt
- **Port binding error**: Procfile or port configuration issue
- **API key error**: Environment variable not set correctly
- **Import error**: Check if all files uploaded correctly

## 📞 Alternative: Quick Local Test

Test your API locally to ensure it works:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
Visit: http://localhost:8000/docs

If local works but Railway fails, it's usually an environment variable issue.
