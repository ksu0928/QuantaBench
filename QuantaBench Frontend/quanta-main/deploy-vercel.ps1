# QuantaBench Vercel Deployment Script
# Run this script to deploy the frontend to Vercel

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  QuantaBench Vercel Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if in correct directory
if (-not (Test-Path "package.json")) {
    Write-Host "Error: package.json not found!" -ForegroundColor Red
    Write-Host "Please run this script from the frontend directory:" -ForegroundColor Yellow
    Write-Host "  cd 'QuantaBench Frontend\quanta-main'" -ForegroundColor Yellow
    exit 1
}

# Check Vercel CLI
Write-Host "Checking Vercel CLI..." -ForegroundColor Blue
try {
    $vercelVersion = vercel --version
    Write-Host "✓ Vercel CLI installed: $vercelVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Vercel CLI not found" -ForegroundColor Red
    Write-Host "Install with: npm install -g vercel" -ForegroundColor Yellow
    exit 1
}

# Login check
Write-Host ""
Write-Host "Checking Vercel authentication..." -ForegroundColor Blue
$whoami = vercel whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please login to Vercel first:" -ForegroundColor Yellow
    Write-Host "  vercel login" -ForegroundColor White
    exit 1
}
Write-Host "✓ Logged in as: $whoami" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deployment Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Make sure your backend is deployed and accessible" -ForegroundColor Yellow
Write-Host "   (e.g., Heroku, Render, Railway, or ngrok for local)" -ForegroundColor Gray
Write-Host ""

$backendUrl = Read-Host "Enter your backend API URL (or press Enter for http://localhost:8000)"
if ([string]::IsNullOrWhiteSpace($backendUrl)) {
    $backendUrl = "http://localhost:8000"
}

Write-Host ""
Write-Host "2. Deploying to Vercel..." -ForegroundColor Yellow
Write-Host "   This will create a preview deployment first" -ForegroundColor Gray
Write-Host ""

# Deploy to preview
Write-Host "Running: vercel" -ForegroundColor Blue
vercel

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ Preview deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Preview deployment successful!" -ForegroundColor Green
Write-Host ""

# Ask about environment variable
$setEnv = Read-Host "Set NEXT_PUBLIC_API_URL environment variable? (Y/n)"
if ($setEnv -ne 'n' -and $setEnv -ne 'N') {
    Write-Host ""
    Write-Host "Setting environment variable..." -ForegroundColor Blue
    Write-Host "NEXT_PUBLIC_API_URL=$backendUrl" -ForegroundColor Gray
    
    # Note: Vercel CLI env add is interactive, so we provide instructions
    Write-Host ""
    Write-Host "Please run these commands manually:" -ForegroundColor Yellow
    Write-Host "  vercel env add NEXT_PUBLIC_API_URL production" -ForegroundColor White
    Write-Host "  # Then enter: $backendUrl" -ForegroundColor Gray
    Write-Host "  vercel env add NEXT_PUBLIC_API_URL preview" -ForegroundColor White
    Write-Host "  # Then enter: $backendUrl" -ForegroundColor Gray
    Write-Host ""
    
    $continue = Read-Host "Press Enter after setting environment variables..."
}

# Deploy to production
Write-Host ""
Write-Host "3. Deploying to production..." -ForegroundColor Yellow
Write-Host ""

$deployProd = Read-Host "Deploy to production? (Y/n)"
if ($deployProd -ne 'n' -and $deployProd -ne 'N') {
    Write-Host ""
    Write-Host "Running: vercel --prod" -ForegroundColor Blue
    vercel --prod
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  ✓ Deployment Successful!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Your QuantaBench frontend is now live!" -ForegroundColor White
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Visit your deployment URL (shown above)" -ForegroundColor White
        Write-Host "  2. Check backend connection status in header" -ForegroundColor White
        Write-Host "  3. Run a test optimization" -ForegroundColor White
        Write-Host "  4. Add custom domain (optional): vercel domains add yourdomain.com" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "✗ Production deployment failed" -ForegroundColor Red
        Write-Host "Check the error messages above for details" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Deployment script complete!" -ForegroundColor Cyan
Write-Host ""
