from abc import ABC, abstractmethod


class SecretManagerPort(ABC):
    @abstractmethod
    async def hash_secret(self, raw_secret: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def verify_secret(
            self,
            raw_secret: str,
            hashed_secret: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def generate_random_secret(self, nbytes: int = 32) -> str:
        raise NotImplementedError
