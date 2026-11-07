# QuantaBench Vercel Deployment Guide

This guide explains how to deploy the QuantaBench frontend to Vercel.

---

## 🚀 Quick Deploy

### Option 1: Deploy via Vercel CLI (Recommended)

**1. Install Vercel CLI**
```bash
npm install -g vercel
```

**2. Login to Vercel**
```bash
vercel login
```

**3. Deploy the Frontend**
```bash
cd "QuantaBench Frontend/quanta-main"
vercel
```

**4. Follow the prompts:**
- Set up and deploy? **Y**
- Which scope? Select your account
- Link to existing project? **N** (first time)
- Project name? **quantabench** (or your preferred name)
- Directory? **./QuantaBench Frontend/quanta-main**
- Override settings? **N**

**5. Set Environment Variables**
```bash
vercel env add NEXT_PUBLIC_API_URL
# Enter your backend API URL (e.g., https://your-backend.herokuapp.com)
```

**6. Deploy to Production**
```bash
vercel --prod
```

---

### Option 2: Deploy via GitHub Integration

**1. Push to GitHub** (Already done!)
```
✓ Repository: https://github.com/ksu0928/QuantaBench
```

**2. Import to Vercel**
- Go to https://vercel.com/new
- Click "Import Git Repository"
- Select **ksu0928/QuantaBench**
- Click "Import"

**3. Configure Project**

**Root Directory:**
```
QuantaBench Frontend/quanta-main
```

**Framework Preset:**
```
Next.js
```

**Build Command:**
```
pnpm build
```

**Output Directory:**
```
.next
```

**Install Command:**
```
pnpm install
```

**4. Environment Variables**

Add the following environment variable:

| Name | Value | Description |
|------|-------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://your-backend-url.com` | Backend API URL |

**5. Deploy**

Click **"Deploy"** and wait for build to complete (~2-3 minutes)

---

## 🔧 Configuration Details

### Backend URL Options

**Option A: Deploy Backend to Heroku/Render/Railway**
```
NEXT_PUBLIC_API_URL=https://quantabench-api.herokuapp.com
```

**Option B: Use ngrok for local backend**
```bash
# Terminal 1: Start backend
cd backend
uvicorn app.main:app --port 8000

# Terminal 2: Expose via ngrok
ngrok http 8000

# Use the ngrok URL in Vercel
NEXT_PUBLIC_API_URL=https://abc123.ngrok.io
```

**Option C: Deploy backend to cloud**
- AWS Lambda
- Google Cloud Run
- Azure Functions
- DigitalOcean App Platform

### Vercel Project Settings

After deployment, configure:

**1. Environment Variables**
```
Settings → Environment Variables
```
Add `NEXT_PUBLIC_API_URL` for all environments (Production, Preview, Development)

**2. Deployment Protection** (Optional)
```
Settings → Deployment Protection
```
Enable password protection if needed

**3. Custom Domain** (Optional)
```
Settings → Domains
```
Add your custom domain (e.g., quantabench.com)

---

## 🧪 Testing Deployment

**1. Visit Deployment URL**
```
https://quantabench-xyz.vercel.app
```

**2. Check Backend Connection**
- Look for status pills in header
- Should show backend connection status
- If offline, check NEXT_PUBLIC_API_URL

**3. Run Optimization**
- Click "Run Benchmark"
- Should connect to backend API
- View results in real-time

**4. Check Console** (F12)
```javascript
// Should not see CORS errors
// Should see successful API calls to backend
```

---

## 🔍 Troubleshooting

### Issue 1: Backend Not Connected

**Symptoms:**
- Status pills show "Backend offline"
- API calls fail

**Solution:**
```bash
# Check environment variable
vercel env ls

# Update if needed
vercel env add NEXT_PUBLIC_API_URL production
```

### Issue 2: CORS Errors

**Symptoms:**
- Console shows CORS policy errors

**Solution:**
Update backend CORS settings to include Vercel domain:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://quantabench-xyz.vercel.app",  # Add your Vercel URL
        "https://quantabench.com",  # Custom domain if any
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue 3: Build Fails

**Symptoms:**
- Vercel build process fails
- TypeScript errors

**Solution:**
```bash
# Test build locally first
cd "QuantaBench Frontend/quanta-main"
pnpm install
pnpm build

# If successful locally but fails on Vercel:
# Check Node.js version in package.json
```

Add to package.json:
```json
{
  "engines": {
    "node": ">=18.0.0",
    "pnpm": ">=8.0.0"
  }
}
```

### Issue 4: Environment Variables Not Working

