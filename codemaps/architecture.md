# Creative AutoGPT - Architecture Overview

**Last Updated:** 2025-01-25
**Framework:** FastAPI + React/TypeScript
**Type:** AI-Powered Creative Writing System

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│  React/TypeScript (Vite) + Zustand + Tailwind CSS              │
│  - Workspace Layout                                             │
│  - Real-time WebSocket Updates                                  │
│  - Task Monitoring & Preview                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                          API Layer                              │
│  FastAPI Routes (sessions, websocket, prompts)                  │
│  - Session Management                                           │
│  - Real-time Execution Control                                  │
│  - Prompt Template Management                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    Application Layer                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LoopEngine - AutoGPT Agent Loop                        │   │
│  │  Plan → Execute → Evaluate → Rewrite → Memory           │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────┬──────────────┬──────────────┬────────────┐   │
│  │TaskPlanner  │  Evaluator   │VectorMemory  │EngineReg   │   │
│  │(DAG Tasks)  │(Quality)     │(ChromaDB)    │(Singleton) │   │
│  └─────────────┴──────────────┴──────────────┴────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      Plugin System                              │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐  │
│  │Character │WorldView │  Event   │Timeline │  Foreshadow  │  │
│  │Plugin    │Plugin    │Plugin    │Plugin   │Plugin        │  │
│  ├──────────┼──────────┼──────────┼──────────┼──────────────┤  │
│  │  Scene   │Dialogue  │          │          │              │  │
│  │Plugin    │Plugin    │          │          │              │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────────┘  │
│              NovelElementPlugin (Base Class)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                   Infrastructure Layer                           │
│  ┌──────────────┬──────────────┬────────────────────────────┐  │
│  │MultiLLMClient│ VectorStore  │    SessionStorage         │  │
│  │Intelligent   │(ChromaDB +   │(SQLAlchemy + PostgreSQL) │  │
│  │Routing       │Embeddings)   │                          │  │
│  └──────────────┴──────────────┴────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │        Prompt Manager + Feedback Transformer            │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

