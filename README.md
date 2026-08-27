# Kanban Realtime

![Python](https://img.shields.io/badge/Python-3.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%20async-red)
![WebSocket](https://img.shields.io/badge/WebSocket-native-black)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

Quadro Kanban colaborativo com atualização em tempo real via WebSocket. Múltiplos usuários conectados ao mesmo board veem cards sendo criados e movidos instantaneamente, sem recarregar a página.

## O problema

Ferramentas de gestão de tarefas colaborativas (Trello, Jira, etc.) resolvem um problema técnico específico: manter várias sessões de cliente sincronizadas com o mesmo estado, em tempo real, sem que cada usuário precise atualizar a página manualmente para ver o que os outros fizeram.

Este projeto implementa esse mecanismo do zero — sem framework de real-time pronto (Socket.IO, Django Channels) — para entender e demonstrar o problema de sincronização de estado por trás dele: gerenciar conexões WebSocket ativas por sala, propagar eventos de forma consistente, e lidar com o que acontece quando uma conexão cai no meio do processo.

## Como funciona

A API REST (FastAPI + SQLAlchemy assíncrono) é a única fonte de verdade: toda escrita (criar coluna, criar card, mover card) passa primeiro pelo banco PostgreSQL, dentro de uma transação. Só depois de a escrita ser confirmada, um evento é propagado via WebSocket para todos os clientes conectados àquele board — o WebSocket nunca é usado para persistir dado, apenas para notificar.

Cada cliente mantém uma conexão WebSocket por board (`/ws/boards/{board_id}`), autenticada via JWT passado como query parameter. Um `ConnectionManager` em memória mantém o registro de quais conexões estão ativas em cada board e faz o broadcast das mensagens.

O frontend (HTML/CSS/JS puro, sem framework) consome a API REST para carregar o estado inicial do board e escuta o WebSocket para se manter atualizado. Ao receber qualquer evento (`card_moved`, `card_created`, `column_created`), a estratégia adotada é recarregar o board inteiro via REST — mais simples de implementar e depurar do que reconciliar o DOM manualmente, com um custo de performance irrelevante na escala de um board pessoal.

Cards podem ser arrastados entre colunas via HTML5 Drag and Drop API nativa, disparando o endpoint de movimentação, que por sua vez propaga o evento para os demais clientes.

## Decisões técnicas

**Posição por inteiro sequencial, não fracionária.** Cada card e coluna guarda um campo `position` inteiro. Mover um item exige reindexar os vizinhos afetados (decrementar quem ficou entre a posição antiga e a nova, ou o inverso) em vez de apenas escrever um novo valor de posição fracionária. A escolha prioriza previsibilidade e facilidade de depuração — os valores de posição são sempre uma sequência limpa (0, 1, 2, ...), sem acúmulo de casas decimais ao longo de sucessivos reordenamentos. O custo é uma operação de `UPDATE` em lote a cada movimentação, que em SQL é uma única query, não um laço.

**SQLAlchemy assíncrono, não síncrono.** Diferente dos dois projetos anteriores do portfólio, aqui o banco é acessado de forma assíncrona (`asyncpg` + `AsyncSession`). A justificativa é técnica, não estética: o `ConnectionManager` do WebSocket roda dentro do mesmo event loop assíncrono do FastAPI, gerenciando múltiplas conexões simultâneas. Uma chamada de banco síncrona bloquearia esse event loop inteiro durante a consulta, travando o broadcast para os demais clientes conectados naquele instante — inaceitável em um sistema pensado para tempo real, mesmo em baixa escala.

Uma consequência direta dessa escolha: relações do SQLAlchemy (`relationship`) não podem ser carregadas de forma implícita (lazy loading) em contexto assíncrono — tentar isso lança `MissingGreenlet`. Toda relação usada na resposta da API é carregada explicitamente, via `selectinload` em consultas ou `refresh(attribute_names=[...])` em objetos recém-criados.

**Autenticação de WebSocket via query parameter.** Conexões WebSocket não suportam o header `Authorization` da forma que requisições HTTP tradicionais fazem. O token JWT é passado como query parameter na URL de conexão (`?token=...`) e validado manualmente antes de aceitar o handshake — se inválido, a conexão é recusada com o código de fechamento `1008` (policy violation).

**Banco como única fonte de verdade, WebSocket como canal de notificação.** Nenhuma lógica de negócio depende do WebSocket estar funcionando. Se a conexão de um cliente cair, a próxima vez que ele carregar a página via REST verá o estado real e atualizado — o WebSocket apenas acelera essa atualização para os clientes que seguem conectados.

**Conexões mortas não interrompem o broadcast.** Se o envio de uma mensagem a um cliente desconectado abruptamente lançar exceção, o `ConnectionManager` captura o erro, remove essa conexão do registro, e continua o envio aos demais — testado forçando o fechamento abrupto de uma aba durante um broadcast ativo.

## Funcionalidades

- Autenticação via JWT (registro, login, rotas protegidas)
- CRUD de boards, colunas e cards via API REST
- Movimentação de cards entre colunas e reordenação dentro da mesma coluna, com reindexação automática dos itens afetados
- Atualização em tempo real via WebSocket para todos os clientes conectados a um board
- Interface Kanban funcional com drag and drop nativo (HTML5)
- Containerização completa (aplicação + banco) via Docker Compose

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (assíncrono), Alembic, python-jose (JWT), passlib + bcrypt
- **Banco:** PostgreSQL 17, driver asyncpg
- **Frontend:** HTML, CSS e JavaScript puros, WebSocket API nativa, HTML5 Drag and Drop API
- **Infraestrutura:** Docker, Docker Compose

## Como rodar

Requer Docker e Docker Compose instalados.

```bash
git clone https://github.com/MauroHLO/kanban-realtime.git
cd kanban-realtime
cp .env.example .env.docker
```

Edite `.env.docker` preenchendo `SECRET_KEY` com uma chave gerada (`python -c "import secrets; print(secrets.token_hex(32))"`).

```bash
docker compose up -d --build
```

A aplicação estará disponível em `http://localhost:8000/static/index.html`, e a documentação interativa da API em `http://localhost:8000/docs`.
