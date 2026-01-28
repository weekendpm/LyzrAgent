# 🚀 Railway Deployment Guide - Easy Cloud Deployment

## Why Railway?

Railway is perfect for your Document Processing Platform because:
- ✅ **Simple deployment** - Just connect GitHub and deploy
- ✅ **Automatic HTTPS** - Get a secure URL instantly  
- ✅ **Environment variables** - Easy to set API keys
- ✅ **Free tier** - Great for testing and development
- ✅ **Lovable compatible** - Works perfectly with frontend

## Step-by-Step Deployment

### 1. Push to GitHub (Required)

First, push your code to GitHub:

```bash
# Add GitHub remote (replace with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/LyzrAgent.git

# Push to GitHub
git push -u origin main
```

### 2. Deploy to Railway

1. **Go to [railway.app](https://railway.app)**
2. **Sign up/Login** with GitHub
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Choose your `LyzrAgent` repository**
6. **Railway will automatically detect it's a Python app**

### 3. Set Environment Variables

In Railway dashboard:

1. Go to your project
2. Click **"Variables"** tab
3. Add these variables:

| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | `your-openai-api-key-here` |
| `ENVIRONMENT` | `production` |
| `LANGCHAIN_TRACING_V2` | `true` |
| `LANGCHAIN_PROJECT` | `document-processor` |

### 4. Deploy!

Railway will automatically:
- ✅ Build your Docker container
- ✅ Install dependencies from `requirements.txt`
- ✅ Start your FastAPI server
- ✅ Give you a public URL

## Your Deployment URL

After deployment, you'll get a URL like:
```
https://lyzragent-production.up.railway.app
```

## Test Your Deployment

```bash
# Test health endpoint
curl https://your-app.railway.app/health

# Test text processing
curl -X POST "https://your-app.railway.app/process-text" \
  -H "Content-Type: application/json" \
  -d '{"text_content": "Test document", "document_type": "txt"}'
```

## Update Lovable Frontend

Once deployed, update your Lovable frontend:

```typescript
// Replace with your Railway URL
const API_BASE_URL = 'https://your-app.railway.app';

const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/process-document`, {
    method: 'POST',
    body: formData,
  });
  
  return response.json();
};
```

## Alternative: Render Deployment

If you prefer Render:

1. **Go to [render.com](https://render.com)**
2. **Connect GitHub**
3. **Create Web Service**
4. **Choose your repo**
5. **Set build command**: `pip install -r requirements.txt`
6. **Set start command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
7. **Add environment variables** (same as above)

## Files Created for Deployment

✅ `railway.json` - Railway configuration  
✅ `Procfile` - Process definition  
✅ `runtime.txt` - Python version  
✅ `requirements.txt` - Dependencies (updated with langsmith)  
✅ `.gitignore` - Git ignore rules  

## Monitoring & Logs

### Railway Dashboard
- **Logs**: Real-time deployment and application logs
- **Metrics**: CPU, memory, network usage
- **Deployments**: History of all deployments

### API Endpoints
- **Health**: `https://your-app.railway.app/health`
- **Docs**: `https://your-app.railway.app/docs`
- **All endpoints**: Same as local, just different URL

## Troubleshooting

### Common Issues

#### 1. Build Fails
- Check that `requirements.txt` is correct
- Verify Python version in `runtime.txt`
- Check Railway build logs

#### 2. App Won't Start
- Verify `OPENAI_API_KEY` is set correctly
- Check application logs in Railway dashboard
- Ensure health check endpoint works

#### 3. CORS Issues
- Your app is already configured for Lovable domains
- Verify the deployment URL is correct

### Getting Help

1. **Railway Docs**: [docs.railway.app](https://docs.railway.app)
2. **Railway Discord**: Active community support
3. **Application Logs**: Check Railway dashboard

## Cost Considerations

### Railway Pricing
- **Hobby Plan**: $5/month - Perfect for development
- **Pro Plan**: $20/month - Production ready
- **Usage-based**: Pay for what you use

### Optimization Tips
- **Sleep on idle**: Railway automatically sleeps inactive apps
- **Resource limits**: Set appropriate CPU/memory limits
- **Monitor usage**: Use Railway dashboard to track costs

## Security Best Practices

✅ **Environment Variables**: Never commit API keys  
✅ **HTTPS**: Automatic with Railway  
✅ **CORS**: Already configured for Lovable  
✅ **Rate Limiting**: Consider adding for production  

## Next Steps

1. **Push to GitHub**: `git push origin main`
2. **Deploy to Railway**: Follow steps above
3. **Test endpoints**: Verify everything works
4. **Update Lovable**: Use your new URL
5. **Monitor**: Check logs and metrics

## Quick Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Railway project created
- [ ] Environment variables set
- [ ] Deployment successful
- [ ] Health check passes
- [ ] API endpoints working
- [ ] Lovable frontend updated
- [ ] End-to-end test completed

🎉 **Your Document Processing Platform is now live and ready for Lovable!**

## Example Integration

Here's a complete example for your Lovable frontend:

```typescript
// api.ts
const API_BASE_URL = 'https://your-app.railway.app';

export const documentAPI = {
  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/process-document`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    return response.json();
  },

  async getStatus(threadId: string) {
    const response = await fetch(`${API_BASE_URL}/status/${threadId}`);
    return response.json();
  },

  async getResults(threadId: string) {
    const response = await fetch(`${API_BASE_URL}/results/${threadId}`);
    return response.json();
  }
};
```

**Happy deploying! 🚀**