External Services:
- Aliyun Qwen (Long Context, Global Planning)
- DeepSeek (Logic, Cost-effective)
- Ark/Doubao (Creative Writing)
- ChromaDB (Vector Storage)
```

## Core Components

### 1. LoopEngine (core/loop_engine.py)
**Purpose:** AutoGPT-inspired agent execution loop

**Responsibilities:**
- Plan: Generate task DAG from goals via TaskPlanner
- Execute: Run tasks in dependency order
- Evaluate: Assess quality via EvaluationEngine
- Rewrite: Retry if below quality threshold
- Memory: Store results in VectorMemoryManager

**Key Methods:**
- `run(goal, chapter_count)` - Main execution loop
- `_execute_task(task, goal)` - Execute single task with plugin hooks
- `pause()` / `resume()` / `stop()` - Execution control
- `set_callbacks()` - Event monitoring hooks

**State Management:**
- ExecutionStatus enum (IDLE, PLANNING, RUNNING, PAUSED, COMPLETED, FAILED)
- Approval mode for user review
- High-score examples storage for self-improvement

### 2. TaskPlanner (core/task_planner.py)
**Purpose:** DAG-based task dependency planning

**Task Flow:**
```
Phase 0: 创意脑暴 → 故事核心 (is_foundation=True)
Phase 1: 大纲 (is_foundation=True)
Phase 2: 世界观规则 (is_foundation=True)
Phase 3: 人物设计 (is_foundation=True)
Phase 4: 主题确认 → 风格元素 → 市场定位
Phase 5: 事件 → 场景物品冲突 → 伏笔列表 (is_foundation=True)
Phase 6: 一致性检查
Phase 7: 章节循环 (章节大纲 → 章节内容 → [润色])
```

**Features:**
- Short novel optimization (<=3 chapters): Simplified 5-task flow
- Foundation task tracking: Stored in vector DB for chapter retrieval
- Dependency resolution with topological ordering

### 3. EvaluationEngine (core/evaluator.py)
**Purpose:** Multi-dimensional quality assessment

**Criteria:**
- Coherence (20%), Creativity (20%), Quality (20%)
- Consistency (20%), Goal Alignment (20%)

**Content-Specific Overrides:**
- 章节内容: Adds Character Voice (10%), Plot Progression (10%)
- 对话检查: Dialogue Quality (40%), Character Voice (30%)
- 大纲: Plot Progression (25%)

**Evaluation Methods:**
- LLM-based: Uses DeepSeek for logical evaluation
- Rule-based: Fallback with heuristics (length, vocabulary, format)

### 4. VectorMemoryManager (core/vector_memory.py)
**Purpose:** High-level memory for long-form consistency

**Memory Types:**
- CHARACTER, PLOT, WORLDVIEW, FORESHADOW, SCENE, CHAPTER, OUTLINE, GENERAL

**Retrieval Strategies:**
- Recent context: Last N task results
- Semantic search: Vector similarity via ChromaDB
- Chapter-scoped: Filter by chapter_index
- Task-specific: Previous attempts for retry

### 5. EngineRegistry (core/engine_registry.py)
**Purpose:** Global singleton for managing running engines

**Features:**
- Register/unregister LoopEngine instances by session_id
- Pause/resume/stop control across API requests
- Background cleanup (removes completed engines after 5 min)
- Thread-safe with asyncio.Lock

## Multi-LLM Routing Strategy

**Task Type Map (utils/llm_client.py):**

| LLM | Provider | Task Types | Rationale |
|-----|----------|------------|-----------|
| Qwen | Aliyun | 大纲, 风格元素, 人物设计, 主题确认, 世界观 | 200K+ context, global consistency |
| DeepSeek | DeepSeek | 事件, 场景物品, 评估, 一致性检查, 时间线, 伏笔 | Strong logic, cost-effective |
| Doubao | Ark | 章节内容, 修订, 润色, 对话检查 | Literary creativity, smooth prose |

**Features:**
- Exponential backoff retry (max 5 attempts)
- Rate limit handling
- Automatic fallback between providers

## Plugin System Architecture

**Base Class:** NovelElementPlugin (plugins/base.py)

**Lifecycle Hooks:**
```python
on_init(context)              # Plugin initialization
on_before_task(task, context) # Modify task before execution
on_after_task(task, result, context) # Modify result after execution
on_finalize(context)          # Cleanup on session completion
```

**Required Methods:**
- `get_schema()` - JSON Schema for validation
- `get_prompts()` - Prompt templates
- `get_tasks()` - Task definitions
- `validate(data, context)` - ValidationResult

**Plugin Manager (plugins/manager.py):**
- Priority-based execution order
- Dependency resolution
- Enable/disable plugins at runtime
- Hook execution with error isolation

**Implemented Plugins:**
1. **CharacterPlugin** - Character profiles, relationships, arcs, voice profiles
2. **WorldViewPlugin** - World settings, power systems, factions, locations
3. **EventPlugin** - Plot events, conflicts, pacing
4. **ForeshadowPlugin** - Plant/payoff tracking
5. **TimelinePlugin** - Chronology and time consistency
6. **ScenePlugin** - Scene descriptions and atmosphere
7. **DialoguePlugin** - Dialogue consistency and character voice

## API Layer

**Routes (api/routes/):**
- **sessions.py** - Session CRUD, progress tracking, export
- **websocket.py** - Real-time execution control
- **prompts.py** - Prompt template management

**WebSocket Events:**
```
subscribe      → Subscribe to session updates
start          → Start execution (creates LoopEngine, registers)
pause          → Pause running engine
resume         → Resume paused engine
stop           → Stop engine
approve_task   → Approve/reject current task result
feedback       → Submit user feedback
preview        → Get task result preview
```

## Storage Layer

**SessionStorage (storage/session.py):**
- SQLAlchemy models: SessionModel, TaskResultModel
- Async engine with async_sessionmaker
- Session state, progress tracking, task persistence
- Checkpoint/resume capability

**VectorStore (storage/vector_store.py):**
- ChromaDB with persistent client
- Aliyun embedding function (text-embedding-v3)
- MemoryType enum for categorization
- Chapter-scoped retrieval

## Data Flow

```
User Request (WebSocket)
    ↓
