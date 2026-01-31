# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Creative AutoGPT is an AI-powered creative writing system specialized for long-form novels (10万字 to 500万字). It adapts the AutoGPT agent loop pattern for creative writing, with multi-LLM collaboration and a plugin-based element management system.

**Key characteristics:**
- AutoGPT-inspired agent loop (Think -> Plan -> Execute -> Evaluate -> Memory)
- Multi-LLM intelligent routing (Qwen + DeepSeek + Doubao)
- Plugin-based architecture for novel elements (characters, plot, world-building, foreshadowing)
- Real-time interactive writing with WebSocket progress updates
- Vector-based memory management for long-form consistency
- Chapter version management with rewrite capability

## Quick Start

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure API keys (required)
cp .env.example .env
# Edit .env with: ALIYUN_API_KEY, DEEPSEEK_API_KEY, ARK_API_KEY

# Initialize database
python scripts/init_db.py init

# Run server
python scripts/run_server.py
# API at http://localhost:8000, docs at http://localhost:8000/docs

# Run frontend (optional, for web UI)
cd frontend && npm install && npm run dev
# Frontend at http://localhost:5173
```

## Architecture

### Layered Architecture

```
Frontend (React/TypeScript) -> HTTP/WebSocket -> API Layer (FastAPI)
    |
    v
Application Layer (LoopEngine, TaskPlanner, Mode, Evaluator, EngineRegistry)
    |
    v
Domain Layer (Plugin System, VectorMemory, Storage)
    |
    v
Infrastructure Layer (MultiLLMClient, VectorStore, SessionStorage)
```

### Core Module Locations

| Module | Location | Purpose |
|--------|----------|---------|
| LoopEngine | `core/loop_engine.py` | Main execution loop (run/pause/resume/stop) |
| TaskPlanner | `core/task_planner.py` | DAG-based task dependency planning |
| Evaluator | `core/evaluator.py` | Multi-dimensional quality assessment |
| VectorMemory | `core/vector_memory.py` | ChromaDB-based semantic context retrieval |
| EngineRegistry | `core/engine_registry.py` | Global singleton for managing running engines |
| ChapterRewriter | `core/chapter_rewriter.py` | Chapter rewrite with version management |
| Plugin System | `plugins/` | Extensible element management |
| MultiLLMClient | `utils/llm_client.py` | Intelligent LLM routing with fallback |
| WebSocket Handler | `api/routes/websocket.py` | Real-time execution control |
| Session Storage | `storage/session.py` | SQLAlchemy-based persistence |

### Agent Loop Pattern

The `LoopEngine.run()` method executes:
1. **Plan** - `TaskPlanner.plan()` generates task DAG from goals
2. **Execute** - Tasks executed in dependency order via `_execute_task()`
3. **Evaluate** - `EvaluationEngine.evaluate()` scores quality
4. **Rewrite** - `_attempt_rewrite()` if score below threshold (max 3 attempts)
5. **Memory** - Results stored in `VectorMemoryManager` for context

Each task triggers plugin hooks: `on_before_task()` -> execute -> `on_after_task()`

### Task Dependency Flow

```
风格元素 -> 主题确认 -> 市场定位 -> 大纲 ->
  |   |    人物设计
  |    世界观规则
  |    事件
  |    场景物品冲突
  |    伏笔列表
  v
一致性检查 -> 章节循环生成 (章节大纲 -> 场景生成 -> 章节内容 -> 章节润色 -> 评估)
```

## Multi-LLM Routing Strategy

The `MultiLLMClient` uses `DEFAULT_TASK_TYPE_MAP` to route tasks to optimal LLMs:

| LLM | Provider | Task Types | Rationale |
|-----|----------|------------|-----------|
| **Qwen** | Aliyun | 大纲, 风格元素, 人物设计, 主题确认, 世界观 | Long context (200K+), global consistency |
| **DeepSeek** | DeepSeek | 事件, 场景物品, 评估, 一致性检查, 时间线, 伏笔 | Strong logic, cost-effective |
| **Doubao** | Ark | 章节内容, 修订, 润色, 对话检查 | Literary creativity, smooth prose |

To add new task types, extend `DEFAULT_TASK_TYPE_MAP` in `utils/llm_client.py`.

### LLM Client Configuration

```python
# Provider selection priority:
# 1. Explicit llm parameter in generate()
# 2. Task type mapping in DEFAULT_TASK_TYPE_MAP
# 3. Fallback to default provider (Qwen)

