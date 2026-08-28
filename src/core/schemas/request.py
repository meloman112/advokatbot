from pydantic import BaseModel


class RequestCreateS(BaseModel):
    user_id: int
    name: str
    phone: str
    text: str


class RequestUpdateS(BaseModel):
    status: str | None = None
    answer: str | None = None
    answered_by: int | None = None
