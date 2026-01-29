# 🚀 Horizontal Document Processing Platform - Lovable Integration Guide

## 🎯 Platform Philosophy

This is **NOT** a pre-configured invoice/contract processor. This is a **self-learning, horizontal, agentic platform** that:

1. ✅ **Accepts ANY document type** (passport, invoice, driver license, medical record, etc.)
2. ✅ **Dynamically discovers fields** based on document content
3. ✅ **Self-classifies** document types intelligently
4. ✅ **Extracts without hardcoded schemas** - AI figures out what to extract
5. ✅ **Learns and adapts** - no manual configuration needed

---

## 🤖 Agentic Workflow

```
Document Input
    ↓
🔹 COORDINATOR AGENT (orchestrates the flow)
    ↓
📥 INGESTION AGENT (processes file/text)
    ↓
🔍 CLASSIFICATION AGENT (identifies document type dynamically)
    ↓
📄 EXTRACTION AGENT (discovers and extracts ALL fields intelligently)
    ↓
✅ VALIDATION AGENT (validates extracted data)
    ↓
⚖️ RULE EVALUATION AGENT (applies business rules)
    ↓
🚨 ANOMALY DETECTION AGENT (detects unusual patterns)
    ↓
👥 HUMAN REVIEW AGENT (routes for review if needed)
    ↓
📚 AUDIT LEARNING AGENT (logs and learns from processing)
    ↓
🔹 COORDINATOR AGENT (decides next steps at each stage)
```

---

## 📡 API Integration

### **Endpoint:**
```
GET https://lyzragent-production.up.railway.app/results/{thread_id}
```

### **Dynamic Response Structure:**

The response structure **adapts based on document type**. Here's what you'll ALWAYS get:

```json
{
  "success": true,
  "document_id": "...",
  "status": "completed",
  "extracted_data": {
    // DYNAMIC FIELDS - discovered by AI
    "field_name_1": "value1",
    "field_name_2": "value2",
    // ... (all discovered fields with their actual names from the document)
    
    // INSIGHTS (always present)
    "_insights": {
      "summary": "AI-generated overview",
      "key_points": ["point 1", "point 2", ...],
      "action_items": ["action if any"],
      "status": "document status"
    },
    
    // ENTITIES (always present)
    "_entities": {
      "people": ["names found"],
      "organizations": ["companies found"],
      "locations": ["addresses found"]
    },
    
    // TEMPORAL DATA (always present)
    "_temporal": {
      "dates": ["all dates"],
      "deadlines": ["important deadlines"],
      "periods": ["date ranges"]
    },
    
    // FINANCIAL DATA (always present)
    "_financial": {
      "amounts": [100.00, 200.00],
      "currencies": ["USD"],
      "transactions": [...]
    },
    
    // METADATA (always present)
    "_metadata": {
      // Additional structured info
    },
    
    // ANALYSIS (always present)
    "_analysis": {
      "identified_type": "what AI thinks it is",
      "classified_as": "classification result",
      "extraction_method": "dynamic_ai"
    }
  },
  "validated_data": {
    // Same fields as extracted_data but validated/normalized
  },
  "confidence_scores": {
    "classification": 0.95,
    "extraction": 0.90,
    "validation": 1.0
  },
  "business_rules_applied": [...],
  "anomalies_detected": [...],
  "human_review_required": false,
  "human_review_details": {
    "review_id": "review_123...",
    "reason": "Low extraction confidence (0.55); Data validation failed (3 errors)",
    "priority": "high",
    "required_actions": ["verify_extraction", "correct_errors", "approve_document"],
    "context": {
      "extraction_confidence": 0.55,
      "validation_errors": ["Missing invoice_number", "Invalid date format", "Amount out of range"],
      "flagged_rules": ["high_value_transaction"]
    },
    "due_date": "2024-01-30T18:00:00Z"
  }
}
```

---

## 🎨 Frontend Integration (Lovable)

### **Adaptive UI Strategy:**

Since fields are **dynamically discovered**, your frontend should:

1. **Always display standard insights:**
   ```javascript
   const insights = data.extracted_data._insights;
   setSummary(insights.summary);
   setKeyPoints(insights.key_points);
   setActions(insights.action_items);
   setStatus(insights.status);
   ```

2. **Display discovered entities:**
   ```javascript
   const entities = data.extracted_data._entities;
   setPeople(entities.people);
   setOrganizations(entities.organizations);
   setLocations(entities.locations);
   ```

3. **Display temporal information:**
   ```javascript
   const temporal = data.extracted_data._temporal;
   setDates(temporal.dates);
   setDeadlines(temporal.deadlines);
   ```

4. **Display financial data if present:**
   ```javascript
   const financial = data.extracted_data._financial;
   if (financial.amounts.length > 0) {
     setAmounts(financial.amounts);
     setCurrencies(financial.currencies);
   }
   ```

5. **Handle human review if required:**
   ```javascript
   if (data.human_review_required && data.human_review_details) {
     const review = data.human_review_details;
     
     // Show review alert/modal
     showReviewAlert({
       reason: review.reason,  // Why it needs review
       priority: review.priority,  // high/medium/low
       actions: review.required_actions,  // What needs to be done
       context: review.context,  // Additional details
       dueDate: review.due_date
     });
   }
   ```

6. **Dynamically render ALL discovered fields:**
   ```javascript
   const allFields = {};
   for (const [key, value] of Object.entries(data.extracted_data)) {
     // Skip internal fields (starting with _)
     if (!key.startsWith('_')) {
       allFields[key] = value;
     }
   }
   
   // Render these fields dynamically:
   // - Invoice → invoice_number, vendor_name, total_amount
   // - Passport → Passport No, Surname, Date of Birth
   // - Driver License → DL NO, NAME, EXPIRY DATE
   // - Medical Record → Patient ID, Diagnosis, Medications
   // ... etc.
   ```

