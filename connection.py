from pydantic import BaseModel, Field


class Connection(BaseModel):
    origin: str
    to: str
    max_link_capacity: int = Field(default=1, ge=1)
    extra_step: bool = Field(default=False)
