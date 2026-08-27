from pydantic import BaseModel, ConfigDict
from datetime import datetime


# --- User ---
class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Card ---
class CardBase(BaseModel):
    title: str
    description: str = ""


class CardCreate(CardBase):
    column_id: int


class CardOut(CardBase):
    id: int
    position: int
    column_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Column ---
class ColumnBase(BaseModel):
    title: str


class ColumnCreate(ColumnBase):
    board_id: int


class ColumnOut(ColumnBase):
    id: int
    position: int
    board_id: int
    cards: list[CardOut] = []

    model_config = ConfigDict(from_attributes=True)


# --- Board ---
class BoardBase(BaseModel):
    title: str


class BoardCreate(BoardBase):
    pass


class BoardOut(BoardBase):
    id: int
    owner_id: int
    created_at: datetime
    columns: list[ColumnOut] = []

    model_config = ConfigDict(from_attributes=True)

class CardMove(BaseModel):
    new_column_id: int
    new_position: int