**Symptoms:**
- Frontend tries to connect to localhost
- API URL not set correctly

**Solution:**
```bash
# Ensure variable name starts with NEXT_PUBLIC_
vercel env add NEXT_PUBLIC_API_URL

# Redeploy after adding
vercel --prod
```

---

## 📊 Deployment Checklist

- [ ] Backend is deployed and accessible
- [ ] Backend CORS allows Vercel domain
- [ ] Environment variable `NEXT_PUBLIC_API_URL` is set
- [ ] Vercel project is connected to GitHub repo
- [ ] Build completes successfully
- [ ] Frontend loads at Vercel URL
- [ ] Backend connection works (check status pills)
- [ ] Optimization runs successfully
- [ ] No console errors

---

## 🌐 Deployment Architecture

```
┌─────────────────────────────────────────┐
│     User Browser                        │
│     quantabench-xyz.vercel.app          │
└─────────────┬───────────────────────────┘
              │
              │ HTTPS
              │
┌─────────────▼───────────────────────────┐
│     Vercel Edge Network                 │
│     - Static assets cached globally     │
│     - Next.js SSR on demand            │
│     - Automatic HTTPS                   │
└─────────────┬───────────────────────────┘
              │
              │ REST API calls
              │ (NEXT_PUBLIC_API_URL)
              │
┌─────────────▼───────────────────────────┐
│     Backend API                         │
│     (Heroku/Render/Railway/etc)        │
│     - FastAPI application               │
│     - QAOA pipeline                     │
│     - Result caching                    │
└─────────────────────────────────────────┘
```

---

## 🎯 Post-Deployment Steps

### 1. Update Repository README

Add deployment badge:
```markdown
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/ksu0928/QuantaBench)
```

### 2. Configure Custom Domain (Optional)

```bash
# Add domain via CLI
vercel domains add quantabench.com

# Or via dashboard: Settings → Domains
```

### 3. Set Up Monitoring

**Vercel Analytics:**
```typescript
// Already included in layout.tsx
import { Analytics } from '@vercel/analytics/next'
```

**Custom Monitoring:**
- Sentry for error tracking
- LogRocket for session replay
- Datadog for performance

### 4. Enable Automatic Deployments

In Vercel dashboard:
- **Production**: Deploy from `main` branch
- **Preview**: Deploy from pull requests
- **Development**: Deploy from `dev` branch (if created)

---

## 💰 Pricing Considerations

### Vercel Free Tier Includes:
- ✅ 100 GB bandwidth/month
- ✅ Unlimited deployments
- ✅ Automatic HTTPS
- ✅ Global CDN
- ✅ Serverless functions

### Upgrade to Pro if needed:
- More bandwidth
- Team collaboration
- Advanced analytics
- Priority support

---

## 🚀 Continuous Deployment

Once connected to GitHub:

**1. Push to GitHub**
```bash
git add .
git commit -m "Update frontend"
git push origin main
```

**2. Automatic Deployment**
- Vercel automatically detects push
- Builds and deploys new version
- Creates preview URL for testing

**3. Production Promotion**
- Once verified, deployment goes live
- Old version remains available as rollback

---

## 📱 Preview Deployments

Every pull request gets a preview deployment:

**1. Create Feature Branch**
```bash
git checkout -b feature/new-ui
```

**2. Make Changes & Push**
```bash
git add .
git commit -m "Add new UI feature"
git push origin feature/new-ui
```

**3. Create Pull Request**
- Vercel creates preview deployment
- Comment with preview URL
- Test changes before merging

---

## 🔐 Security

### Environment Variables
- Never commit `.env.local` to git (already in .gitignore)
- Use Vercel environment variables for secrets
- Prefix public vars with `NEXT_PUBLIC_`

### HTTPS
- Automatic HTTPS on Vercel
- Free SSL certificates
- HTTP to HTTPS redirect

### Backend Authentication
- Consider adding API keys
- Implement rate limiting
- Use CORS properly

---

## 📞 Support

### Vercel Resources
- **Documentation**: https://vercel.com/docs
- **CLI Reference**: https://vercel.com/docs/cli
- **Support**: https://vercel.com/support

### QuantaBench Issues
- **GitHub**: https://github.com/ksu0928/QuantaBench/issues
- **Documentation**: See README.md

---

## ✅ Deployment Complete!

Once deployed, your QuantaBench frontend will be available at:
```
https://quantabench-xyz.vercel.app
```

With features:
- ✅ Global CDN delivery
- ✅ Automatic HTTPS
- ✅ Continuous deployment
- ✅ Preview deployments
- ✅ Analytics built-in

**Happy deploying! 🎉**
