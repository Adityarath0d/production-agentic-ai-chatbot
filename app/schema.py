from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lets Pydantic read SQLAlchemy objects
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

class ThreadRename(BaseModel):
    title: str = Field(min_length=1, max_length=100)

class MessageOut(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    thread_id : str
    message : str

