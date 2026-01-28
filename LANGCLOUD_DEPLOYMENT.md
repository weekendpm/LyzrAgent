# 🚀 LangGraph Cloud Deployment Guide

## Overview

This guide walks you through deploying your Document Processing Platform to **LangGraph Cloud**, making it accessible to your Lovable frontend.

## Prerequisites

✅ **LangSmith Account**: Sign up at [smith.langchain.com](https://smith.langchain.com)  
✅ **OpenAI API Key**: Required for AI agents  
✅ **Git Repository**: Your code should be in a Git repo  
✅ **LangGraph CLI**: Already installed in your project  

## Step-by-Step Deployment

### 1. Get Your API Keys

#### LangSmith API Key
1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Sign up/login to your account
3. Go to Settings → API Keys
4. Create a new API key
5. Copy the key (starts with `ls__`)

#### OpenAI API Key
- You already have this: `sk-proj-b6jPHxiv...`

### 2. Set Environment Variables

```bash
# Required for deployment
export OPENAI_API_KEY="your-openai-api-key-here"

# Required for LangSmith tracing
export LANGCHAIN_API_KEY="ls__your-langsmith-api-key-here"
```

### 3. Deploy to LangGraph Cloud

#### Option A: Use the Deployment Script (Recommended)
```bash
cd /Users/rudranshtiwri/Code/LyzrAgent
./deploy-langcloud.sh
```

#### Option B: Manual Deployment
```bash
# Login to LangGraph Cloud
langgraph auth login

# Deploy your application
langgraph deploy --wait
```

### 4. Get Your Deployment URL

After successful deployment, you'll get a URL like:
```
https://your-app-name.langchain.app
```

### 5. Test Your Deployment

```bash
# Test health endpoint
curl https://your-app-name.langchain.app/health

# Test text processing
curl -X POST "https://your-app-name.langchain.app/process-text" \
  -H "Content-Type: application/json" \
  -d '{"text_content": "Test document", "document_type": "txt"}'
```

## Configuration Files Created

### `langgraph.json`
```json
{
  "dependencies": ["requirements.txt"],
  "graphs": {
    "document_processor": "./workflows/document_workflow.py:get_workflow"
  },
  "env": {
    "OPENAI_API_KEY": null,
    "LANGCHAIN_TRACING_V2": "true",
    "LANGCHAIN_PROJECT": "document-processor"
  }
}
```

### `Dockerfile.langcloud`
- Optimized Docker container for LangGraph Cloud
- Includes all system dependencies (tesseract, etc.)
- Production-ready configuration

## Environment Variables in LangGraph Cloud

Set these in your LangGraph Cloud dashboard:

| Variable | Value | Required |
|----------|-------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | ✅ Yes |
| `LANGCHAIN_API_KEY` | Your LangSmith API key | ⚠️ Recommended |
| `ANTHROPIC_API_KEY` | Your Anthropic API key | ❌ Optional |
| `ENVIRONMENT` | `production` | ✅ Yes |
| `LOG_LEVEL` | `INFO` | ❌ Optional |

## Lovable Integration

### Update Your Frontend

Once deployed, update your Lovable frontend to use the new URL:

```typescript
// Replace localhost with your deployment URL
const API_BASE_URL = 'https://your-app-name.langchain.app';

// Example API call
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

### CORS Configuration

Your deployment is already configured for Lovable domains:
- `https://*.lovable.dev`
- `https://*.lovableproject.com`
- `http://localhost:3000` (for local development)

## Monitoring & Debugging

### LangSmith Dashboard
- **URL**: [smith.langchain.com](https://smith.langchain.com)
- **Features**: Real-time tracing, debugging, performance monitoring
- **Project**: `document-processor`

### Deployment Commands

```bash
# Check deployment status
langgraph deployment list

# View logs
langgraph deployment logs

# Update deployment
langgraph deploy

# Delete deployment
langgraph deployment delete
```

## API Endpoints

Your deployed API will have these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | API documentation |
| `/process-document` | POST | Upload and process document |
| `/process-text` | POST | Process text directly |
| `/status/{thread_id}` | GET | Get processing status |
| `/results/{thread_id}` | GET | Get processing results |
| `/human-review/{thread_id}/submit` | POST | Submit human review |

## Troubleshooting

### Common Issues

#### 1. Deployment Fails
```bash
# Check your environment variables
echo $OPENAI_API_KEY
echo $LANGCHAIN_API_KEY

# Verify langgraph.json is valid
cat langgraph.json | jq .
```

#### 2. API Key Errors
- Ensure `OPENAI_API_KEY` is set in LangGraph Cloud dashboard
- Verify the key is valid and has sufficient credits

#### 3. CORS Issues
- Check that your Lovable domain is in the allowed origins
- Verify the deployment URL is correct

#### 4. Health Check Fails
```bash
# Check deployment status
langgraph deployment list

# View detailed logs
langgraph deployment logs --follow
```

### Getting Help

1. **LangGraph Cloud Docs**: [langchain-ai.github.io/langgraph/cloud/](https://langchain-ai.github.io/langgraph/cloud/)
2. **LangSmith Docs**: [docs.smith.langchain.com](https://docs.smith.langchain.com)
3. **Deployment Logs**: `langgraph deployment logs`

## Cost Optimization

### Tips to Reduce Costs

1. **Set Scaling Limits**: Configure `min_instances: 1, max_instances: 3`
2. **Monitor Usage**: Use LangSmith dashboard to track API calls
3. **Optimize Prompts**: Shorter prompts = lower costs
4. **Use Caching**: Enable response caching where possible

## Security Best Practices

✅ **API Keys**: Never commit API keys to Git  
✅ **Environment Variables**: Use LangGraph Cloud dashboard to set secrets  
✅ **CORS**: Restrict origins in production  
✅ **Rate Limiting**: Consider adding rate limiting for production  
✅ **Monitoring**: Enable LangSmith tracing for observability  

## Next Steps

1. **Deploy**: Run `./deploy-langcloud.sh`
2. **Test**: Verify all endpoints work
3. **Update Lovable**: Use your new deployment URL
4. **Monitor**: Check LangSmith dashboard
5. **Scale**: Adjust scaling settings as needed

🎉 **You're ready to deploy!** Your Document Processing Platform will be live and accessible to Lovable in just a few minutes.

## Quick Deployment Checklist

- [ ] Set `OPENAI_API_KEY` environment variable
- [ ] Set `LANGCHAIN_API_KEY` environment variable  
- [ ] Run `./deploy-langcloud.sh`
- [ ] Test deployment with `curl`
- [ ] Update Lovable frontend with new URL
- [ ] Verify CORS is working
- [ ] Check LangSmith dashboard for tracing

**Happy deploying! 🚀**