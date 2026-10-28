from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    def __repr__(self) -> str:
        values = ', '.join(
            f"{col.name}={getattr(self, col.name)!r}"
            for col in self.__table__.primary_key.columns
        )
        return f"<{self.__class__.__name__}({values})>"
    

    def __str__(self) -> str:
        return self.__repr__()
