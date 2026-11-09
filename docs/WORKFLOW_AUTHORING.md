# Workflow Authoring Guide

This guide details how developers and domain engineers can create, validate, and register new voice-first conversational workflows on the KuralCredit platform without modifying the core conversation orchestration engine.

---

## 1. Workflow Architecture Overview

A workflow in KuralCredit is a self-contained, versioned declarative structure that specifies:
1. **Stages**: The conversational and operational lifecycle of the session.
2. **Fields**: The structured data items to extract from speech and documents.
3. **Questions**: The stage-linked prompt questions and localized translations.
4. **Document Profiles**: The synthetic or operational records accepted for reconciliation.
5. **Rule Plugins**: Deterministic logic executed on extracted facts and documents.

```
Workflow Definition
  ├── Metadata (id, name, version, domain)
  ├── Stages (ordered progression)
  ├── Fields (schema, data types, extraction hints)
  ├── Questions (templates, localized strings)
  ├── Document Profiles (expected records, parsing keys)
  ├── State Transitions (permitted status changes)
  └── Rule Plugins (pluggable deterministic business logic)
```

---

## 2. The `WorkflowDefinition` Schema

All workflows must conform to the `WorkflowDefinition` schema defined in `backend/app/domain/workflow/schema.py`:

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

class WorkflowFieldDefinition(BaseModel):
    key: str
    label: str
    data_type: Literal["string", "currency", "scale_unit", "categorical", "boolean", "date"]
    required: bool = True
    description: Optional[str] = None
    extraction_hint: Optional[str] = None
    synonyms: List[str] = Field(default_factory=list)
    allowed_values: Optional[List[str]] = None

class WorkflowQuestionDefinition(BaseModel):
    id: str
    field_key: Optional[str] = None
    stage: str
    text_template: str
    purpose: str
    required: bool = True
    order: int = 0
    translations: Dict[str, str] = Field(default_factory=dict)

class WorkflowDocumentProfile(BaseModel):
    document_type: str
    label: str
    required: bool = False
    allowed_extensions: List[str] = Field(default_factory=lambda: [".csv", ".pdf", ".txt"])
    extracted_fields: List[str] = Field(default_factory=list)

class WorkflowStageDefinition(BaseModel):
    id: str
    label: str
    order: int
    is_terminal: bool = False

