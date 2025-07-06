from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional

# --- User sheme ---
class UserBase(BaseModel):
    username: str
    email: str
    is_admin: bool = False

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

# --- Login / Token shema ---
class Token(BaseModel):
    access_token: str
    token_type: str

# --- Roba (stock) sheme ---
class StockEntryCreate(BaseModel):
    item_name: str
    quantity: int
    entry_type: Literal["ulaz", "izlaz"]

class StockEntryResponse(BaseModel):
    id: int
    item_name: str
    quantity: int
    entry_type: str
    timestamp: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

