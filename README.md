# MyTaskly MCP Server

**Model Context Protocol (MCP) server** for [MyTaskly](https://github.com/Gabry848/MyTaskly-app) with **OAuth 2.1 JWT authentication** and seamless integration with the [FastAPI backend](https://github.com/Gabry848/MyTaskly-server).

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-2025-00D8FF?style=flat-square)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Integration-00D8FF?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 📋 Key Features

### 🔐 Enterprise-Grade Authentication
- **OAuth 2.1 JWT** - Token-based authentication following MCP 2025 standards (RFC 8707)
- **SSE Transport** - Server-Sent Events for HTTP-based deployment (Railway-ready)
- **Context-Based Auth** - Token extracted automatically from SSE request headers

### 🚀 High-Performance Integration
- **HTTP API Gateway** - Communicates with FastAPI backend, no direct database access
- **Stateless Architecture** - No session management, fully scalable
- **Connection Pooling** - Optimized async HTTP client (httpx)

### 📱 Mobile-First Design
- **React Native Optimized** - `show_*` tools return data formatted for native mobile components
- **Voice-Friendly Responses** - Includes `voice_summary` for TTS in chat applications
- **Dual-Mode Tools** - `get_*` for internal data processing, `show_*` to trigger UI updates

---

## 🛠️ Available MCP Tools (18 Active)

The MCP server provides **18 active tools** organized into 3 categories. All tools require JWT authentication via SSE Authorization header.

> Tools follow a dual pattern: `get_*` returns raw data for model reasoning, `show_*` triggers UI rendering in the mobile app.

### 📋 Task Tools (8)

| Tool | Description |
|------|-------------|
| `get_tasks` | Get tasks with filters — for internal model use (raw data) |
| `add_task` | Create a new task with smart category lookup |
| `update_task` | Update one or more fields of an existing task |
| `complete_task` | Quick shortcut to mark a task as completed |
| `get_task_stats` | Get aggregate statistics by status, priority, and category |
| `get_overdue_tasks` | Get all overdue pending tasks |
| `get_upcoming_tasks` | Get tasks due in the next N days |
| `show_tasks_to_user` | Display task list in the mobile app UI |

**Example Response — `get_tasks`:**
```json
{
  "tasks": [
    {
      "task_id": 123,
      "title": "Pizza",
      "description": "Ordinare pizza margherita",
      "end_time": "2025-12-15T18:00:00",
      "start_time": null,
      "priority": "Alta",
      "status": "In sospeso",
      "category_id": 5,
      "duration_minutes": 30
    }
  ],
  "total": 10
}
```

**Example Response — `add_task` (success):**
```json
{
  "success": true,
  "task_id": 124,
  "category_used": "Cibo"
}
```

**Example Response — `add_task` (category not found):**
```json
{
  "success": false,
  "message": "Categoria 'Cibo' non trovata.",
  "category_suggestions": ["Alimentari", "Cucina"],
  "action_required": "ask_user_to_create_category"
}
```

**Example Response — `get_task_stats`:**
```json
{
  "success": true,
  "by_status": {
    "In sospeso": 5,
    "Completato": 3,
    "Annullato": 1
  },
  "by_priority": {
    "Alta": 2,
    "Media": 4,
    "Bassa": 3
  },
  "by_category": { "5": 4, "3": 2 },
  "total": 9
}
```

**Example Response — `get_overdue_tasks`:**
```json
{
  "tasks": [
    {
      "task_id": 10,
      "title": "Consegnare report",
      "priority": "Alta",
      "status": "In sospeso",
      "end_time": "2025-12-01T09:00:00",
      "days_overdue": 14
    }
  ],
  "total": 1
}
```

**Example Response — `show_tasks_to_user`:**
```json
{
  "type": "task_list",
  "success": true,
  "filters_applied": {
    "priority": "Alta",
    "status": "In sospeso"
  }
}
```

---

### 📂 Category Tools (5)

