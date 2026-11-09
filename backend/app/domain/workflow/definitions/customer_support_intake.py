from __future__ import annotations

from app.domain.workflow.schema import (
    WorkflowDefinition,
    WorkflowDocumentProfile,
    WorkflowFieldDefinition,
    WorkflowQuestionDefinition,
    WorkflowStageDefinition,
    WorkflowStateTransition,
)

CUSTOMER_SUPPORT_INTAKE_WORKFLOW = WorkflowDefinition(
    workflow_id="customer_support_intake",
    workflow_version=1,
    display_name="Customer Support Intake & Triage",
    description=(
        "Voice-first customer support request intake, automated symptom capture, "
        "triage categorization, and human support agent packet preparation."
    ),
    category="customer_support",
    supported_languages=["en-IN", "ta-IN", "hi-IN"],
    input_modes=["audio", "text"],
    stages=[
        WorkflowStageDefinition(
            id="collecting_issue_details",
            label="Issue Details",
            description="Collects description of the customer issue and product/service affected.",
            order=1,
        ),
        WorkflowStageDefinition(
            id="collecting_triage_context",
            label="Triage & Contact",
            description="Captures urgency level, contact method, and troubleshooting steps.",
            order=2,
        ),
        WorkflowStageDefinition(
            id="collecting_documents",
            label="Attachments & Logs",
            description="Collects optional error screenshots, receipts, or diagnostic logs.",
            order=3,
        ),
        WorkflowStageDefinition(
            id="resolving_clarifications",
            label="Clarifications",
            description="Resolves any missing symptom context before routing to support.",
            order=4,
        ),
        WorkflowStageDefinition(
            id="applicant_review",
            label="Customer Review",
            description="Allows the customer to review and confirm their ticket details.",
            order=5,
        ),
        WorkflowStageDefinition(
            id="submitted_for_human_review",
            label="Support Queue",
            description="Routed to a customer support specialist for triage and resolution.",
            order=6,
        ),
    ],
    initial_stage="collecting_issue_details",
    fields=[
        WorkflowFieldDefinition(
            id="customer_issue",
            label="Issue description",
            type="text",
            required=True,
            description="Detailed explanation of the issue or problem being faced.",
            measure_type="issue_context",
        ),
        WorkflowFieldDefinition(
            id="product_or_service",
            label="Product or service affected",
            type="string",
            required=True,
            description="Name of the product, subscription, or service experiencing the issue.",
            measure_type="product_context",
        ),
        WorkflowFieldDefinition(
            id="urgency",
            label="Urgency level",
            type="enum",
            required=True,
            allowed_values=["low", "medium", "high", "critical"],
            description="Customer-declared urgency of the request.",
            measure_type="triage_context",
        ),
        WorkflowFieldDefinition(
            id="preferred_contact_method",
            label="Preferred contact channel",
            type="enum",
            required=True,
            allowed_values=["phone", "email", "callback"],
            description="Channel by which the customer wishes to be reached.",
            measure_type="contact_context",
        ),
        WorkflowFieldDefinition(
            id="steps_already_tried",
            label="Troubleshooting steps tried",
            type="text",
            required=False,
            description="Actions or remedies already attempted by the customer.",
            measure_type="troubleshooting_context",
        ),
    ],
    questions=[
        WorkflowQuestionDefinition(
            id="q_customer_issue",
            field_key="customer_issue",
            stage="collecting_issue_details",
            prompt="Could you describe the issue you are experiencing with our service?",
            reason="Support specialists require symptom description to triage the ticket.",
            expected_answer_type="text",
            priority=10,
        ),
        WorkflowQuestionDefinition(
            id="q_product_or_service",
            field_key="product_or_service",
            stage="collecting_issue_details",
            prompt="Which product, subscription, or service is this regarding?",
            reason="Ensures the ticket is routed to the corresponding engineering or support pod.",
            expected_answer_type="text",
            priority=20,
        ),
        WorkflowQuestionDefinition(
            id="q_urgency",
            field_key="urgency",
            stage="collecting_triage_context",
            prompt="How urgent is this issue: low, medium, high, or critical?",
            reason="Determines triage SLA and escalation priority for support dispatch.",
            expected_answer_type="choice",
            priority=30,
        ),
        WorkflowQuestionDefinition(
            id="q_preferred_contact_method",
            field_key="preferred_contact_method",
            stage="collecting_triage_context",
            prompt="How should our support team contact you: phone, email, or callback?",
            reason="Specifies communication channel for updates and troubleshooting.",
            expected_answer_type="choice",
            priority=40,
        ),
        WorkflowQuestionDefinition(
            id="q_steps_already_tried",
            field_key="steps_already_tried",
            stage="collecting_triage_context",
            prompt="What troubleshooting steps have you already tried, if any?",
            reason="Prevents repeating troubleshooting actions that have already failed.",
            expected_answer_type="text",
            priority=50,
        ),
    ],
    document_profiles=[
        WorkflowDocumentProfile(
            id="support_log_or_screenshot",
            label="Screenshot or error log",
            required=False,
            accepted_formats=["pdf", "csv", "xlsx", "txt"],
            description="Optional screenshot, log, or receipt illustrating the issue.",
            parser="text",
        ),
    ],
    transitions=[
        WorkflowStateTransition(
            from_stage="collecting_issue_details",
            to_stage="collecting_triage_context",
            condition="all_fields_present",
            required_fields=["customer_issue", "product_or_service"],
            summary="Issue details captured; moving to triage and contact preference.",
        ),
        WorkflowStateTransition(
            from_stage="collecting_triage_context",
            to_stage="resolving_clarifications",
            condition="all_fields_present",
            required_fields=["urgency", "preferred_contact_method"],
            summary="Triage preferences captured; evaluating need for clarifications.",
        ),
        WorkflowStateTransition(
            from_stage="resolving_clarifications",
            to_stage="applicant_review",
            condition="clarifications_resolved",
            summary="Clarifications resolved; ticket summary ready for customer review.",
        ),
    ],
    rules=["support_triage"],
    completion_criteria={
        "required_fields": [
            "customer_issue",
            "product_or_service",
            "urgency",
            "preferred_contact_method",
        ],
        "required_documents": [],
        "require_clarifications_resolved": True,
    },
    human_review_required=True,
    consent_version="2026-support-v1",
    consent_notice=(
        "I consent to the recording of my support issue and contact preferences for processing "
        "by our technical support team."
    ),
    feature_flags={
        "enable_voice_interview": True,
        "enable_document_upload": True,
        "enable_reconciliation": False,
    },
)
