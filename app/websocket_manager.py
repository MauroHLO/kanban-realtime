from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # board_id -> lista de conexões ativas naquele board
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, board_id: int, websocket: WebSocket):
        await websocket.accept()
        if board_id not in self.active_connections:
            self.active_connections[board_id] = []
        self.active_connections[board_id].append(websocket)

    def disconnect(self, board_id: int, websocket: WebSocket):
        if board_id in self.active_connections:
            self.active_connections[board_id].remove(websocket)
            if not self.active_connections[board_id]:
                del self.active_connections[board_id]

    async def broadcast(self, board_id: int, message: dict):
        if board_id not in self.active_connections:
            return
        for connection in self.active_connections[board_id]:
            await connection.send_json(message)


manager = ConnectionManager()

async def broadcast(self, board_id: int, message: dict):
    if board_id not in self.active_connections:
        return

    dead_connections = []
    for connection in self.active_connections[board_id]:
        try:
            await connection.send_json(message)
        except Exception:
            dead_connections.append(connection)

    for connection in dead_connections:
        self.disconnect(board_id, connection)