| Tool | Description |
|------|-------------|
| `get_my_categories` | Get all user categories — for internal model use (raw data) |
| `create_category` | Create a new category |
| `update_category` | Update name or description of an existing category |
| `show_categories_to_user` | Display category list in the mobile app UI |
| `show_category_details` | Display details of a single category in the mobile app UI |

**Example Response — `get_my_categories`:**
```json
{
  "categories": [
    {
      "category_id": 1,
      "name": "Lavoro",
      "description": "Task di lavoro"
    },
    {
      "category_id": 2,
      "name": "Casa",
      "description": "Faccende domestiche"
    }
  ],
  "total": 2
}
```

**Example Response — `create_category`:**
```json
{
  "success": true,
  "type": "category_created",
  "category_id": 3
}
```

**Example Response — `show_categories_to_user`:**
```json
{
  "type": "category_list",
  "success": true
}
```

---

### 📝 Note Tools (5)

| Tool | Description |
|------|-------------|
| `get_notes` | Get all user notes — for internal model use (raw data) |
| `create_note` | Create a new post-it style note |
| `update_note` | Update text, position, or color of a note |
| `delete_note` | Delete a note (irreversible) |
| `show_notes_to_user` | Display note board in the mobile app UI |

**Available note colors:** `#FFEB3B` (yellow), `#FF9800` (orange), `#4CAF50` (green), `#2196F3` (blue), `#E91E63` (pink), `#9C27B0` (purple)

**Example Response — `get_notes`:**
```json
{
  "notes": [
    {
      "note_id": 456,
      "title": "Comprare il latte",
      "color": "#FFEB3B",
      "position_x": "100",
      "position_y": "250",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 3
}
```

**Example Response — `create_note`:**
```json
{
  "success": true,
  "type": "note_created",
  "note_id": 456
}
```

**Example Response — `show_notes_to_user`:**
```json
{
  "type": "note_list",
  "success": true
}
```

---

### ⚕️ Inactive Tools (2 — commented out)

| Tool | Description |
|------|-------------|
| `add_multiple_tasks` | Bulk create multiple tasks at once |
| `health_check` | Check server health and connectivity (no auth required) |

These tools are defined in `src/tools/` but not registered. Uncomment in `src/core/server.py` to enable.

---

## 🚀 Getting Started

### Usage Options

You have **two ways** to use the MyTaskly MCP Server:

#### Option 1: Use Official Public Server (Recommended)

Use the **official MyTaskly MCP server** (coming soon) - no setup required!

```bash
# Configure your MCP client to connect to:
# https://mcp.mytasklyapp.com (URL will be published soon)
```

**Benefits:**
- ✅ No installation or configuration needed
- ✅ Always up-to-date with latest features
- ✅ Managed and monitored by MyTaskly team
- ✅ Works out-of-the-box with MyTaskly mobile app

---

#### Option 2: Self-Host (Advanced Users)

Run your own local MCP server instance.

