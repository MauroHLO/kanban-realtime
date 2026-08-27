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

        const titleEl = document.createElement("div");
        titleEl.className = "column-title";
        titleEl.textContent = column.title;
        columnEl.appendChild(titleEl);

        const sortedCards = [...column.cards].sort((a, b) => a.position - b.position);

        for (const card of sortedCards) {
            const cardEl = document.createElement("div");
            cardEl.className = "card";
            cardEl.textContent = card.title;
            columnEl.appendChild(cardEl);
        }

        boardEl.appendChild(columnEl);
    }
}
