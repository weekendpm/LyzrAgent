# 📋 Document Processing Platform - Client API Documentation

## 🚀 Overview

Professional document processing platform with 9 specialized AI agents, built using LangGraph and FastAPI. This API follows **LangGraph Cloud standards** for seamless integration.

### 🎯 Key Features
- **9 AI Agents**: Ingestion, Classification, Extraction, Validation, Rule Evaluation, Anomaly Detection, Human Review, Audit Learning, Coordinator
- **Standard LangGraph API**: Compatible with LangGraph Cloud tooling
- **Real-time Updates**: WebSocket streaming for live progress
- **Professional Grade**: Enterprise-ready with proper error handling

---

## 🔗 API Endpoints

### Base URL
```
Production: https://your-domain.railway.app
Development: http://localhost:8000
```

### Authentication
```
API Key: Required in headers or environment
Header: Authorization: Bearer YOUR_API_KEY
```

---

## 📊 Standard LangGraph Endpoints

### 1. **POST /invoke** - Start Workflow
Initiates document processing with 9 AI agents.

**Request:**
```json
{
  "input": {
    "text_content": "Invoice from ABC Corp for $1000 due on 2024-12-31",
    "file_type": "text"
  },
  "config": {},
  "metadata": {
    "client_id": "your_client_id",
    "priority": "high"
  }
}
```

**Response:**
```json
{
  "run_id": "run_uuid_timestamp",
  "status": "running",
  "input": {
    "text_content": "Invoice from ABC Corp for $1000 due on 2024-12-31",
    "file_type": "text"
  },
  "output": null,
  "metadata": {
    "document_id": "uuid",
    "thread_id": "thread_uuid_timestamp",
    "created_at": "2026-01-28T21:32:46.891444"
  }
}
```

**cURL Example:**
```bash
curl -X POST https://your-domain.railway.app/invoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "input": {
      "text_content": "Your document content here",
      "file_type": "text"
    }
  }'
```

---

### 2. **GET /runs/{run_id}** - Check Status
Monitor workflow progress and get results.

**Response:**
```json
{
  "run_id": "run_uuid_timestamp",
  "status": "success|running|error",
  "input": {
    "text_content": "Original input"
  },
  "output": {
    "extracted_data": {
      "invoice_number": "INV-001",
      "vendor_name": "ABC Corp",
      "total_amount": 1000.00,
      "due_date": "2024-12-31"
    },
    "validated_data": { /* Validated version */ },
    "confidence_scores": {
      "extraction": 0.95,
      "classification": 0.98,
      "validation": 0.92
    },
    "business_rules_applied": [
      {
        "rule_id": "invoice_validation",
        "rule_name": "Invoice Amount Check",
        "action": "approved",
        "priority": 1
      }
    ],
    "anomalies_detected": [],
    "human_review_required": false
  },
  "metadata": {
    "document_id": "uuid",
    "thread_id": "thread_uuid_timestamp",
    "progress_percentage": 100.0,
    "current_step": "completed",
    "agent_status": {
      "ingestion_agent": {"status": "completed", "confidence": 0.95},
      "classification_agent": {"status": "completed", "confidence": 0.98},
      "extraction_agent": {"status": "completed", "confidence": 0.95}
      /* ... all 9 agents */
    }
  },
  "created_at": "2026-01-28T21:32:46.891444",
  "updated_at": "2026-01-28T21:33:15.234567"
}
```

**Status Values:**
- `running` - Processing in progress
- `success` - Completed successfully
- `error` - Failed with error

---

### 3. **GET /stream/{run_id}** - Real-time Updates
Get WebSocket connection info for live updates.

**Response:**
```json
{
  "message": "Use WebSocket for streaming",
  "websocket_url": "ws://your-domain.railway.app/workflow/{document_id}/stream",
  "run_id": "run_uuid_timestamp",
  "document_id": "uuid"
}
```

**WebSocket Messages:**
```json
{
  "type": "workflow_started|agent_completed|workflow_completed|workflow_error",
  "run_id": "run_uuid_timestamp",
  "document_id": "uuid",
  "agent_name": "extraction_agent",
  "progress": 45.5,
  "timestamp": "2026-01-28T21:33:00.000Z"
}
```

---

