from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ProviderError,
    ValidationAppError,
)
from app.core.lifecycle import ApplicationStatus, assert_transition
from app.domain.application_state import is_editable_by_applicant
from app.domain.conversation_state import (
    ConversationStage,
    stage_for_status,
)
from app.domain.period import previous_fy_period
from app.domain.provenance import ProvenanceStatus
from app.domain.workflow_i18n import localized_question
from app.models.application import Application
from app.models.conversation_turn import ConversationTurn
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.fact_repository import FactRepository
from app.schemas.clarification import ClarificationOut
from app.schemas.conversation import (
    ConversationOut,
    NextQuestionOut,
    TurnCreate,
    TurnResponse,
)
from app.services.audit_service import AuditService
from app.services.clarification_service import ClarificationService
from app.services.extraction_service import ExtractionService
from app.services.reconciliation_service import ReconciliationService
from app.services.serializers import clarification_out, turn_out

REQUIRED_FIELDS = ("business_type", "annual_sales", "gst_turnover")
FINANCIAL_STAGES = {
    ConversationStage.FINANCIAL_CONTEXT,
    ConversationStage.DOCUMENTS,
    ConversationStage.CLARIFICATIONS,
}
CLOSED_STATUSES = {
    ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
    ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS,
    ApplicationStatus.REVIEW_COMPLETED,
    ApplicationStatus.WITHDRAWN,
    ApplicationStatus.ARCHIVED,
}


