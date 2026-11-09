from __future__ import annotations

try:
    from tests.helpers import create_application, upload_bank_statement
except ImportError:
    from helpers import create_application, upload_bank_statement


def test_document_upload_and_extraction(client):
    created, headers = create_application(client)
    app_id = created["application"]["id"]

    uploaded = upload_bank_statement(client, app_id, headers)
    assert uploaded["document"]["id"]
    assert uploaded["document"]["document_type"] == "bank_statement"
    assert uploaded["facts_created"] >= 1