### 4. **GET /health** - Health Check
Verify API availability.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T21:33:00.000000",
  "service": "Document Processing Platform"
}
```

---

## 🎨 Frontend Integration Examples

### JavaScript/TypeScript
```javascript
class DocumentProcessingClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async invokeWorkflow(textContent, fileType = 'text') {
    const response = await fetch(`${this.baseUrl}/invoke`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        input: { text_content: textContent, file_type: fileType }
      })
    });
    return response.json();
  }

  async checkStatus(runId) {
    const response = await fetch(`${this.baseUrl}/runs/${runId}`, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    return response.json();
  }

  connectWebSocket(documentId) {
    return new WebSocket(`${this.baseUrl.replace('http', 'ws')}/workflow/${documentId}/stream`);
  }
}

// Usage
const client = new DocumentProcessingClient('https://your-domain.railway.app', 'your-api-key');

// Start processing
const result = await client.invokeWorkflow('Invoice content here');
console.log('Started:', result.run_id);

// Monitor progress
const status = await client.checkStatus(result.run_id);
console.log('Progress:', status.metadata.progress_percentage + '%');

// Real-time updates
const ws = client.connectWebSocket(result.metadata.document_id);
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Update:', update);
};
```

### Python Client
```python
import requests
import websocket
import json

class DocumentProcessingClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {'Authorization': f'Bearer {api_key}'}

    def invoke_workflow(self, text_content, file_type='text'):
        response = requests.post(
            f'{self.base_url}/invoke',
            json={
                'input': {
                    'text_content': text_content,
                    'file_type': file_type
                }
            },
            headers={**self.headers, 'Content-Type': 'application/json'}
        )
        return response.json()

    def check_status(self, run_id):
        response = requests.get(
            f'{self.base_url}/runs/{run_id}',
            headers=self.headers
        )
        return response.json()

# Usage
client = DocumentProcessingClient('https://your-domain.railway.app', 'your-api-key')
result = client.invoke_workflow('Invoice content here')
print(f"Started: {result['run_id']}")
```

---

## 🔧 Error Handling

### Error Response Format
```json
{
  "detail": "Error description",
  "status_code": 400,
  "error_type": "validation_error|processing_error|not_found"
}
```

### Common Error Codes
- **400** - Bad Request (invalid input)
- **404** - Not Found (invalid run_id)
- **500** - Internal Server Error (processing failed)
- **503** - Service Unavailable (system overloaded)

---

## 📈 Performance & Limits

### Processing Times
- **Simple Text**: 2-5 seconds
- **Complex Documents**: 10-30 seconds
- **Large Files**: 30-60 seconds

### Rate Limits
- **Invoke**: 10 requests/minute
- **Status Check**: 60 requests/minute
- **WebSocket**: 1 connection per document

### File Limits
- **Text Content**: 100KB max
- **Processing Timeout**: 5 minutes

---

## 🚀 Deployment Information

### Production URL
```
https://your-domain.railway.app
```

### Environment Variables Required
```env
OPENAI_API_KEY=your_openai_key
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4
```

### Health Monitoring
- **Health Check**: `GET /health`
- **Uptime**: 99.9% SLA
- **Response Time**: <2s average

---

## 📞 Support & Integration

### Integration Support
- **Documentation**: This API follows LangGraph Cloud standards
- **SDKs**: Compatible with LangGraph client libraries
- **Webhooks**: WebSocket streaming for real-time updates

### Contact Information
- **Technical Support**: [Your contact info]
- **API Issues**: [Your support email]
- **Documentation**: [Your docs URL]

---

## 🔒 Security

### Authentication
- API Key required for all endpoints
- Keys should be kept secure and rotated regularly

### Data Privacy
- Documents processed in memory only
- No persistent storage of client data
- GDPR compliant processing

### HTTPS
- All production endpoints use HTTPS
- WebSocket connections use WSS

---

## 📋 Quick Start Checklist

- [ ] Get API key from provider
- [ ] Test `/health` endpoint
- [ ] Try `/invoke` with sample data
- [ ] Monitor with `/runs/{run_id}`
- [ ] Set up WebSocket for real-time updates
- [ ] Implement error handling
- [ ] Deploy to production

**Your Document Processing Platform is ready for client integration!** 🎉