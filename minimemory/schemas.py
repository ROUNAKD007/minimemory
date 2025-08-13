from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# auth
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# memories
class MemoryCreate(BaseModel):
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    is_long_term: bool = True

class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    is_long_term: Optional[bool] = None

class MemoryOut(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str]
    is_long_term: bool
    created_at: datetime
    owner_id: int
    model_config = ConfigDict(from_attributes=True)
