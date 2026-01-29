# 🔄 Platform Update - Human Review Metadata

## ✅ **What Changed:**

The API now includes **detailed human review metadata** when a document requires manual approval.

---

## 📡 **Updated Response Structure:**

```json
{
  "success": true,
  "status": "completed",
  "extracted_data": { ... },
  "validated_data": { ... },
  "confidence_scores": { ... },
  
  // NEW: Human review metadata
  "human_review_required": true,  // Boolean flag
  "human_review_details": {
    "review_id": "review_abc123_1234567890",
    "reason": "Low extraction confidence (0.55); Data validation failed (3 errors)",
    "priority": "high",  // high/medium/low
    "required_actions": [
      "verify_extraction",
      "correct_errors", 
      "approve_document"
    ],
    "context": {
      "extraction_confidence": 0.55,
      "validation_errors": [
        "Missing invoice_number",
        "Invalid date format",
        "Amount out of range"
      ],
      "flagged_rules": ["high_value_transaction"],
      "anomalies": ["Unusual vendor name"]
    },
    "due_date": "2024-01-30T18:00:00Z"
  }
}
```

---

## 🎨 **Frontend Implementation:**

### **1. Check for Human Review:**
```javascript
const results = await fetch(`/results/${threadId}`).then(r => r.json());

if (results.human_review_required && results.human_review_details) {
  // Show review UI
  showHumanReviewAlert(results.human_review_details);
}
```

### **2. Display Review Alert:**
```javascript
function HumanReviewAlert({ reviewDetails }) {
  return (
    <div className="review-alert" data-priority={reviewDetails.priority}>
      <div className="alert-header">
        <h3>⚠️ Human Review Required</h3>
        <span className={`priority-badge ${reviewDetails.priority}`}>
          {reviewDetails.priority.toUpperCase()} PRIORITY
        </span>
      </div>
      
      <div className="alert-body">
        <p className="reason">{reviewDetails.reason}</p>
        
        <div className="required-actions">
          <h4>Actions Required:</h4>
          <ul>
            {reviewDetails.required_actions.map((action, i) => (
              <li key={i}>{action.replace(/_/g, ' ')}</li>
            ))}
          </ul>
        </div>
        
        {reviewDetails.context.validation_errors && (
          <div className="issues">
            <h4>Issues Found:</h4>
            <ul className="error-list">
              {reviewDetails.context.validation_errors.map((error, i) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          </div>
        )}
        
        {reviewDetails.context.flagged_rules && (
          <div className="flagged-rules">
            <h4>Business Rules Triggered:</h4>
            <ul>
              {reviewDetails.context.flagged_rules.map((rule, i) => (
                <li key={i}>{rule.replace(/_/g, ' ')}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
      
      <div className="alert-footer">
        <p>Due: {new Date(reviewDetails.due_date).toLocaleString()}</p>
        <button onClick={() => approveDocument(reviewDetails.review_id)}>
          Approve
        </button>
        <button onClick={() => rejectDocument(reviewDetails.review_id)}>
          Reject
        </button>
      </div>
    </div>
  );
}
```

### **3. Example CSS:**
```css
.review-alert {
  border-left: 4px solid var(--warning-color);
  padding: 1rem;
  margin: 1rem 0;
  background: var(--warning-bg);
  border-radius: 4px;
}

.review-alert[data-priority="high"] {
  border-left-color: var(--error-color);
  background: var(--error-bg);
}

.priority-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 600;
}

.priority-badge.high {
  background: #dc3545;
  color: white;
}

.priority-badge.medium {
  background: #ffc107;
  color: #000;
}

.priority-badge.low {
  background: #17a2b8;
  color: white;
}

.error-list li {
  color: var(--error-color);
  padding: 0.25rem 0;
}
```

---

## 🚨 **What Triggers Human Review:**

1. **Low Confidence Scores** (< 0.7):
   - Low extraction confidence
   - Uncertain classification

2. **Validation Failures**:
   - Missing required fields
   - Invalid data formats
   - Data out of expected ranges

3. **Business Rules**:
   - High-value transactions
   - New/unknown vendors
   - Unusual patterns

4. **Anomalies Detected**:
   - Statistical outliers
   - Suspicious patterns
   - Duplicate detection

---

## 📊 **Example Scenarios:**

### **Scenario 1: Low Extraction Confidence**
```json
{
  "human_review_required": true,
  "human_review_details": {
    "reason": "Low extraction confidence (0.45)",
    "priority": "medium",
    "required_actions": ["verify_extraction", "approve_document"],
    "context": {
      "extraction_confidence": 0.45,
      "unclear_fields": ["total_amount", "vendor_name"]
    }
  }
}
```

### **Scenario 2: Validation Errors**
```json
{
  "human_review_required": true,
  "human_review_details": {
    "reason": "Data validation failed (2 errors)",
    "priority": "high",
    "required_actions": ["correct_errors", "revalidate"],
    "context": {
      "validation_errors": [
        "Invoice date is in the future",
        "Total amount exceeds limit"
      ]
    }
  }
}
```

### **Scenario 3: Business Rule Triggered**
```json
{
  "human_review_required": true,
  "human_review_details": {
    "reason": "High-value transaction flagged",
    "priority": "high",
    "required_actions": ["verify_vendor", "approve_amount"],
    "context": {
      "flagged_rules": ["high_value_transaction"],
      "transaction_amount": 50000,
      "approval_threshold": 10000
    }
  }
}
```

---

## ✅ **Implementation Checklist:**

- [ ] Add `human_review_required` check after fetching results
- [ ] Create `HumanReviewAlert` component
- [ ] Display review reason prominently
- [ ] Show all required actions
- [ ] List validation errors/issues
- [ ] Show flagged business rules
- [ ] Display priority badge
- [ ] Add approve/reject buttons
- [ ] Show due date
- [ ] Style based on priority level

---

## 🎯 **Key Benefits:**

1. **Transparency** - Users see exactly why review is needed
2. **Actionable** - Clear list of required actions
3. **Prioritized** - High/medium/low priority indication
4. **Context-Rich** - Full details on issues found
5. **Trackable** - Review ID for audit trail

**The platform now provides complete transparency for human-in-the-loop workflows!** 🚀