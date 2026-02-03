# 🚀 Document Processing Platform

A sophisticated document processing platform built with LangGraph, featuring AI agents and human-in-the-loop capabilities for intelligent document analysis, extraction, and validation.
<img width="1702" height="1011" alt="image" src="https://github.com/user-attachments/assets/01fe5e32-b645-49e0-af24-c6140cdfa07b" />
<img width="1720" height="1001" alt="image" src="https://github.com/user-attachments/assets/5a06580b-d678-467b-b4a9-9a1ede0acdaa" />

## 🌟 Features

### 🤖 AI-Powered Processing Pipeline
- **9 Specialized Agents**: Each handling a specific aspect of document processing
- **LangGraph Orchestration**: Sophisticated workflow management with state persistence
- **Multi-LLM Support**: OpenAI GPT-4 and Anthropic Claude integration
- **Human-in-the-Loop**: Seamless human review and feedback integration

### 📄 Document Support
- **Multiple Formats**: PDF, DOCX, TXT, JPG, PNG, JPEG
- **OCR Capabilities**: Automatic text extraction from images
- **Smart Classification**: AI-powered document type detection
- **Structured Extraction**: Convert unstructured documents to structured data

### ⚡ Advanced Features
- **Real-time Processing**: WebSocket-based live updates
- **Business Rules Engine**: Configurable compliance and validation rules
- **Anomaly Detection**: ML-based unusual pattern detection
- **Audit Trail**: Comprehensive logging and learning system
- **RESTful API**: Complete API for integration

## 🏗️ Architecture

### Agent Pipeline
```
📥 Ingestion → 🏷️ Classification → 📋 Extraction → ✅ Validation 
    ↓
⚖️ Rule Evaluation → 🔍 Anomaly Detection → 👤 Human Review → 📊 Audit Learning
```

### Core Components
- **State Management**: TypedDict-based state flowing through all agents
- **Workflow Orchestration**: LangGraph StateGraph with conditional routing
- **Coordinator Agent**: Intelligent routing and decision making
- **WebSocket Manager**: Real-time communication and updates
- **Configuration System**: Environment-based configuration management

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- OpenAI API key or Anthropic API key
- Tesseract OCR (for image processing)

### Installation

1. **Clone and Setup**
```bash
git clone <your-repo-url>
cd LyzrAgent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

2. **Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys and settings
nano .env
```

3. **Required Environment Variables**
```bash
# Choose your LLM provider
LLM_PROVIDER="openai"  # or "anthropic"

# Add your API key
OPENAI_API_KEY="your-openai-api-key-here"
# OR
ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

### Running the Platform

1. **Test the Workflow**
```bash
python test_workflow.py
```

2. **Start the API Server**
```bash
uvicorn api.main:app --reload --port 8000
```

## 📚 Usage Examples

### 1. Process a Document via API

```bash
# Upload and process a document
curl -X POST "http://localhost:8000/process-document" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_invoice.pdf"
```

### 2. Process Text Content

```bash
# Process text directly
curl -X POST "http://localhost:8000/process-text" \
  -H "Content-Type: application/json" \
  -d '{
    "text_content": "INVOICE #123...",
    "document_type": "txt"
  }'
```

### 3. Check Processing Status

```bash
# Get document status
curl "http://localhost:8000/status/{document_id}"
```

### 4. WebSocket Real-time Updates

```javascript
// Connect to WebSocket for real-time updates
const ws = new WebSocket('ws://localhost:8000/workflow/{document_id}/stream');

ws.onmessage = function(event) {
    const update = JSON.parse(event.data);
    console.log('Processing update:', update);
};
```

### 5. Human Review Workflow

```bash
# Get review context
curl "http://localhost:8000/human-review/{document_id}/context"

# Submit human feedback
curl -X POST "http://localhost:8000/human-review/{document_id}/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "approve",
    "feedback": "Document looks good",
    "reviewer": "john.doe@company.com"
  }'
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider (openai/anthropic) | openai |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `CONFIDENCE_THRESHOLD` | Minimum confidence for auto-processing | 0.8 |
| `ENABLE_HUMAN_REVIEW` | Enable human review workflow | true |
| `MAX_FILE_SIZE` | Maximum file size in bytes | 52428800 |
| `API_PORT` | API server port | 8000 |

### Workflow Configuration

```python
from workflows.state_schema import WorkflowConfig

config = WorkflowConfig(
    llm_provider="openai",
    model_name="gpt-4",
    temperature=0.1,
    confidence_threshold=0.8,
    enable_human_review=True,
    enable_anomaly_detection=True
)
```

