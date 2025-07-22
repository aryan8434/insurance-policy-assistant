# Railway Deployment Guide

## 🚀 Deploy Your PDF Q&A API on Railway (FREE)

### Step 1: Prepare Your Code
1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - PDF Q&A API"
   git branch -M main
   git remote add origin https://github.com/yourusername/pdf-qa-api.git
   git push -u origin main
   ```

### Step 2: Deploy on Railway
1. **Go to [railway.app](https://railway.app)**
2. **Sign up/Login** with GitHub
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Choose your repository**

### Step 3: Configure Environment Variables
1. **In Railway Dashboard**:
   - Go to your project
   - Click "Variables" tab
   - Add: `GOOGLE_API_KEY` = `your_api_key_here`

### Step 4: Railway will automatically:
- ✅ Detect Python project
- ✅ Install dependencies from `api_requirements.txt`
- ✅ Run using `Procfile` configuration
- ✅ Provide you with a public URL

### Step 5: Test Your Live API
Your API will be available at: `https://your-app-name.up.railway.app`

**Interactive Docs**: `https://your-app-name.up.railway.app/docs`

## 🔧 Railway Configuration Files Created:

- `Procfile`: Tells Railway how to run your app
- `runtime.txt`: Specifies Python version
- `api_requirements.txt`: Lists all dependencies

## 💰 Railway Free Tier:
- ✅ $5 free credits monthly
- ✅ Enough for moderate usage
- ✅ Automatic deployments
- ✅ Custom domains available

## 🌐 Alternative Free Hosting Options:

### 1. **Render** (Alternative)
- Similar to Railway
- Good free tier
- Easy deployment

### 2. **Heroku** (Limited Free)
- Popular platform
- Good documentation
- Limited free hours

## 📱 How Others Will Use Your API:

Once deployed, share your Railway URL:
```
https://your-app-name.up.railway.app
```

Others can:
1. **Upload PDFs** via POST to `/upload-pdf`
2. **Ask questions** via POST to `/ask-question` 
3. **View docs** at `/docs`

## 🔒 Security Note:
Your Google API key is safely stored as an environment variable and won't be visible in your code or to users.
