from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.database import get_db
from app import models, schemas
from sqlalchemy.orm import selectinload
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import hash_password, verify_password, create_access_token, get_current_user

from fastapi import WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from app.websocket_manager import manager
from app.config import settings

app = FastAPI(title="Kanban Realtime")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/users", response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(models.User).where(models.User.username == user.username))
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = models.User(username=user.username, hashed_password=hash_password(user.password))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.post("/boards", response_model=schemas.BoardOut)
async def create_board(
    board: schemas.BoardCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_board = models.Board(title=board.title, owner_id=current_user.id)
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
async def create_column(
    column: schemas.ColumnCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
async def create_card(
    card: schemas.CardCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(models.User).where(models.User.username == form_data.username))
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.patch("/cards/{card_id}/move", response_model=schemas.CardOut)
async def move_card(
    card_id: int,
    move: schemas.CardMove,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    card = await db.get(models.Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    old_column_id = card.column_id
    old_position = card.position

    target_column = await db.get(models.Column, move.new_column_id)
    if not target_column:
        raise HTTPException(status_code=404, detail="Target column not found")

    if old_column_id == move.new_column_id:
        # Reordenando dentro da mesma coluna
        if move.new_position > old_position:
            await db.execute(
                update(models.Card)
                .where(
                    models.Card.column_id == old_column_id,
                    models.Card.position > old_position,
                    models.Card.position <= move.new_position,
                    models.Card.id != card_id,
                )
                .values(position=models.Card.position - 1)
            )
        elif move.new_position < old_position:
            await db.execute(
                update(models.Card)
                .where(
                    models.Card.column_id == old_column_id,
                    models.Card.position >= move.new_position,
                    models.Card.position < old_position,
                    models.Card.id != card_id,
                )
                .values(position=models.Card.position + 1)
            )
    else:
        # Movendo para outra coluna
        await db.execute(
            update(models.Card)
            .where(models.Card.column_id == old_column_id, models.Card.position > old_position)
            .values(position=models.Card.position - 1)
        )
        await db.execute(
            update(models.Card)
            .where(models.Card.column_id == move.new_column_id, models.Card.position >= move.new_position)
            .values(position=models.Card.position + 1)
        )

    card.column_id = move.new_column_id
    card.position = move.new_position

    await db.commit()
    await db.refresh(card)
    board_id = target_column.board_id
    await manager.broadcast(board_id, {
        "type": "card_moved",
        "card_id": card.id,
        "old_column_id": old_column_id,
        "new_column_id": card.column_id,
        "new_position": card.position,
    })
    return card

async def get_user_from_token(token: str, db: AsyncSession) -> models.User | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    return await db.scalar(select(models.User).where(models.User.username == username))


@app.websocket("/ws/boards/{board_id}")
async def websocket_board(
    websocket: WebSocket,
    board_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_from_token(token, db)
    if user is None:
        await websocket.close(code=1008)  # policy violation
        return

    board = await db.get(models.Board, board_id)
    if board is None:
        await websocket.close(code=1008)
        return

    await manager.connect(board_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # mantém a conexão viva; ainda não processamos mensagens recebidas
    except WebSocketDisconnect:
        manager.disconnect(board_id, websocket)
