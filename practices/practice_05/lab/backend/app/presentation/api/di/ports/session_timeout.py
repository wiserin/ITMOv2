from typing import Annotated

from fastapi import Depends


def get_session_idle_timeout() -> int:
    from app.config import app_config

    return app_config.session_idle_timeout_minutes


SessionIdleTimeoutDI = Annotated[
    int, Depends(get_session_idle_timeout),
]
