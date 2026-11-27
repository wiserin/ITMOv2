from abc import ABC, abstractmethod

from app.domain.entities.token import SessionTokenEntity


class JwtProviderPort(ABC):
    @abstractmethod
    def encode(self, token: SessionTokenEntity) -> str:
        raise NotImplementedError

    @abstractmethod
    def decode(self, token: str) -> SessionTokenEntity:
        raise NotImplementedError