**Prerequisites:**
- **Python 3.11+** (virtual environment recommended)
- **MyTaskly FastAPI Server** running locally (see [MyTaskly-server](https://github.com/Gabry848/MyTaskly-server))
- **JWT Secret Key** matching your FastAPI server configuration

**Quick Start (5 minutes):**

```bash
git clone https://github.com/Gabry848/MyTaskly-mcp.git
cd MyTaskly-mcp
python -m venv venv && pip install -r requirements.txt
cp .env.example .env && python main.py
```

---

### Self-Hosting Setup Guide

#### 1. Clone & Install

```bash
# Clone the repository
git clone https://github.com/Gabry848/MyTaskly-mcp.git
cd MyTaskly-mcp

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment Variables

Create `.env` file in the root directory:

```env
# ============ FASTAPI BACKEND ============
FASTAPI_BASE_URL=http://localhost:8080
FASTAPI_API_KEY=your_api_key_here

# ============ JWT CONFIGURATION ============
# CRITICAL: Must match FastAPI server configuration!
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
MCP_AUDIENCE=mcp://mytaskly-mcp-server

# ============ SERVER CONFIGURATION ============
MCP_SERVER_NAME=MyTaskly MCP Server
MCP_SERVER_VERSION=0.1.1
LOG_LEVEL=INFO

# ============ DEPLOYMENT ============
HOST=0.0.0.0
PORT=8000
```

⚠️ **CRITICAL:** `JWT_SECRET_KEY` MUST match your FastAPI server's `SECRET_KEY` environment variable!

#### 3. Start the MCP Server

```bash
python main.py
```

The server starts in **SSE (Server-Sent Events) mode** on `http://0.0.0.0:8000`. Configure your MCP client to connect to this URL.

---

## 🔐 Authentication & Security

### OAuth 2.1 Flow

The MCP server uses JWT tokens following OAuth 2.1 and RFC 8707 standards. The token is extracted automatically from the SSE `Authorization` header — tools receive a `ctx: Context` parameter, not an explicit `authorization` string.

```
┌─────────────────┐
│  Mobile Client  │
│  (React Native) │
└────────┬────────┘
         │ 1. Login request
         ▼
┌─────────────────┐
│  FastAPI Server │  2. Validates credentials
│  (Auth Server)  │  3. Generates JWT with MCP audience claim
└────────┬────────┘
         │ 4. Returns JWT token
         ▼
┌─────────────────┐
│  Mobile Client  │  5. Stores token securely
└────────┬────────┘
         │ 6. Calls MCP tools via SSE with Authorization header
         ▼
┌─────────────────┐
│   MCP Server    │  7. Extracts token from SSE context
│ (This project)  │  8. Validates JWT signature + audience
│                 │  9. Extracts user_id from "sub" claim
└────────┬────────┘
         │ 10. Makes HTTP request to FastAPI with user_id
         ▼
┌─────────────────┐
│  FastAPI Server │  11. Returns user-specific data
│ (Resource API)  │
└────────┬────────┘
         │ 12. Formats data for mobile UI
         ▼
┌─────────────────┐
│   MCP Server    │  13. Returns formatted response
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Mobile Client  │  14. Renders UI / plays TTS
└─────────────────┘
```

### JWT Token Structure

The JWT must include these claims (following RFC 7519 and RFC 8707):

```json
{
  "sub": "123",                              // User ID (required)
  "aud": "mcp://mytaskly-mcp-server",       // Audience (required, RFC 8707)
  "iss": "https://api.mytasklyapp.com",     // Issuer (optional)
  "exp": 1735689600,                         // Expiration timestamp (required)
  "iat": 1735686000,                         // Issued at timestamp (required)
  "scope": "tasks:read tasks:write notes:write" // Scopes (optional)
}
```

**Security Features:**
| Feature | Implementation |
|---------|----------------|
| **Signature Validation** | HS256 with shared secret |
| **Audience Claim** | Prevents token reuse across services (RFC 8707) |
| **Expiration Check** | Automatic token invalidation |
| **User Isolation** | Each request scoped to authenticated user |

### Getting a JWT Token

**Option 1: From FastAPI (Production)**

Add this endpoint to your FastAPI server:

```python
@router.post("/auth/mcp-token")
async def get_mcp_token(current_user: User = Depends(get_current_user)):
    """Generate JWT token for MCP server access."""
    payload = {
        "sub": str(current_user.user_id),
        "aud": "mcp://mytaskly-mcp-server",
        "iss": "https://api.mytasklyapp.com",
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
        "scope": "tasks:read tasks:write categories:read notes:read notes:write"
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    return {"mcp_token": token, "expires_in": 1800}
```

**Option 2: Generate Test Token (Development)**

```python
from src.auth import create_test_token

# Generate test token for user_id=1
token = create_test_token(user_id=1, expires_minutes=30)
print(f"Test Token: {token}")
```

---

## 🧪 Testing & Development

### Generate Test Token

```bash
python -c "from src.auth import create_test_token; print(create_test_token(1))"
```

### Manual Testing with cURL

```bash
# Export token to environment variable
export MCP_TOKEN="your_token_here"

# Test get_tasks (SSE endpoint)
curl -X POST http://localhost:8000/mcp/get_tasks \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json"

# Test add_task
curl -X POST http://localhost:8000/mcp/add_task \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Comprare latte", "category_name": "Casa", "priority": "Bassa"}'
```

### Automated Test Suite

```bash
# Run all unit tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_auth.py -v

# Run with coverage report
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 🔒 Security Best Practices

1. **Always use HTTPS** in production
2. **Keep JWT_SECRET_KEY secure** - never commit to git
3. **Use short-lived tokens** (15-30 minutes)
4. **Implement token refresh** in your client
5. **Validate audience claim** (RFC 8707) - prevents token reuse
6. **Log authentication failures** for monitoring

---

## 🏗️ Architecture & Project Structure

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MyTaskly Ecosystem                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────────────────┐                                       │
│   │  Mobile Client  │  1. User authentication               │
│   │ (React Native)  │  2. Receives JWT token                │
│   └────────┬────────┘  3. Calls MCP tools via SSE          │
│            │                                                  │
│            ▼                                                  │
│   ┌─────────────────┐                                       │
│   │   MCP Server    │  4. Validates JWT (OAuth 2.1)        │
│   │ (This project)  │  5. Extracts user_id from token       │
│   └────────┬────────┘  6. Formats data for mobile UI        │
│            │                                                  │
│            ▼                                                  │
│   ┌─────────────────┐                                       │
│   │  FastAPI Server │  7. Handles business logic            │
│   │ (MyTaskly-API)  │  8. Manages database operations       │
│   └────────┬────────┘  9. Returns raw data                  │
│            │                                                  │
│            ▼                                                  │
│   ┌─────────────────┐                                       │
│   │   PostgreSQL    │  10. Persistent storage               │
│   │    Database     │  11. Triggers & notifications         │
│   └─────────────────┘                                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure

```
MyTaskly-mcp/
├── src/
│   ├── core/                      # Core MCP server
│   │   ├── __init__.py
│   │   └── server.py             # FastMCP instance, log_tool decorator & tool registration
│   │
│   ├── client/                    # HTTP client layer
│   │   ├── __init__.py
│   │   ├── base.py               # BaseClient with async HTTP methods + JWT token generation
│   │   ├── categories.py         # CategoryClient
│   │   ├── tasks.py              # TaskClient (with status/priority normalization)
│   │   ├── notes.py              # NoteClient
│   │   └── health.py             # HealthClient
│   │
│   ├── tools/                     # MCP tool definitions
│   │   ├── __init__.py
│   │   ├── categories.py         # 5 category tools
│   │   ├── tasks.py              # 8 task tools
│   │   ├── notes.py              # 5 note tools
│   │   ├── meta.py               # add_multiple_tasks (inactive)
│   │   └── health.py             # health_check (inactive)
│   │
│   ├── formatters/                # Response formatters for React Native
│   │   ├── __init__.py
│   │   └── tasks.py              # format_tasks_for_ui, format_categories_for_ui, format_notes_for_ui
│   │
│   ├── auth.py                    # JWT authentication (extract, verify, create_test_token)
│   ├── config.py                  # Pydantic settings (loaded from .env)
│   └── http_server.py            # HTTP server wrapper
│
├── tests/                         # Test suite
├── main.py                        # Entry point — runs FastMCP in SSE mode
├── pyproject.toml                 # Project configuration
├── requirements.txt               # Python dependencies
├── ARCHITECTURE.md                # Detailed architecture documentation
└── README.md                      # This file
```

### Layer Architecture

| Layer | Files | Responsibility |
|-------|-------|----------------|
| **Core Layer** | `src/core/` | FastMCP instance, `log_tool` decorator, tool registration |
| **Tools Layer** | `src/tools/` | MCP tool definitions — auth, business logic, response shaping |
| **Client Layer** | `src/client/` | Async HTTP communication with FastAPI backend |
| **Formatters Layer** | `src/formatters/` | Transform API responses into React Native-ready structures |

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **MCP Server** | FastMCP + SSE | Request handling, tool orchestration, Railway deployment |
| **JWT Authentication** | PyJWT (HS256) | Token validation via SSE context headers |
| **HTTP Client** | httpx (async) | FastAPI backend communication |
| **Data Formatters** | Custom formatters | Mobile-optimized response structure with voice summaries |

📚 **For detailed architecture information**, see [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 🛠️ Development Guide

### Adding New MCP Tools

Follow the layered architecture pattern:

#### 1. Add HTTP Client Method

```python
# src/client/tasks.py
async def new_operation(self, user_id: int, params...) -> Dict[str, Any]:
    """Call new FastAPI endpoint."""
    token = await self._get_user_token(user_id)
    return await self._post("/new-endpoint", token, json={...})
```

#### 2. Add MCP Tool

```python
# src/tools/tasks.py
from fastmcp import Context
from src.auth import authenticate_from_context

async def new_tool(ctx: Context, params...) -> Dict[str, Any]:
    """Tool documentation here."""
    user_id = await authenticate_from_context(ctx)
    result = await task_client.new_operation(user_id, params)
    return format_response(result)
```

#### 3. Register Tool

```python
# src/core/server.py
from src.tools.tasks import new_tool
mcp.tool()(log_tool(new_tool))
```

**For more details**, see [ARCHITECTURE.md](ARCHITECTURE.md#adding-new-tools)

### Code Quality

```bash
# Format code with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html
```

### Common Development Tasks

| Task | Command |
|------|---------|
| **Run server** | `python main.py` |
| **Generate test token** | `python -c "from src.auth import create_test_token; print(create_test_token(1))"` |
| **Run tests** | `pytest tests/ -v` |
| **Check coverage** | `pytest tests/ --cov=src` |
| **Format code** | `black src/ tests/` |
| **Install dependencies** | `pip install -r requirements.txt` |

---

## 📚 Resources & Related Projects

### MyTaskly Ecosystem

- **[MyTaskly Mobile App](https://github.com/Gabry848/MyTaskly-app)** - React Native frontend
- **[MyTaskly Server](https://github.com/Gabry848/MyTaskly-server)** - FastAPI backend
- **MyTaskly MCP** (this project) - Model Context Protocol server

### Documentation

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [RFC 8707 - Resource Indicators for OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc8707)
- [RFC 7519 - JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)

---

## 🤝 Contributing

We welcome contributions! This project is part of the MyTaskly ecosystem.

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make your changes** with clear commit messages
4. **Add tests** for new functionality
5. **Ensure tests pass**: `pytest tests/ -v`
6. **Format code**: `black src/ tests/`
7. **Submit a pull request**

### Development Workflow

```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/MyTaskly-mcp.git
cd MyTaskly-mcp

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Make changes and test
pytest tests/ -v

# 4. Commit with descriptive message
git commit -m "feat: add new MCP tool for task statistics"

# 5. Push and create PR
git push origin feature/my-feature
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

The MIT License allows you to:
- ✅ Use commercially
- ✅ Modify
- ✅ Distribute
- ✅ Private use

---

## 📞 Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/Gabry848/MyTaskly-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Gabry848/MyTaskly-mcp/discussions)
- **Email**: support@mytasklyapp.com

---

<div align="center">

Made with ❤️ by [Gabry848](https://github.com/Gabry848) as part of the **MyTaskly** project

**Starring is appreciated!** ⭐

[⬆ Back to Top](#mytaskly-mcp-server)

</div>