class WorkflowDefinition(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    domain: str
    description: str
    stages: List[WorkflowStageDefinition]
    fields: List[WorkflowFieldDefinition]
    questions: List[WorkflowQuestionDefinition]
    document_profiles: List[WorkflowDocumentProfile] = Field(default_factory=list)
    rule_plugins: List[str] = Field(default_factory=list)
```

---

## 3. Step-by-Step Workflow Authoring Walkthrough

### Step 1: Define the Workflow Specification
Create a new Python module in `backend/app/domain/workflow/definitions/` (e.g. `customer_support_intake.py`):

```python
from backend.app.domain.workflow.schema import (
    WorkflowDefinition,
    WorkflowFieldDefinition,
    WorkflowQuestionDefinition,
    WorkflowStageDefinition,
)

CUSTOMER_SUPPORT_WORKFLOW = WorkflowDefinition(
    id="customer_support_intake",
    name="Customer Support Intake",
    version="1.0.0",
    domain="customer_operations",
    description="Cross-domain voice workflow for triaging customer issues and support tickets.",
    stages=[
        WorkflowStageDefinition(id="collecting_issue_details", label="Issue Description", order=1),
        WorkflowStageDefinition(id="collecting_triage_context", label="Triage & Priority", order=2),
        WorkflowStageDefinition(id="resolving_clarifications", label="Clarifications", order=3),
        WorkflowStageDefinition(id="applicant_review", label="Summary Review", order=4),
        WorkflowStageDefinition(id="submitted_for_human_review", label="Submitted", order=5, is_terminal=True),
    ],
    fields=[
        WorkflowFieldDefinition(
            key="product_or_service",
            label="Product / Service",
            data_type="string",
            required=True,
            extraction_hint="Product or service name",
            synonyms=["product", "software", "service", "hardware", "portal"]
        ),
        WorkflowFieldDefinition(
            key="issue_summary",
            label="Issue Summary",
            data_type="string",
            required=True,
            extraction_hint="Summary of problem experienced",
            synonyms=["problem", "error", "bug", "fault", "outage"]
        ),
        WorkflowFieldDefinition(
            key="urgency_level",
            label="Urgency Level",
            data_type="categorical",
            required=True,
            allowed_values=["low", "medium", "high", "critical"],
            synonyms=["severity", "urgency", "priority"]
        ),
    ],
    questions=[
        WorkflowQuestionDefinition(
            id="q_product_or_service",
            field_key="product_or_service",
            stage="collecting_issue_details",
            text_template="Which product or service are you encountering an issue with?",
            purpose="Identify affected product or service",
            order=1,
            translations={
                "ta-IN": "நீங்கள் எந்த தயாரிப்பு அல்லது சேவையில் சிக்கலை எதிர்கொள்கிறீர்கள்?",
                "hi-IN": "आप किस उत्पाद या सेवा में समस्या का सामना कर रहे हैं?",
            }
        ),
        WorkflowQuestionDefinition(
            id="q_issue_summary",
            field_key="issue_summary",
            stage="collecting_issue_details",
            text_template="Could you briefly describe the issue or error you are experiencing?",
            purpose="Extract core issue description",
            order=2,
        ),
        WorkflowQuestionDefinition(
            id="q_urgency",
            field_key="urgency_level",
            stage="collecting_triage_context",
            text_template="What is the severity or urgency of this issue: low, medium, high, or critical?",
            purpose="Determine triage urgency",
            order=3,
        ),
    ],
    rule_plugins=["support_triage_plugin"],
)
```

### Step 2: (Optional) Implement a Domain Rule Plugin
If your workflow requires deterministic validation or reconciliation rules, implement a plugin under `backend/app/domain/workflow/plugins/`:

```python
from backend.app.domain.workflow.plugins.base import WorkflowRulePlugin, PluginEvaluationResult

class SupportTriagePlugin(WorkflowRulePlugin):
    @property
    def plugin_name(self) -> str:
        return "support_triage_plugin"

    def evaluate(self, application, facts, documents, context) -> PluginEvaluationResult:
        findings = []
        urgency = next((f.normalized_value for f in facts if f.field_key == "urgency_level"), "medium")
        if urgency == "critical":
            findings.append("Ticket marked as CRITICAL - 2-hour SLA response required")
        return PluginEvaluationResult(status="passed", findings=findings)
```

### Step 3: Register the Workflow in `WorkflowRegistry`
In `backend/app/domain/workflow/registry.py`:
```python
from backend.app.domain.workflow.definitions.customer_support_intake import CUSTOMER_SUPPORT_WORKFLOW

def _register_builtin_workflows(self):
    self.register(LOAN_APPLICATION_WORKFLOW)
    self.register(CUSTOMER_SUPPORT_WORKFLOW)
```

---

## 4. Validating Workflow Definitions

The platform provides a validation API endpoint to verify workflow schemas without restarting services:

```http
POST /api/v1/workflows/validate
Content-Type: application/json

{
  "id": "my_custom_workflow",
  "name": "Custom Intake",
  "version": "1.0.0",
  "domain": "operations",
  "description": "Custom workflow definition",
  "stages": [...],
  "fields": [...],
  "questions": [...]
}
```

Response:
```json
{
  "valid": true,
  "workflow_id": "my_custom_workflow",
  "errors": []
}
```

---

## 5. Reference Implementations in Codebase

| Workflow ID | Domain | Stages | Required Fields | Rule Plugin |
|---|---|---|---|---|
| `loan_application` | MSME Lending | 6 stages | `annual_sales`, `peak_season_monthly_sales`, `lean_season_monthly_sales`, `gst_registered` | `financial_reconciliation_plugin` |
| `customer_support_intake` | Customer Ops | 5 stages | `product_or_service`, `issue_summary`, `urgency_level` | `support_triage_plugin` |

