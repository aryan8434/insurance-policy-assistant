# Steps to Upload Your Project to GitHub

## 1. Create GitHub Repository
1. Go to https://github.com
2. Click "New Repository"
3. Name it: `ai-pdf-qa-api` or `smart-document-assistant`
4. Add description: "AI-powered PDF Q&A API using Google Gemini and FastAPI"
5. Make it PUBLIC (for hackathons)
6. Click "Create Repository"

## 2. Upload Your Code
Open terminal in your project folder and run:

```bash
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: AI-powered PDF Q&A API"

# Add GitHub repository
git remote add origin https://github.com/yourusername/ai-pdf-qa-api.git

# Push to GitHub
git push -u origin main
```

## 3. Deploy to Railway (Free)
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Add environment variable: `GOOGLE_API_KEY = your-key-here`
6. Deploy automatically!

## 4. Get Your Live URL
After deployment, Railway gives you a URL like:
`https://ai-pdf-qa-api-production.railway.app`

Use this URL in your hackathon submission!
