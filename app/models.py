from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    boards_owned: Mapped[list["Board"]] = relationship(back_populates="owner")
    memberships: Mapped[list["BoardMembership"]] = relationship(back_populates="user")


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner: Mapped["User"] = relationship(back_populates="boards_owned")
    columns: Mapped[list["Column"]] = relationship(back_populates="board", cascade="all, delete-orphan")
    memberships: Mapped[list["BoardMembership"]] = relationship(back_populates="board", cascade="all, delete-orphan")


class BoardMembership(Base):
    __tablename__ = "board_memberships"
    __table_args__ = (UniqueConstraint("board_id", "user_id", name="uq_board_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    board: Mapped["Board"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


class Column(Base):
    __tablename__ = "columns"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(Integer)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id"))

    board: Mapped["Board"] = relationship(back_populates="columns")
    cards: Mapped[list["Card"]] = relationship(back_populates="column", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(1000), default="")
    position: Mapped[int] = mapped_column(Integer)
    column_id: Mapped[int] = mapped_column(ForeignKey("columns.id"))

    column: Mapped["Column"] = relationship(back_populates="cards")
