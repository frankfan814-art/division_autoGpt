# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Creative AutoGPT is an AI-powered creative writing system specialized for long-form novels (10万字 to 500万字). It adapts the AutoGPT agent loop pattern for creative writing, with multi-LLM collaboration and a plugin-based element management system.

**Key characteristics:**
- AutoGPT-inspired agent loop (Think → Plan → Execute → Evaluate → Memory)
- Multi-LLM intelligent routing (Qwen + DeepSeek + Doubao)
- Plugin-based architecture for novel elements (characters, plot, world-building, foreshadowing)
- Real-time interactive writing with WebSocket progress updates
- Vector-based memory management for long-form consistency

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
```

## Architecture

### Layered Architecture

```
Frontend (React/TypeScript) → HTTP/WebSocket → API Layer (FastAPI)
    ↓
Application Layer (LoopEngine, TaskPlanner, Mode, Evaluator, EngineRegistry)
    ↓
Domain Layer (Plugin System, VectorMemory, Storage)
    ↓
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
| Plugin System | `plugins/` | Extensible element management |
| MultiLLMClient | `utils/llm_client.py` | Intelligent LLM routing with fallback |
| WebSocket Handler | `api/routes/websocket.py` | Real-time execution control |
| Session Storage | `storage/session.py` | SQLAlchemy-based persistence |

### Agent Loop Pattern

The `LoopEngine.run()` method executes:
1. **Plan** - `TaskPlanner.plan()` generates task DAG from goals
2. **Execute** - Tasks executed in dependency order via `_execute_task()`
3. **Evaluate** - `EvaluationEngine.evaluate()` scores quality
4. **Rewrite** - `_attempt_rewrite()` if score below threshold
5. **Memory** - Results stored in `VectorMemoryManager` for context

Each task triggers plugin hooks: `on_before_task()` → execute → `on_after_task()`

### Task Dependency Flow

```
风格元素 → 主题确认 → 市场定位 → 大纲 →
├── 人物设计
├── 世界观规则
├── 事件
├── 场景物品冲突
└── 伏笔列表
→ 一致性检查 → 章节循环生成 (章节大纲 → 场景生成 → 章节内容 → 章节润色 → 评估)
```

## Multi-LLM Routing Strategy

The `MultiLLMClient` uses `DEFAULT_TASK_TYPE_MAP` to route tasks to optimal LLMs:

| LLM | Provider | Task Types | Rationale |
|-----|----------|------------|-----------|
| **Qwen** | Aliyun | 大纲, 风格元素, 人物设计, 主题确认, 世界观 | Long context (200K+), global consistency |
| **DeepSeek** | DeepSeek | 事件, 场景物品, 评估, 一致性检查, 时间线, 伏笔 | Strong logic, cost-effective |
| **Doubao** | Ark | 章节内容, 修订, 润色, 对话检查 | Literary creativity, smooth prose |

To add new task types, extend `DEFAULT_TASK_TYPE_MAP` in `utils/llm_client.py`.

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
async def on_init(context)           # Called when plugin initialized
async def on_before_task(task, context) -> task  # Modify task before execution
async def on_after_task(task, result, context) -> result  # Modify result
async def on_finalize(context)        # Cleanup on session completion
def get_schema() -> Dict             # JSON Schema for validation
def get_prompts() -> Dict[str, str]  # Prompt templates
def get_tasks() -> List[Dict]        # Task definitions
async def validate(data, context) -> ValidationResult
async def enrich_context(task, context) -> context
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
- `TaskResultModel` - Task results with chapter index, evaluation, metadata

### Alembic Migrations

```bash
alembic upgrade head    # Apply migrations
alembic revision -m "description"  # Create new migration
```

### Vector Store

Uses ChromaDB with sentence-transformers embeddings. Memory types: CHARACTER, PLOT, WORLDVIEW, FORESHADOW, SCENE, CHAPTER, OUTLINE, GENERAL.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/init_db.py` | Database init/reset/clear: `python scripts/init_db.py init\|reset\|clear` |
| `scripts/run_server.py` | Start development server |
| `scripts/test_llm.py` | Test LLM connectivity |
| `scripts/test_system.py` | Run system tests |

## Important Notes

- **All I/O is async** - Use `async/await` consistently throughout
- **New task types** must be added to `DEFAULT_TASK_TYPE_MAP` for LLM routing
- **Plugin methods** must implement all abstract methods from `NovelElementPlugin`
- **Quality threshold** defaults to 0.7, configurable via `EvaluationEngine.__init__()`
- **Session state** is persisted for checkpoint/resume capability
- **EngineRegistry** is a singleton - use `get_registry()` to access it
- **WebSocket handler** stores running engines in local dict; for distributed deployment, use EngineRegistry

## Code Quality Commands

```bash
black src/           # Format
pylint src/          # Lint
mypy src/            # Type check
pytest tests/ -v     # Run tests
```