API Handler (websocket.py)
    ↓
EngineRegistry.register(session_id, engine)
    ↓
LoopEngine.run(goal, chapter_count)
    ↓
TaskPlanner.plan() → Generate Task DAG
    ↓
[For Each Task]:
    ├─ PluginManager.before_task()
    ├─ VectorMemoryManager.get_context()
    ├─ MultiLLMClient.generate() [Routed by task type]
    ├─ EvaluationEngine.evaluate()
    ├─ If score < threshold: _attempt_rewrite()
    ├─ PluginManager.after_task()
    └─ VectorMemoryManager.store()
    ↓
WebSocket broadcast progress updates
    ↓
SessionStorage.persist()
```

## External Dependencies

**LLM Providers:**
- Aliyun Qwen (dashscope SDK)
- DeepSeek (OpenAI-compatible API)
- Ark/Doubao (VolcEngine)

**Storage:**
- PostgreSQL (asyncpg driver)
- ChromaDB (persistent vector store)
- sentence-transformers (embedding fallback)

**Web Framework:**
- FastAPI 0.104+ (async web framework)
- uvicorn (ASGI server)
- websockets (real-time communication)

## Configuration

**Environment Variables (.env):**
- `ALIYUN_API_KEY` - Qwen API access
- `DEEPSEEK_API_KEY` - DeepSeek API access
- `ARK_API_KEY` - Doubao API access
- `DATABASE_URL` - PostgreSQL connection
- `CHROMA_PERSIST_DIRECTORY` - Vector storage path

**Settings (utils/config.py):**
- Pydantic-based configuration
- Development vs production modes
- CORS origins, API timeouts
- Embedding model selection

## Frontend Architecture

**Stack:** React 18 + TypeScript + Vite + Zustand + Tailwind CSS

**State Management (Zustand Stores):**
- sessionStore - Session list and current session
- taskStore - Task list and progress
- previewStore - Task result preview
- wsStatusStore - WebSocket connection status
- chatStore - User feedback and chat

**Components Structure:**
```
components/
├── layout/
│   ├── MainLayout      - Main app shell
│   ├── Header          - Top navigation
│   ├── Sidebar         - Session list
│   └── WorkspaceLayout - Writing workspace
├── ui/                 - Reusable UI components
├── SessionCard         - Session display
├── TaskCard            - Task display with controls
├── PreviewPanel        - Task result preview
├── TaskApproval        - Approve/reject modal
└── ExportDialog        - Export options
```

## Key Design Patterns

1. **Singleton Pattern:** EngineRegistry, PromptEvolver
2. **Plugin Pattern:** NovelElementPlugin extensible system
3. **Strategy Pattern:** MultiLLMClient task routing
4. **Observer Pattern:** WebSocket event broadcasting
5. **Repository Pattern:** SessionStorage, VectorStore
6. **Factory Pattern:** Plugin instantiation, LLM client creation

## Scalability Considerations

**Current Design:**
- Single-process execution (not distributed)
- In-memory engine registry (EngineRegistry)
- Local ChromaDB persistence

**Future Improvements:**
- Redis for distributed engine registry
- Celery/RQ for background task processing
- Separate vector DB service (Qdrant, Milvus)
- Message queue (RabbitMQ, Kafka) for async operations

## Security Notes

- API keys stored in environment variables only
- CORS configured for specific origins
- SQL injection prevented via SQLAlchemy ORM
- WebSocket connections require session_id
- No user authentication yet (TODO)

---

**Related Codemaps:**
- [Backend Structure](backend.md) - API routes and handlers
- [Frontend Structure](frontend.md) - React components and state
- [Data Models](data.md) - Schemas and storage models