### **Example UI Component:**

```javascript
function DocumentDisplay({ resultData }) {
  const extractedData = resultData.extracted_data;
  const insights = extractedData._insights || {};
  const entities = extractedData._entities || {};
  const temporal = extractedData._temporal || {};
  const financial = extractedData._financial || {};
  const analysis = extractedData._analysis || {};
  
  // Get all discovered fields (excluding internal _ fields)
  const discoveredFields = Object.entries(extractedData)
    .filter(([key]) => !key.startsWith('_'))
    .map(([key, value]) => ({ field: key, value }));
  
  return (
    <div className="document-view">
      {/* Human Review Alert */}
      {resultData.human_review_required && resultData.human_review_details && (
        <div className="review-alert">
          <h3>⚠️ Human Review Required</h3>
          <p className="review-reason">{resultData.human_review_details.reason}</p>
          <div className="review-priority">
            Priority: <span className={`priority-${resultData.human_review_details.priority}`}>
              {resultData.human_review_details.priority.toUpperCase()}
            </span>
          </div>
          <div className="required-actions">
            <h4>Required Actions:</h4>
            <ul>
              {resultData.human_review_details.required_actions.map((action, i) => (
                <li key={i}>{action}</li>
              ))}
            </ul>
          </div>
          {resultData.human_review_details.context.validation_errors && (
            <div className="validation-errors">
              <h4>Issues Found:</h4>
              <ul>
                {resultData.human_review_details.context.validation_errors.map((error, i) => (
                  <li key={i}>{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    
    <div className="document-content">
      {/* Document Type */}
      <h2>{analysis.identified_type || "Document"}</h2>
      
      {/* Summary & Key Points */}
      <section className="insights">
        <p className="summary">{insights.summary}</p>
        <ul className="key-points">
          {insights.key_points?.map((point, i) => (
            <li key={i}>{point}</li>
          ))}
        </ul>
      </section>
      
      {/* Discovered Fields (Dynamic) */}
      <section className="extracted-fields">
        <h3>Extracted Information</h3>
        <dl>
          {discoveredFields.map(({ field, value }) => (
            <div key={field}>
              <dt>{field}</dt>
              <dd>{value || 'N/A'}</dd>
            </div>
          ))}
        </dl>
      </section>
      
      {/* Entities */}
      {entities.people?.length > 0 && (
        <section className="entities">
          <h4>People</h4>
          <ul>{entities.people.map((p, i) => <li key={i}>{p}</li>)}</ul>
        </section>
      )}
      
      {/* Dates */}
      {temporal.dates?.length > 0 && (
        <section className="dates">
          <h4>Important Dates</h4>
          <ul>{temporal.dates.map((d, i) => <li key={i}>{d}</li>)}</ul>
        </section>
      )}
      
      {/* Financial Data */}
      {financial.amounts?.length > 0 && (
        <section className="financial">
          <h4>Amounts</h4>
          <ul>
            {financial.amounts.map((amt, i) => (
              <li key={i}>{financial.currencies[i] || ''} {amt}</li>
            ))}
          </ul>
        </section>
      )}
      
      {/* Actions */}
      {insights.action_items?.length > 0 && (
        <section className="actions">
          <h4>Action Items</h4>
          <ul>{insights.action_items.map((a, i) => <li key={i}>{a}</li>)}</ul>
        </section>
      )}
    </div>
  );
}
```

---

## 📊 Example Outputs

### Invoice:
```json
{
  "invoice_number": "ABC123",
  "vendor_name": "TechCorp",
  "total_amount": "5000.00",
  "_insights": { "summary": "Invoice from TechCorp for $5000" },
  "_entities": { "organizations": ["TechCorp", "Acme Inc"] },
  "_temporal": { "dates": ["2024-05-15"], "deadlines": ["2024-06-15"] },
  "_financial": { "amounts": [5000.00], "currencies": ["USD"] }
}
```

### Passport:
```json
{
  "Passport No": "P123456789",
  "Surname": "Smith",
  "Given Names": "John",
  "Nationality": "USA",
  "_insights": { "summary": "US Passport for John Smith" },
  "_entities": { "people": ["John Smith"] },
  "_temporal": { "dates": ["1985-01-15"], "deadlines": ["2030-03-01"] }
}
```

### Driver License:
```json
{
  "DL NO": "D1234567",
  "NAME": "JANE DOE",
  "CLASS": "C",
  "EXPIRY DATE": "2028-06-01",
  "_insights": { "summary": "Class C driver license for Jane Doe" },
  "_entities": { "people": ["JANE DOE"], "locations": ["123 Main St"] },
  "_temporal": { "dates": ["1990-03-15"], "deadlines": ["2028-06-01"] }
}
```

---

## ✅ Key Advantages

1. **No Schema Management** - AI discovers fields automatically
2. **Works with ANY Document** - truly horizontal platform
3. **Self-Learning** - improves with each document processed
4. **Intelligent Orchestration** - Coordinator agent manages workflow
5. **Human-in-the-Loop** - Routes complex cases for review
6. **Audit Trail** - Complete logging of all processing
7. **Business Rules** - Applies custom rules dynamically
8. **Anomaly Detection** - Flags unusual patterns

---

## 🚀 Production Ready

- ✅ Deployed: `https://lyzragent-production.up.railway.app`
- ✅ Dynamic field discovery
- ✅ Self-classifying document types
- ✅ Intelligent extraction without hardcoded schemas
- ✅ Full agentic workflow orchestration
- ✅ LangSmith tracing for observability

**This is a true horizontal, self-learning document processing platform!** 🎯