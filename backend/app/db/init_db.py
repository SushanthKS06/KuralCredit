from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.session import get_engine
from app.models import Base


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())

        if "applications" in tables:
            cols = {c["name"] for c in inspector.get_columns("applications")}
            if "workflow_id" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE applications ADD COLUMN workflow_id "
                        "VARCHAR(60) DEFAULT 'loan_application'"
                    )
                )
            if "workflow_version" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE applications ADD COLUMN workflow_version "
                        "INTEGER DEFAULT 1"
                    )
                )
            conn.execute(
                text(
                    "UPDATE applications SET workflow_version = 1 "
                    "WHERE workflow_version IS NULL OR workflow_version IN ('1.0.0', '1', '1.0')"
                )
            )

        if "sessions" in tables:
            cols = {c["name"] for c in inspector.get_columns("sessions")}
            if "workflow_id" not in cols:
                conn.execute(
                    text("ALTER TABLE sessions ADD COLUMN workflow_id VARCHAR(60)")
                )

