# 🚀 Deployment Guide - Document Processing Platform

## Overview
Deploy your LangGraph document processing platform to production for client access. This guide covers Railway, Render, and other cloud platforms.

---

## 🚂 Railway Deployment (Recommended)

### Step 1: Prepare Your Project
```bash
# Create requirements.txt for production
pip freeze > requirements.txt

# Create Procfile
echo "web: uvicorn api.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Create railway.json
cat > railway.json << EOF
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn api.main:app --host 0.0.0.0 --port \$PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE"
  }
}
EOF
```

### Step 2: Deploy to Railway
1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Initialize Project:**
   ```bash
   cd /Users/rudranshtiwri/Code/LyzrAgent
   railway init
   railway link
   ```

3. **Set Environment Variables:**
   ```bash
   railway variables set OPENAI_API_KEY="your-openai-key"
   railway variables set LLM_PROVIDER="openai"
   railway variables set OPENAI_MODEL="gpt-4"
   railway variables set ENVIRONMENT="production"
   ```

4. **Deploy:**
   ```bash
   railway up
   ```

5. **Get Your URL:**
   ```bash
   railway status
   # Your app will be available at: https://your-app.railway.app
   ```

---

## 🎨 Render Deployment

### Step 1: Create render.yaml
```yaml
services:
  - type: web
    name: document-processor
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
    healthCheckPath: "/health"
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: LLM_PROVIDER
        value: openai
      - key: OPENAI_MODEL
        value: gpt-4
      - key: ENVIRONMENT
        value: production
```

### Step 2: Deploy
1. **Connect GitHub repo** to Render
2. **Set environment variables** in Render dashboard
3. **Deploy automatically** on git push

---

## ☁️ AWS/GCP Deployment

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  document-processor:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LLM_PROVIDER=openai
      - OPENAI_MODEL=gpt-4
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 🔧 Production Configuration

### Update CORS for Production
```python
# In api/main.py, update CORS origins
def get_cors_origins():
    return [
        "https://your-client-domain.com",
        "https://*.lovable.dev",
        "https://*.lovableproject.com",
        # Add your production domains
    ]
```

### Environment Variables
```env
# Production .env
OPENAI_API_KEY=your_production_key
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4
ENVIRONMENT=production
LOG_LEVEL=INFO
WORKERS=2
```

### Update API URLs in Client Code
```javascript
// Update your client configuration
const API_CONFIG = {
  BASE_URL: 'https://your-app.railway.app',  // Your deployed URL
  WS_BASE_URL: 'wss://your-app.railway.app', // WebSocket URL
  // ... rest of config
};
```

---

## 📊 Monitoring & Health Checks

### Health Check Endpoint
Your API includes a health check at `/health`:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T21:33:00.000000",
  "service": "Document Processing Platform"
}
```

### Monitoring Setup
```bash
# Test your deployed API
curl https://your-app.railway.app/health

# Test the standard endpoints
curl -X POST https://your-app.railway.app/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": {"text_content": "test", "file_type": "text"}}'
```

---

## 🔒 Security Considerations

### API Key Management
- Use environment variables, never hardcode keys
- Rotate API keys regularly
- Use different keys for dev/staging/production

### CORS Configuration
```python
# Production CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-client-domain.com",
        "https://your-lovable-app.lovableproject.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Rate Limiting (Optional)
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/invoke")
@limiter.limit("10/minute")
async def invoke_workflow(request: Request, ...):
    # Your endpoint code
```

---

## 📋 Client Integration Checklist

### For Your Overseas Clients:

1. **Share Production URL:**
   ```
   API Base URL: https://your-app.railway.app
   Health Check: https://your-app.railway.app/health
   Documentation: https://your-app.railway.app/docs
   ```

2. **Provide API Key:**
   - Generate secure API key
   - Share securely (not via email/chat)
   - Include in client documentation

3. **Share Documentation:**
   - `CLIENT_API_DOCUMENTATION.md`
   - Interactive docs at `/docs`
   - Example code snippets

4. **Test Integration:**
   ```bash
   # Test with client
   curl -X POST https://your-app.railway.app/invoke \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer CLIENT_API_KEY" \
     -d '{"input": {"text_content": "test invoice", "file_type": "text"}}'
   ```

---

## 🚀 Lovable Frontend Deployment

### Update Lovable Configuration
1. **Update API URL in Lovable:**
   ```
   LANGGRAPH_API_URL=https://your-app.railway.app
   ```

2. **Deploy Lovable App:**
   - Lovable will automatically deploy your frontend
   - Get your Lovable app URL: `https://your-app.lovableproject.com`

3. **Update CORS:**
   ```python
   # Add your Lovable URL to CORS origins
   allow_origins=[
       "https://your-app.lovableproject.com",
       # ... other origins
   ]
   ```

---

## 📞 Client Handoff Package

### What to Provide Your Client:

1. **🔗 URLs:**
   - Production API: `https://your-app.railway.app`
   - Frontend App: `https://your-app.lovableproject.com`
   - API Docs: `https://your-app.railway.app/docs`

2. **📋 Documentation:**
   - `CLIENT_API_DOCUMENTATION.md`
   - Integration examples
   - Error handling guide

3. **🔑 Credentials:**
   - API key (secure delivery)
   - Access instructions

4. **🛠 Support:**
   - Your contact information
   - SLA agreements
   - Monitoring dashboard access

### Professional Handoff Email Template:
```
Subject: Document Processing Platform - Production Ready

Dear [Client Name],

Your AI-powered document processing platform is now live and ready for integration!

🔗 Production URLs:
- API: https://your-app.railway.app
- Web Interface: https://your-app.lovableproject.com
- Documentation: https://your-app.railway.app/docs

📋 Key Features:
- 9 specialized AI agents for document processing
- Real-time progress tracking
- Standard LangGraph Cloud API
- Professional web interface
- 99.9% uptime SLA

📚 Integration Resources:
- Complete API documentation attached
- Code examples in JavaScript/Python
- WebSocket streaming for real-time updates

🔑 Your API credentials will be shared separately via secure channel.

Best regards,
[Your Name]
```

---

## ✅ Deployment Verification

### Final Checklist:
- [ ] API deployed and accessible
- [ ] Health check returns 200
- [ ] All endpoints working (`/invoke`, `/runs`, `/stream`)
- [ ] Environment variables set
- [ ] CORS configured for client domains
- [ ] API key authentication working
- [ ] WebSocket connections functional
- [ ] Documentation accessible
- [ ] Client integration tested
- [ ] Monitoring set up

**Your professional document processing platform is ready for client delivery!** 🎉