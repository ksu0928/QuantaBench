# 🚀 Deploy QuantaBench to Vercel NOW

## Quick Start (3 Steps)

### Step 1: Deploy via GitHub (Easiest) ⭐

1. **Go to Vercel**: https://vercel.com/new

2. **Import Repository**:
   - Click "Import Git Repository"
   - Search for **ksu0928/QuantaBench**
   - Click "Import"

3. **Configure Build**:
   - **Root Directory**: `QuantaBench Frontend/quanta-main`
   - **Framework Preset**: Next.js (auto-detected)
   - **Build Command**: `pnpm build` (auto-detected)
   - **Output Directory**: `.next` (auto-detected)
   - **Install Command**: `pnpm install` (auto-detected)

4. **Add Environment Variable**:
   - Click "Add Environment Variable"
   - **Name**: `NEXT_PUBLIC_API_URL`
   - **Value**: 
     - For local testing: `http://localhost:8000`
     - For deployed backend: `https://your-backend-url.com`
   - Apply to: **All** (Production, Preview, Development)

5. **Click "Deploy"**

⏱️ **Wait 2-3 minutes for build to complete**

✅ **Done!** Your app will be live at: `https://quantabench-xyz.vercel.app`

---

### Step 2: Deploy via CLI (Alternative)

If you prefer command line:

```powershell
# Navigate to frontend
cd "C:\Users\kusha\Downloads\QuantaBench\QuantaBench Frontend\quanta-main"

# Run deployment script
.\deploy-vercel.ps1

# OR manually:
vercel                    # Preview deployment
vercel --prod             # Production deployment
```

---

## 📝 Important Notes

### Backend Connection

Your frontend needs a backend API. Options:

**Option A: Deploy Backend First** (Recommended)
- Deploy backend to Heroku/Render/Railway
- Use that URL in `NEXT_PUBLIC_API_URL`

**Option B: Use Local Backend with ngrok**
```powershell
# Terminal 1: Start backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8000

# Terminal 2: Expose with ngrok
ngrok http 8000
# Copy the https URL (e.g., https://abc123.ngrok.io)
```

**Option C: Deploy Backend to Heroku**
```bash
# In backend directory
heroku create quantabench-api
git push heroku main
# Use: https://quantabench-api.herokuapp.com
```

### Update Backend CORS

After deploying to Vercel, update backend CORS:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://quantabench-xyz.vercel.app",  # Add your Vercel URL
        "https://*.vercel.app",  # Allow all preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## ✅ Verification Checklist

After deployment:

- [ ] Visit your Vercel URL
- [ ] Check backend status pills in header
- [ ] Click "Run Benchmark"
- [ ] Verify optimization runs successfully
- [ ] Check browser console for errors (F12)
- [ ] Test on mobile device

---

## 🔗 Useful Links

**Your Repository**: https://github.com/ksu0928/QuantaBench

**Vercel Dashboard**: https://vercel.com/dashboard

**Vercel Docs**: https://vercel.com/docs

**Detailed Guide**: See `VERCEL_DEPLOYMENT.md`

---

## 🆘 Troubleshooting

### "Backend offline" message

**Fix**: Check `NEXT_PUBLIC_API_URL` environment variable in Vercel dashboard

### CORS errors in console

**Fix**: Update backend CORS settings to include your Vercel URL

### Build fails

**Fix**: Ensure `package.json` has correct dependencies and scripts

### Can't see environment variable changes

**Fix**: Redeploy after changing environment variables:
```bash
vercel --prod
```

---

## 🎉 Success!

Once deployed, share your link:
```
https://quantabench-xyz.vercel.app
```

**Features:**
✅ Global CDN (fast worldwide)  
✅ Automatic HTTPS  
✅ Free SSL certificate  
✅ Continuous deployment from GitHub  
✅ Preview deployments for PRs  

---

## 🔄 Auto-Deploy Updates

Every time you push to GitHub:
```bash
git add .
git commit -m "Update feature"
git push origin main
```

Vercel automatically:
1. Detects the push
2. Builds new version
3. Deploys to production

No manual deployment needed! 🚀