## 🧪 Testing

### Run Test Suite
```bash
# Run comprehensive workflow tests
python test_workflow.py

# Test specific components
python -m pytest tests/
```

### Test Cases Included
- ✅ Invoice processing and extraction
- ✅ Contract analysis and validation
- ✅ Resume parsing and structuring
- ✅ Error handling scenarios
- ✅ Human review workflows
- ✅ Anomaly detection
- ✅ Business rules evaluation

## 📊 Monitoring and Audit

### Audit Logs
- **Location**: `audit_logs/` directory
- **Format**: JSON with comprehensive processing details
- **Includes**: Agent performance, data quality metrics, business impact

### Metrics Tracked
- Processing time per agent
- Confidence scores and accuracy
- Human review rates
- Error rates and types
- Business rule compliance

### Learning System
- Pattern identification in processing results
- Confidence calibration analysis
- Performance trend tracking
- Improvement opportunity detection

## 🔌 API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/process-document` | POST | Upload and process document |
| `/process-text` | POST | Process text content |
| `/status/{document_id}` | GET | Get processing status |
| `/results/{document_id}` | GET | Get final results |
| `/human-review/{document_id}/context` | GET | Get review context |
| `/human-review/{document_id}/submit` | POST | Submit human feedback |
| `/workflow/{document_id}/stream` | WebSocket | Real-time updates |

### Response Models

```python
# Document processing response
{
  "success": true,
  "document_id": "uuid",
  "workflow_id": "workflow_uuid",
  "status": "processing",
  "requires_human_review": false
}

# Processing results
{
  "extracted_data": {...},
  "validated_data": {...},
  "business_rules_applied": [...],
  "anomalies_detected": [...],
  "confidence_scores": {...}
}
```

## 🛠️ Development

### Project Structure
```
LyzrAgent/
├── agents/                 # AI agent implementations
│   ├── ingestion_agent.py
│   ├── classification_agent.py
│   ├── extraction_agent.py
│   ├── validation_agent.py
│   ├── rule_evaluation_agent.py
│   ├── anomaly_detection_agent.py
│   ├── human_review_agent.py
│   ├── audit_learning_agent.py
│   └── coordinator_agent.py
├── workflows/              # LangGraph workflow definitions
│   ├── document_workflow.py
│   └── state_schema.py
├── api/                    # FastAPI application
│   ├── main.py
│   └── websocket_manager.py
├── config/                 # Configuration management
│   └── settings.py
├── tools/                  # Utility tools and processors
├── test_workflow.py        # Test suite
└── requirements.txt        # Dependencies
```

### Adding New Agents

1. **Create Agent File**
```python
# agents/my_new_agent.py
async def my_new_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    # Agent implementation
    return state
```

2. **Update Workflow**
```python
# workflows/document_workflow.py
from agents.my_new_agent import my_new_agent

# Add to workflow
workflow.add_node("my_new_agent", my_new_agent)
```

3. **Update Coordinator**
```python
# agents/coordinator_agent.py
AGENT_SEQUENCE = [..., "my_new_agent", ...]
```

### Custom Business Rules

```python
# Add to rule_evaluation_agent.py
async def my_custom_rule(self, rule, data, doc_type, metadata):
    # Custom rule logic
    if condition_met:
        return {
            "triggered": True,
            "confidence": 0.9,
            "details": "Custom rule triggered"
        }
    return {"triggered": False}
```

## 🚨 Production Deployment

### Security Checklist
- [ ] Change default secret keys
- [ ] Set up proper CORS origins
- [ ] Enable API authentication
- [ ] Use HTTPS in production
- [ ] Secure API keys in environment
- [ ] Set up rate limiting
- [ ] Configure proper logging

### Performance Optimization
- [ ] Use production ASGI server (Gunicorn + Uvicorn)
- [ ] Set up Redis for caching
- [ ] Configure database connection pooling
- [ ] Implement request queuing
- [ ] Set up monitoring and alerting

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add type hints to all functions
- Write comprehensive docstrings
- Include unit tests for new features
- Update documentation as needed

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangGraph**: For the powerful workflow orchestration framework
- **FastAPI**: For the excellent API framework
- **OpenAI/Anthropic**: For the powerful language models
- **Pydantic**: For data validation and settings management

## 📞 Support

- **Documentation**: Check the `/docs` endpoint when running the API
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

---

**Built with ❤️ using LangGraph, FastAPI, and AI**