# Retry configuration
MAX_RETRIES = 5           # Max retry attempts for failed calls
RETRY_DELAY = 2.0         # Delay between retries (exponential backoff)
```

## Plugin System

All plugins extend `NovelElementPlugin` (base class in `plugins/base.py`):

**Implemented Plugins:**
- `CharacterPlugin` - Character profiles, relationships, arcs, voice profiles
- `WorldViewPlugin` - World settings, power systems, factions, locations
- `EventPlugin` - Plot events, conflicts, pacing
- `ForeshadowPlugin` - Plant/payoff tracking
- `TimelinePlugin` - Chronology and time consistency
- `ScenePlugin` - Scene descriptions and atmosphere
- `DialoguePlugin` - Dialogue consistency and character voice

**Plugin Lifecycle:**
```python
async def on_init(context)                      # Called when plugin initialized
async def on_before_task(task, context)         # Modify task before execution
async def on_after_task(task, result, context)  # Modify result
async def on_finalize(context)                  # Cleanup on session completion
def get_schema() -> Dict                       # JSON Schema for validation
def get_prompts() -> Dict[str, str]            # Prompt templates
def get_tasks() -> List[Dict]                  # Task definitions
async def validate(data, context) -> ValidationResult
async def enrich_context(task, context)         # Add relevant data before execution
```

## Execution Control

### Engine Registry

The `EngineRegistry` singleton (`core/engine_registry.py`) manages active `LoopEngine` instances:

```python
# In WebSocket handler when starting execution
from creative_autogpt.core.engine_registry import get_registry

registry = await get_registry()
await registry.register(session_id, engine)

# Control via API endpoints
await registry.pause(session_id)   # Calls engine.pause()
await registry.resume(session_id)  # Calls engine.resume()
await registry.stop(session_id)    # Calls engine.stop() + unregister
```

The registry runs a background cleanup task that removes completed engines after 5 minutes.

### WebSocket Events

Clients connect to `ws://host/ws/ws` and send JSON events:

| Event | Purpose |
|-------|---------|
| `subscribe` | Subscribe to session updates |
| `start` | Start execution (creates LoopEngine, registers it) |
| `pause` | Pause running engine |
| `resume` | Resume paused engine |
| `stop` | Stop engine |
| `feedback` | Submit user feedback for current task |
| `preview` | Get task result preview |

## Database & Storage

### SQLAlchemy Models

Located in `storage/session.py`:
- `SessionModel` - Session state, progress tracking
- `TaskResultModel` - Task results with chapter index, evaluation, metadata, current_version_id, version_count, rewrite_status
- `PluginDataModel` - Plugin data persistence
- `ChapterVersionModel` - Chapter version history (score, content, evaluation, created_by, rewrite_reason)

### Alembic Migrations

```bash
alembic upgrade head              # Apply migrations
alembic revision -m "description"  # Create new migration
alembic downgrade -1              # Rollback one migration
```

### Vector Store

Uses ChromaDB with sentence-transformers embeddings. Memory types: CHARACTER, PLOT, WORLDVIEW, FORESHADOW, SCENE, CHAPTER, OUTLINE, GENERAL.

**Session Isolation**: Each session gets its own collection to prevent cross-contamination.

**Memory Management**:
- Auto-add: Task results stored via `VectorMemoryManager.add_memory()`
- Manual add: `vector_store.add(content, memory_type, metadata)`
- Search: `vector_store.search(query, top_k, filters={})`

## Frontend (React/TypeScript)

### Development Commands

```bash
cd frontend
npm install              # Install dependencies
npm run dev             # Start dev server (http://localhost:5173)
npm run build           # Build for production
npm run type-check      # TypeScript type checking
npm run lint            # ESLint
```

### Frontend Architecture

**Key Directories:**
- `src/pages/` - Page components (Dashboard, ChapterList, ChapterDetail, Characters, etc.)
- `src/components/` - Reusable UI components
- `src/hooks/` - React hooks (useWebSocket, useSession, useChapter, useCharacter, etc.)
- `src/api/` - API client with axios
- `src/types/` - TypeScript type definitions

**Custom Hooks:**
- `useWebSocket(sessionId)` - WebSocket connection for real-time updates
- `useSession()` - Session CRUD operations
- `useChapter(sessionId)` - Chapter management and rewrite
- `useCharacter(sessionId)` - Character management
- `useForeshadow(sessionId)` - Foreshadowing tracking

