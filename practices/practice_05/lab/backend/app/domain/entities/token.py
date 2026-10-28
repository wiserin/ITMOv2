from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionTokenEntity:
    session_id: UUID
    secret: str = field(repr=False)
    issued_at: datetime
