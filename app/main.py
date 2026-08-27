from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app import models, schemas
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

app = FastAPI(title="Kanban Realtime")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/users", response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(models.User).where(models.User.username == user.username))
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = models.User(username=user.username, hashed_password=user.password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.post("/boards", response_model=schemas.BoardOut)
async def create_board(board: schemas.BoardCreate, owner_id: int, db: AsyncSession = Depends(get_db)):
    owner = await db.get(models.User, owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    new_board = models.Board(title=board.title, owner_id=owner_id)
    db.add(new_board)
    await db.commit()
    await db.refresh(new_board, attribute_names=["columns"])
    return new_board


@app.get("/boards/{board_id}", response_model=schemas.BoardOut)
async def get_board(board_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Board)
        .options(selectinload(models.Board.columns).selectinload(models.Column.cards))
        .where(models.Board.id == board_id)
    )
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board

# --- Columns ---
@app.post("/columns", response_model=schemas.ColumnOut)
async def create_column(column: schemas.ColumnCreate, db: AsyncSession = Depends(get_db)):
    board = await db.get(models.Board, column.board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    count = await db.scalar(
        select(func.count()).select_from(models.Column).where(models.Column.board_id == column.board_id)
    )

    new_column = models.Column(title=column.title, board_id=column.board_id, position=count)
    db.add(new_column)
    await db.commit()
    await db.refresh(new_column, attribute_names=["cards"])
    return new_column


# --- Cards ---
@app.post("/cards", response_model=schemas.CardOut)
async def create_card(card: schemas.CardCreate, db: AsyncSession = Depends(get_db)):
    column = await db.get(models.Column, card.column_id)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    count = await db.scalar(
        select(func.count()).select_from(models.Card).where(models.Card.column_id == card.column_id)
    )

    new_card = models.Card(
        title=card.title,
        description=card.description,
        column_id=card.column_id,
        position=count,
    )
    db.add(new_card)
    await db.commit()
    await db.refresh(new_card)
    return new_card