**Vite Configuration:**
- Dev server runs on port 5173
- Proxy `/api` requests to backend (http://localhost:8000)
- WebSocket proxy to `ws://localhost:8000`

### E2E Testing

```bash
cd frontend
npm run test:e2e           # Run all E2E tests
npm run test:e2e:ui        # Run with UI
npm run test:e2e:debug     # Run in debug mode
npm run test:e2e:smoke     # Run smoke tests only
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/init_db.py init\|reset\|clear` | Database initialization/reset |
| `scripts/run_server.py` | Start development server |
| `scripts/test_llm.py --test llm` | Test LLM connectivity and routing |
| `scripts/test_llm.py --test embeddings` | Test vector store embeddings |
| `scripts/test_system.py` | Run full system integration test |
| `scripts/quick_test.py` | Quick sanity test |

## Code Quality Commands

### Backend (Python)

```bash
# Format code (line length: 120)
black src/

# Lint
pylint src/
ruff check src/

# Type check
mypy src/

# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_loop_engine.py::test_pause_resume -v

# Run with coverage
pytest tests/ --cov=src/creative_autogpt --cov-report=html

# Run by marker
pytest tests/ -m unit          # Unit tests only
pytest tests/ -m integration   # Integration tests only
pytest tests/ -m "not slow"    # Skip slow tests
```

### Frontend (TypeScript/React)

```bash
cd frontend

# Type check
npm run type-check

# Lint
npm run lint
```

## Important Notes

- **All I/O is async** - Use `async/await` consistently throughout
- **New task types** must be added to `DEFAULT_TASK_TYPE_MAP` for LLM routing
- **Plugin methods** must implement all abstract methods from `NovelElementPlugin`
- **Quality threshold** defaults to 0.7, configurable via `EvaluationEngine.__init__()`
- **Session state** is persisted for checkpoint/resume capability
- **EngineRegistry** is a singleton - use `get_registry()` to access it
- **Line length** is 120 characters (configured in black and ruff)
- **Python version** requires 3.10 or higher
- **Frontend dev server** proxies API requests to backend and handles WebSocket upgrades

## Task State Machine

Tasks progress through these states managed by `LoopEngine`:

```
pending -> ready -> running -> completed/failed
         |        |
      skipped  paused
```

- **pending**: Initial state, dependencies not satisfied
- **ready**: Dependencies satisfied, waiting to execute
- **running**: Currently executing
- **completed**: Finished successfully
- **failed**: Error occurred, may be retried
- **skipped**: Previously completed, skipped on resume
- **paused**: Execution paused by user

## Writing Context & Plugin Communication

The `WritingContext` class serves as the shared data bus between plugins:

```python
# Context structure
context.novel_data      # Shared novel metadata (genre, theme, style)
context.plugin_data     # Plugin-specific data storage
context.task_results    # Results from completed tasks
context.session_id      # Current session identifier
```

Plugins communicate via `plugin_data`:
- Each plugin has its own namespace: `context.plugin_data['character']`
- Plugins can read other plugins' data for cross-referencing
- Use `enrich_context()` to add relevant data before task execution

## Chapter Version Management

The system includes comprehensive chapter version management for progressive writing.

**Automatic Version Creation:**
- Initial version (v1) saved when chapter first generated
- Each rewrite attempt creates a new version
- Versions marked with: `created_by` ("auto" | "manual" | "rewrite")

**Version Management Methods:**
```python
# Create a new version
await storage.create_chapter_version(
    session_id, task_id, chapter_index, content,
    version_number, is_current, evaluation,
    created_by, rewrite_reason, token_stats
)

# Get all versions for a chapter
versions = await storage.get_chapter_versions(session_id, chapter_index)

# Restore to a specific version
await storage.restore_chapter_version(session_id, task_id, version_id)

# Get current version
current = await storage.get_current_chapter_version(session_id, chapter_index)
```

### Rewrite API Endpoints

```bash
# Rewrite a chapter
POST /chapters/{session_id}/rewrite?chapter_index=1&reason=improve_quality

# Get chapter versions
GET /chapters/{session_id}/chapters/{chapter_index}/versions

# Restore a version
POST /chapters/{session_id}/chapters/{chapter_index}/versions/{version_id}/restore

# Get all chapters with version info
GET /chapters/{session_id}/versions
```

## Common Development Patterns

### Adding a New Plugin

1. Create class extending `NovelElementPlugin` in `plugins/`
2. Implement all abstract methods
3. Register in `PluginManager.__init__()` or use dynamic loading
4. Add task definitions via `get_tasks()`
5. Define JSON schema for validation via `get_schema()`

### Adding a New Task Type

1. Add task type to `TaskType` enum (if applicable)
2. Map to LLM provider in `DEFAULT_TASK_TYPE_MAP` (`utils/llm_client.py`)
3. Create prompt template in `prompts/` or plugin's `get_prompts()`
4. Add task definition with dependencies in plugin's `get_tasks()`

### Debugging Execution Flow

```python
# Enable detailed logging
from creative_autogpt.utils.logger import setup_logger
setup_logger("DEBUG")

# Check engine state via registry
registry = await get_registry()
engine = registry.get_engine(session_id)
print(f"State: {engine.state}, Progress: {engine.progress}")
```

## Environment Configuration

Required environment variables (set in `.env`):

```bash
# LLM API Keys
ALIYUN_API_KEY=sk-***          # Qwen (Aliyun)
DEEPSEEK_API_KEY=sk-***        # DeepSeek
ARK_API_KEY=***                # Doubao (Ark)

# Optional Configuration
DATABASE_URL=sqlite+aiosqlite:///./data/creative_autogpt.db
CHROMA_PERSIST_DIR=./data/chroma
LOG_LEVEL=INFO
```

## Error Handling & Resilience

The system implements multiple layers of error handling:

1. **LLM Client Level**: Automatic retry with exponential backoff (max 5 attempts)
2. **Task Level**: Failed tasks marked for retry, stored in database
3. **Engine Level**: State persisted on pause/error, supports resume
4. **Plugin Level**: Validation via `validate()` method, returns `ValidationResult`

When debugging errors:
- Check logs for retry attempts and provider fallbacks
- Use `pytest tests/ -m integration` to test LLM connectivity
- Verify API keys are correctly set in `.env`