class ConversationService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        reasoning,
    ) -> None:
        self.db = db
        self.settings = settings
        self.turns = ConversationRepository(db)
        self.documents = DocumentRepository(db)
        self.facts = FactRepository(db)
        self.audit = AuditService(db)
        self.reconciliation = ReconciliationService(db, settings.reconciliation_tolerance_percent)
        self.clarifications = ClarificationService(db, reasoning)
        self.extraction = ExtractionService(db, reasoning)

    def get_conversation(self, application: Application) -> ConversationOut:
        self._advance(application, actor="system")
        self.db.commit()
        return self._conversation_out(application)

    def submit_turn(
        self, application: Application, payload: TurnCreate, actor: str
    ) -> TurnResponse:
        if not is_editable_by_applicant(application.status):
            raise ConflictError("The conversation is closed for this application")
        if payload.language and payload.language != application.language:
            raise ValidationAppError("The turn language must match the application language")
        self._advance(application, actor="system")

        clarification = None
        if payload.clarification_id:
            clarification = self.turns.get_clarification(payload.clarification_id)
            if clarification is None or clarification.application_id != application.id:
                raise NotFoundError("Clarification not found for this application")
            if clarification.status != "open":
                raise ConflictError("This clarification has already been answered")
            target_field = clarification.field_key
            question_id = f"clarification:{clarification.id}"
            intent = "clarification_answer"
        else:
            next_question = self._next_question(application)
            if next_question is None:
                raise ConflictError(
                    "There is no pending question. Review and submit the application, or "
                    "answer an open clarification."
                )
            if next_question.expected_answer_type == "document":
                raise ValidationAppError(
                    "This step expects a document upload. Use the documents panel instead."
                )
            target_field = next_question.field_key
            question_id = next_question.question_id
            intent = "answer_question"

        turn = ConversationTurn(
            application_id=application.id,
            turn_index=self.turns.next_turn_index(application.id),
            speaker="applicant",
            input_mode=payload.input_mode,
            transcript=payload.text.strip(),
            language=payload.language or application.language,
            intent=intent,
            target_field=target_field,
            question_id=question_id,
            linked_fact_ids=[],
            provider_metadata={
                "stt_request_id": payload.stt_request_id,
                "stt_latency_ms": payload.stt_latency_ms,
                "stt_model": payload.stt_model,
                "transcript_confirmed": payload.confirmed_transcript,
            },
            correction_status=("confirmed" if payload.input_mode == "audio" else "not_required"),
        )
        self.turns.add_turn(turn)

        created_facts = []
        extraction_notes: list[str] = []
        note: str | None = None
        if clarification is not None:
            self.clarifications.mark_answered(clarification, turn.id, actor=actor)
        else:
            targets = self._extraction_targets(application, target_field)
            stage = stage_for_status(application.status)
            period_hint = previous_fy_period() if stage in FINANCIAL_STAGES else None
            try:
                created_facts, extraction_notes = self.extraction.extract_from_turn(
                    application,
                    turn,
                    targets,
                    period_hint=period_hint,
                )
            except ProviderError as exc:
                turn.intent = "extraction_failed"
                note = (
                    "Your answer was saved, but automated extraction is unavailable right now "
                    f"({exc.code}). Please try again or type the value with a clear amount."
                )
                self.audit.record(
                    application_id=application.id,
                    actor=actor,
                    event_type="extraction_failed",
                    summary="The answer was saved but automated extraction failed.",
                    detail={"turn_id": turn.id, "error_code": exc.code},
                )
            if not created_facts and note is None:
                note = (
                    "No new values were extracted. Try including a clear amount, for example "
                    "18 lakh, and confirm the transcript before saving."
                )
        self.audit.record(
            application_id=application.id,
            actor=actor,
            event_type="conversation_turn",
            summary="Applicant answer recorded. Transcript content is not written to audit logs.",
            detail={
                "turn_id": turn.id,
                "turn_index": turn.turn_index,
                "input_mode": turn.input_mode,
                "intent": turn.intent,
                "question_id": turn.question_id,
                "target_field": turn.target_field,
                "facts_created": len(created_facts),
            },
        )
        self._advance(application, actor=actor)
        self.db.commit()
        conversation = self._conversation_out(application, note=note)
        return TurnResponse(
            turn=turn_out(turn),
            facts_created=len(created_facts),
            candidate_field_keys=sorted({fact.field_key for fact in created_facts}),
            extraction_notes=extraction_notes,
            next_question=conversation.next_question,
            conversation=conversation,
        )

    def _workflow(self, application: Application):
        from app.domain.workflow.registry import get_workflow_registry

        workflow_id = getattr(application, "workflow_id", "loan_application")
        version = getattr(application, "workflow_version", 1)
        return get_workflow_registry().get(workflow_id, version)

    def _evaluate_workflow_rules(self, application: Application, wf) -> bool:
        from app.domain.workflow.plugins.registry import get_rule_registry
        from app.models.clarification import Clarification

        rule_registry = get_rule_registry()
        facts = self.facts.list_for_application(application.id, include_rejected=False)
        documents = self.documents.list_for_application(application.id)
        created_any = False

        if "financial_reconciliation" in wf.rules:
            reconciliation = self.reconciliation.build(application)
            known_facts = self.reconciliation.context_fact_payload(application)
            created = self.clarifications.ensure_for_reconciliation(
                application, reconciliation, known_facts, actor="system"
            )
            if created:
                created_any = True

        for rule_name in wf.rules:
            if rule_name == "financial_reconciliation":
                continue
            plugin = rule_registry.get(rule_name)
            if not plugin:
                continue
            eval_result = plugin.evaluate(application, wf, facts, documents)
            for c in eval_result.clarifications:
                if self.turns.open_clarification_for_field(application.id, c.field_key):
                    continue
                if any(
                    existing.field_key == c.field_key
                    for existing in self.turns.list_clarifications(
                        application.id, status="answered"
                    )
                ):
                    continue
                clarification = Clarification(
                    application_id=application.id,
                    field_key=c.field_key,
                    question_text=c.question_text,
                    reason=c.reason,
                    expected_answer_type=c.expected_answer_type,
                    status="open",
                    priority=c.priority,
                    source="workflow_rule",
                    language=application.language,
                )
                self.turns.add_clarification(clarification)
                self.audit.record(
                    application_id=application.id,
                    actor="system",
                    event_type="clarification_created",
                    summary="A clarification question was generated by workflow rule.",
                    detail={
                        "clarification_id": clarification.id,
                        "field_key": c.field_key,
                        "rule": rule_name,
                    },
                )
                created_any = True

        return created_any

    def _advance(self, application: Application, actor: str) -> bool:
        changed = False
        wf = self._workflow(application)

        for _ in range(6):
            status = ApplicationStatus(application.status)
            advanced = False

            # Evaluate transitions defined in the workflow
            if wf.transitions:
                for transition in wf.transitions:
                    if status.value == transition.from_stage:
                        if transition.condition == "all_fields_present":
                            all_met = all(
                                self._active_field(application.id, f) is not None
                                for f in transition.required_fields
                            )
                            if all_met:
                                target = ApplicationStatus(transition.to_stage)
                                self._transition(
                                    application,
                                    target,
                                    actor,
                                    transition.summary or f"Moving to {transition.to_stage}.",
                                )
                                changed = True
                                advanced = True
                                break
                        elif transition.condition == "document_uploaded":
                            all_uploaded = all(
                                self._has_parsed_document(application.id, doc_type)
                                for doc_type in transition.required_documents
                            )
                            if all_uploaded:
                                target = ApplicationStatus(transition.to_stage)
                                self._transition(
                                    application,
                                    target,
                                    actor,
                                    transition.summary or f"Moving to {transition.to_stage}.",
                                )
                                changed = True
                                advanced = True
                                break
                        elif transition.condition == "clarifications_resolved":
                            created = self._evaluate_workflow_rules(application, wf)
                            if created:
                                changed = True
                                break
                            if not self.turns.list_clarifications(application.id, status="open"):
                                target = ApplicationStatus(transition.to_stage)
                                self._transition(
                                    application,
                                    target,
                                    actor,
                                    transition.summary
                                    or "All clarifications resolved; review is ready.",
                                )
                                changed = True
                                advanced = True
                                break
                if advanced:
                    continue

            # Fallback legacy transition handling for default stages
            if status == ApplicationStatus.COLLECTING_BUSINESS_CONTEXT:
                if self._active_field(application.id, "business_type") is not None:
                    self._transition(
                        application,
                        ApplicationStatus.COLLECTING_FINANCIAL_CONTEXT,
                        actor,
                        "Business context captured; moving to financial context.",
                    )
                    changed = True
                    continue
                break
            if status == ApplicationStatus.COLLECTING_FINANCIAL_CONTEXT:
                if (
                    self._active_field(application.id, "annual_sales") is not None
                    and self._active_field(application.id, "gst_turnover") is not None
                ):
                    self._transition(
                        application,
                        ApplicationStatus.COLLECTING_DOCUMENTS,
                        actor,
                        "Financial context captured; moving to document collection.",
                    )
                    changed = True
                    continue
                break
            if status == ApplicationStatus.COLLECTING_DOCUMENTS:
                if self._has_parsed_bank_statement(application.id):
                    self._transition(
                        application,
                        ApplicationStatus.RESOLVING_CLARIFICATIONS,
                        actor,
                        "Bank statement received; checking comparisons for neutral questions.",
                    )
                    changed = True
                    continue
                break
            if status == ApplicationStatus.RESOLVING_CLARIFICATIONS:
                reconciliation = self.reconciliation.build(application)
                known_facts = self.reconciliation.context_fact_payload(application)
                created = self.clarifications.ensure_for_reconciliation(
                    application, reconciliation, known_facts, actor="system"
                )
                if created:
                    changed = True
                    break
                if not self.turns.list_clarifications(application.id, status="open"):
                    self._transition(
                        application,
                        ApplicationStatus.APPLICANT_REVIEW,
                        actor,
                        "No open clarification questions; applicant review is ready.",
                    )
                    changed = True
                    continue
                break
            break
        if changed:
            self.db.flush()
        return changed

    def _transition(
        self,
        application: Application,
        target: ApplicationStatus,
        actor: str,
        summary: str,
    ) -> None:
        previous = application.status
        assert_transition(previous, target)
        application.status = target.value
        self.audit.record(
            application_id=application.id,
            actor=actor,
            event_type="status_changed",
            summary=summary,
            detail={"from": previous, "to": target.value},
        )

    def _next_question(self, application: Application) -> NextQuestionOut | None:
        status = ApplicationStatus(application.status)
        if status in CLOSED_STATUSES:
            return None
        open_clarification = self.turns.next_open_clarification(application.id)
        if open_clarification is not None:
            return NextQuestionOut(
                question_id=f"clarification:{open_clarification.id}",
                field_key=open_clarification.field_key,
                prompt=open_clarification.question_text,
                reason=open_clarification.reason,
                expected_answer_type=open_clarification.expected_answer_type,
                source="clarification",
                clarification_id=open_clarification.id,
            )

        wf = self._workflow(application)
        questions_for_curr_stage = wf.questions_for_stage(status.value)
        if not questions_for_curr_stage:
            stage = stage_for_status(status)
            questions_for_curr_stage = [q for q in wf.questions if q.stage == stage.value]

        for question in questions_for_curr_stage:
            q_id = getattr(question, "id", None) or getattr(question, "question_id", "")
            q_type = getattr(question, "expected_answer_type", "text")
            q_field = getattr(question, "field_key", "")
            q_prompt = getattr(question, "prompt", "")
            q_reason = getattr(question, "reason", "")

            if q_type == "document":
                if not self._has_parsed_document(application.id, q_field):
                    return NextQuestionOut(
                        question_id=q_id,
                        field_key=q_field,
                        prompt=localized_question(
                            q_id,
                            application.language,
                            q_prompt,
                        ),
                        reason=q_reason,
                        expected_answer_type="document",
                        source="workflow",
                    )
            else:
                if self._active_field(application.id, q_field) is None:
                    return NextQuestionOut(
                        question_id=q_id,
                        field_key=q_field,
                        prompt=localized_question(
                            q_id,
                            application.language,
                            q_prompt,
                        ),
                        reason=q_reason,
                        expected_answer_type=q_type,
                        source="workflow",
                    )
        return None

    def _conversation_out(
        self, application: Application, note: str | None = None
    ) -> ConversationOut:
        open_clarifications = self.turns.list_clarifications(application.id, status="open")
        candidate_count = sum(
            1
            for fact in self.facts.list_for_application(application.id, include_rejected=False)
            if fact.provenance_status == ProvenanceStatus.CANDIDATE.value
        )
        status = ApplicationStatus(application.status)
        default_note = None
        if status == ApplicationStatus.APPLICANT_REVIEW:
            default_note = (
                "Review and confirm the extracted values and documents, then submit for "
                "human review. KuralCredit does not make a credit decision."
            )
        elif status == ApplicationStatus.NEEDS_MORE_INFORMATION:
            default_note = (
                "A reviewer requested more information. Answer any open questions, update the "
                "records, and resubmit."
            )
        elif status == ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW:
            default_note = "Submitted for human review. KuralCredit does not make credit decisions."
        elif status in {
            ApplicationStatus.REVIEW_COMPLETED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.ARCHIVED,
        }:
            default_note = "This application is closed."
        combined_note = "; ".join(part for part in (note, default_note) if part) or None
        return ConversationOut(
            application_id=application.id,
            status=application.status,
            stage=stage_for_status(application.status).value,
            turns=[turn_out(turn) for turn in self.turns.list_turns(application.id)],
            next_question=self._next_question(application),
            open_clarifications=[
                clarification_out(clarification) for clarification in open_clarifications
            ],
            candidate_facts_count=candidate_count,
            note=combined_note,
        )

    def _active_field(self, application_id: str, field_key: str):
        return self.facts.latest_for_field(application_id, field_key)

    def _has_parsed_document(self, application_id: str, document_type: str) -> bool:
        return any(
            document.document_type == document_type
            and document.status in {"parsed", "parsed_with_warnings"}
            for document in self.documents.list_for_application(application_id)
        )

    def _has_parsed_bank_statement(self, application_id: str) -> bool:
        return self._has_parsed_document(application_id, "bank_statement")

    def _extraction_targets(self, application: Application, current_field: str) -> list[str]:
        targets: list[str] = []

        def add(field_key: str) -> None:
            if field_key not in targets:
                targets.append(field_key)

        add(current_field)
        wf = self._workflow(application)
        for field_key in wf.required_fields:
            if self._active_field(application.id, field_key) is None:
                add(field_key)
        stage_questions = wf.questions_for_stage(application.status)
        if not stage_questions:
            stage = stage_for_status(application.status)
            stage_questions = [q for q in wf.questions if q.stage == stage.value]
        for question in stage_questions:
            q_field = getattr(question, "field_key", "")
            if self._active_field(application.id, q_field) is None:
                add(q_field)
        return targets


def open_clarification_payloads(
    clarifications: list[ClarificationOut],
) -> list[ClarificationOut]:
    return clarifications
