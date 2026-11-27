from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ErrorResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    error: str
    message: str
    details: dict[str, JsonValue] = Field(default_factory=dict)
