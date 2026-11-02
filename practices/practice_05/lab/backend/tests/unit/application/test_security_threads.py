import asyncio
import threading
from datetime import UTC, datetime
from unittest.mock import AsyncMock, NonCallableMock, patch

from app.application.dto.login import LoginDTO
from app.application.usecases.auth import AuthUseCase
from app.application.usecases.login import LoginUseCase
from app.domain.entities.credential import CredentialEntity
from app.domain.entities.token import SessionTokenEntity
from app.domain.entities.user import UserEntity
from app.domain.ports.jwt import JwtProviderPort
from app.domain.ports.secret import SecretManagerPort
from app.domain.repositories.credential import CredentialRepository
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository


def test_login_and_auth_offload_sync_security_operations(
        jwt_provider: JwtProviderPort,
        secret_manager: SecretManagerPort) -> None:
    loop_thread = threading.get_ident()
    calls: dict[str, list[int]] = {
        "encode": [], "decode": [], "random": [],
    }
    encode = jwt_provider.encode
    decode = jwt_provider.decode
    generate = secret_manager.generate_random_secret

    def tracked_encode(token: SessionTokenEntity) -> str:
        calls["encode"].append(threading.get_ident())
        return encode(token)

    def tracked_decode(token: str) -> SessionTokenEntity:
        calls["decode"].append(threading.get_ident())
        return decode(token)

    def tracked_generate() -> str:
        calls["random"].append(threading.get_ident())
        return generate()

    async def scenario() -> None:
        now = datetime.now(UTC)
        user = UserEntity(
            email="fan@example.com", username="fan",
            created_at=now, updated_at=now,
        )
        credential = CredentialEntity(
            user_id=user.id, created_at=now,
            password_hash=await secret_manager.hash_secret(
                "password",
            ),
        )
        users = NonCallableMock(spec=UserRepository)
        users.get_by_email.return_value = user
        users.get_by_id.return_value = user
        credentials = NonCallableMock(spec=CredentialRepository)
        credentials.get_current_by_user_id.return_value = credential
        sessions = NonCallableMock(spec=SessionRepository)
        login = LoginUseCase(
            user_repository=users, credential_repository=credentials,
            session_repository=sessions, jwt_provider=jwt_provider,
            secret_manager=secret_manager,
            session_idle_timeout_minutes=30,
        )
        result = await login.login(LoginDTO(
            email=user.email, password="password",
        ))
        session = sessions.create.call_args.args[0]
        assert not hasattr(session, "secret")
        sessions.get_by_id.return_value = session
        commit = AsyncMock()
        auth = AuthUseCase(
            user_repository=users, session_repository=sessions,
            jwt_provider=jwt_provider, secret_manager=secret_manager,
            session_idle_timeout_minutes=30, commit=commit,
        )
        assert (await auth.authenticate(result.token)).id == user.id
        commit.assert_awaited_once()

    with (
        patch.object(jwt_provider, "encode", tracked_encode),
        patch.object(jwt_provider, "decode", tracked_decode),
        patch.object(
            secret_manager, "generate_random_secret",
            tracked_generate,
        ),
    ):
        asyncio.run(scenario())
    for threads in calls.values():
        assert threads and all(t != loop_thread for t in threads)
