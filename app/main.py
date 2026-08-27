from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app import models, schemas
from sqlalchemy import select
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
        .options(selectinload(models.Board.columns))
        .where(models.Board.id == board_id)
    )
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board
