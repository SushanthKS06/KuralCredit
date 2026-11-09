from __future__ import annotations

from app.domain.workflow.schema import (
    WorkflowDefinition,
    WorkflowDocumentProfile,
    WorkflowFieldDefinition,
    WorkflowQuestionDefinition,
    WorkflowStageDefinition,
    WorkflowStateTransition,
)

LOAN_APPLICATION_WORKFLOW = WorkflowDefinition(
    workflow_id="loan_application",
    workflow_version=1,
    display_name="MSME Loan Application Clarification",
    description=(
        "Voice-first multilingual loan-application clarification, document reconciliation, "
        "and evidence preparation for MSME working capital loans. Prepares human reviewer packets."
    ),
    category="lending",
    supported_languages=["en-IN", "ta-IN", "hi-IN", "te-IN", "kn-IN"],
    input_modes=["audio", "text"],
    stages=[
        WorkflowStageDefinition(
            id="collecting_business_context",
            label="Business Context",
            description="Collects business activity, type, and operating history.",
            order=1,
        ),
        WorkflowStageDefinition(
            id="collecting_financial_context",
            label="Financial Context",
            description="Captures applicant-declared sales and GST-reported turnover.",
            order=2,
        ),
        WorkflowStageDefinition(
            id="collecting_documents",
            label="Supporting Documents",
            description="Collects bank statements and GST summaries for verification.",
            order=3,
        ),
        WorkflowStageDefinition(
            id="resolving_clarifications",
            label="Clarifications",
            description="Asks neutral follow-up questions when financial figures require context.",
            order=4,
        ),
        WorkflowStageDefinition(
            id="applicant_review",
            label="Applicant Review",
            description="Allows applicant to review, correct, and confirm all extracted facts.",
            order=5,
        ),
        WorkflowStageDefinition(
            id="submitted_for_human_review",
            label="Human Review Queue",
            description="Routed to human credit officer for review. No automated decision is made.",
            order=6,
        ),
    ],
    initial_stage="collecting_business_context",
    fields=[
        WorkflowFieldDefinition(
            id="business_name",
            label="Registered business name",
            type="string",
            required=True,
            description="Official legal or trade name of the enterprise.",
            measure_type="business_context",
        ),
        WorkflowFieldDefinition(
            id="business_type",
            label="Business type",
            type="string",
            required=True,
            description="Nature of business, products sold, and primary business activity.",
            measure_type="business_context",
        ),
        WorkflowFieldDefinition(
            id="years_in_operation",
            label="Years in operation",
            type="number",
            required=False,
            description="Number of years the business has been in active commercial operation.",
            measure_type="business_context",
        ),
        WorkflowFieldDefinition(
            id="annual_sales",
            label="Applicant-declared annual sales",
            type="money",
            required=True,
            description="Total sales reported by applicant for previous financial year.",
            measure_type="declared_sales",
            default_period="previous_fy",
        ),
        WorkflowFieldDefinition(
            id="gst_turnover",
            label="GST-reported turnover",
            type="money",
            required=True,
            description="Turnover reported in statutory GST returns for previous financial year.",
            measure_type="gst_turnover",
            default_period="previous_fy",
        ),
        WorkflowFieldDefinition(
            id="cash_sales",
            label="Cash sales",
            type="money",
            required=False,
            description="Portion of annual sales transacted in physical cash.",
            measure_type="cash_sales",
            default_period="previous_fy",
        ),
        WorkflowFieldDefinition(
            id="sales_register_total",
            label="Sales register total",
            type="money",
            required=False,
            description="Total from internal point-of-sale or accounting register.",
            measure_type="sales_register_total",
            default_period="previous_fy",
        ),
        WorkflowFieldDefinition(
            id="bank_credits",
            label="Bank statement credits",
            type="money",
            required=True,
            description="Total deposits into current account. Caveat: not revenue.",
            measure_type="bank_credit",
            source_type="bank_statement",
        ),
    ],
    questions=[
        WorkflowQuestionDefinition(
            id="q_business_type",
            field_key="business_type",
            stage="collecting_business_context",
            prompt="What kind of business do you run, and what do you mainly sell?",
            reason="A reviewer needs to understand the business before reading records.",
            expected_answer_type="text",
            priority=10,
        ),
        WorkflowQuestionDefinition(
            id="q_years_in_operation",
            field_key="years_in_operation",
            stage="collecting_business_context",
            prompt="How many years has the business been operating?",
            reason="Business age helps a reviewer interpret the records in context.",
            expected_answer_type="number",
            priority=20,
        ),
        WorkflowQuestionDefinition(
            id="q_annual_sales",
            field_key="annual_sales",
            stage="collecting_financial_context",
            prompt=(
                "What were your total sales in the last financial year, April 2025 to March 2026? "
                "You can say an amount like 18 lakh."
            ),
            reason="Declared sales are compared with GST and bank records using explicit rules.",
            expected_answer_type="amount",
            priority=30,
        ),
        WorkflowQuestionDefinition(
            id="q_gst_turnover",
            field_key="gst_turnover",
            stage="collecting_financial_context",
            prompt="What turnover was reported in your GST returns for the same year?",
            reason="GST turnover is a separate measure and may differ from total sales.",
            expected_answer_type="amount",
            priority=40,
        ),
        WorkflowQuestionDefinition(
            id="q_bank_statement",
            field_key="bank_statement",
            stage="collecting_documents",
            prompt=(
                "Please upload a bank statement for the same period. CSV, XLSX, or a text-based "
                "PDF is supported."
            ),
            reason="Bank credits help a reviewer compare records and are not treated as revenue.",
            expected_answer_type="document",
            priority=50,
        ),
    ],
    document_profiles=[
        WorkflowDocumentProfile(
            id="bank_statement",
            label="Bank statement",
            required=True,
            accepted_formats=["pdf", "csv", "xlsx"],
            description="Official bank statement covering the relevant financial period.",
            parser="bank_statement_table",
        ),
        WorkflowDocumentProfile(
            id="gst_summary",
            label="GST summary return",
            required=False,
            accepted_formats=["pdf", "csv", "xlsx"],
            description="GSTR-3B or annual summary filing.",
            parser="table",
        ),
    ],
    transitions=[
        WorkflowStateTransition(
            from_stage="collecting_business_context",
            to_stage="collecting_financial_context",
            condition="all_fields_present",
            required_fields=["business_type"],
            summary="Business context captured; moving to financial context.",
        ),
        WorkflowStateTransition(
            from_stage="collecting_financial_context",
            to_stage="collecting_documents",
            condition="all_fields_present",
            required_fields=["annual_sales", "gst_turnover"],
            summary="Financial context captured; moving to document collection.",
        ),
        WorkflowStateTransition(
            from_stage="collecting_documents",
            to_stage="resolving_clarifications",
            condition="document_uploaded",
            required_documents=["bank_statement"],
            summary="Bank statement received; checking comparisons for neutral questions.",
        ),
        WorkflowStateTransition(
            from_stage="resolving_clarifications",
            to_stage="applicant_review",
            condition="clarifications_resolved",
            summary="No open clarification questions; applicant review is ready.",
        ),
    ],
    rules=["financial_reconciliation"],
    completion_criteria={
        "required_fields": [
            "business_name",
            "business_type",
            "annual_sales",
            "gst_turnover",
            "bank_credits",
        ],
        "required_documents": ["bank_statement"],
        "require_clarifications_resolved": True,
    },
    human_review_required=True,
    consent_version="2026-02-consent-v1",
    consent_notice=(
        "I consent to the collection of declared business facts, voice processing via Gnani, "
        "and structured evidence preparation for a human credit officer."
    ),
    feature_flags={
        "enable_voice_interview": True,
        "enable_document_upload": True,
        "enable_reconciliation": True,
    },
)
