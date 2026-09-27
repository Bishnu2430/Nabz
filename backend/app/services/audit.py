"""Append-only audit trail (FR-37). Records who did what to which entity; never health values."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(session: Session, actor: uuid.UUID | None, action: str, entity_type: str,
           entity_id: uuid.UUID | None = None, **meta: Any) -> None:
    session.add(AuditLog(actor_user_id=actor, action=action, entity_type=entity_type, entity_id=entity_id,
                         meta=meta or None))
