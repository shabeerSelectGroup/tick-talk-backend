from pydantic import BaseModel, Field


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(..., max_length=512)
    keys: dict[str, str]


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(..., max_length=512)


class PushVapidOut(BaseModel):
    public_key: str
    enabled: bool
