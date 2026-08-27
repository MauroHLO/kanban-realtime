const API_BASE = "http://localhost:8000";
const BOARD_ID = 1;

const loginScreen = document.getElementById("login-screen");
const boardScreen = document.getElementById("board-screen");
const boardTitle = document.getElementById("board-title");
const boardEl = document.getElementById("board");

document.getElementById("login-btn").addEventListener("click", login);

async function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
    });

    if (!response.ok) {
        alert("Login inválido");
        return;
    }

    const data = await response.json();
    localStorage.setItem("token", data.access_token);

    loginScreen.style.display = "none";
    boardScreen.style.display = "block";

    loadBoard();
    connectWebSocket();
}

async function loadBoard() {
    const token = localStorage.getItem("token");
    const response = await fetch(`${API_BASE}/boards/${BOARD_ID}`, {
        headers: { "Authorization": `Bearer ${token}` },
    });

    if (!response.ok) {
        alert("Erro ao carregar board");
        return;
    }

    const board = await response.json();
    renderBoard(board);
}

function renderBoard(board) {
    boardTitle.textContent = board.title;
    boardEl.innerHTML = "";

    const sortedColumns = [...board.columns].sort((a, b) => a.position - b.position);

    for (const column of sortedColumns) {
        const columnEl = document.createElement("div");
        columnEl.className = "column";
        columnEl.dataset.columnId = column.id;

        const titleEl = document.createElement("div");
        titleEl.className = "column-title";
        titleEl.textContent = column.title;
        columnEl.appendChild(titleEl);

        const sortedCards = [...column.cards].sort((a, b) => a.position - b.position);

        for (const card of sortedCards) {
            const cardEl = document.createElement("div");
            cardEl.className = "card";
            cardEl.textContent = card.title;
            cardEl.draggable = true;
            cardEl.dataset.cardId = card.id;

            cardEl.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("text/plain", card.id);
            });

            columnEl.appendChild(cardEl);
        }

        columnEl.addEventListener("dragover", (e) => {
            e.preventDefault(); // necessário para permitir o drop
        });

        columnEl.addEventListener("drop", (e) => {
            e.preventDefault();
            const cardId = e.dataTransfer.getData("text/plain");
            const newColumnId = column.id;
            const newPosition = column.cards.length; // solta sempre no final, por simplicidade
            moveCard(cardId, newColumnId, newPosition);
        });

        boardEl.appendChild(columnEl);
    }
}

let ws = null;

function connectWebSocket() {
    const token = localStorage.getItem("token");
    ws = new WebSocket(`ws://localhost:8000/ws/boards/${BOARD_ID}?token=${token}`);

    ws.onopen = () => console.log("WebSocket conectado");

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Evento recebido:", data);
        loadBoard();
    };

    ws.onclose = () => console.log("WebSocket desconectado");
    ws.onerror = (error) => console.error("Erro WebSocket:", error);
}

async function moveCard(cardId, newColumnId, newPosition) {
    const token = localStorage.getItem("token");
    await fetch(`${API_BASE}/cards/${cardId}/move`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ new_column_id: parseInt(newColumnId), new_position: newPosition }),
    });
}
