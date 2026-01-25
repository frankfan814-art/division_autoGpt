# Backend Architecture - API & Core Logic

**Last Updated:** 2025-01-25
**Framework:** FastAPI (Python 3.12+)
**Entry Point:** api/main.py → create_app()

## Directory Structure

```
src/creative_autogpt/
├── api/
│   ├── main.py                 # FastAPI app factory
│   ├── dependencies.py         # Dependency injection
│   └── routes/
│       ├── sessions.py         # Session CRUD endpoints
│       ├── websocket.py        # Real-time execution
│       └── prompts.py          # Prompt template management
├── core/
│   ├── loop_engine.py          # AutoGPT agent loop
│   ├── task_planner.py         # Task DAG planning
│   ├── evaluator.py            # Quality assessment
│   ├── engine_registry.py      # Engine lifecycle management
│   ├── vector_memory.py        # Memory manager
│   ├── self_evaluator.py       # Self-reflection system
│   └── prompt_evolver.py       # Prompt optimization
├── plugins/
│   ├── base.py                 # Plugin base class
│   ├── manager.py              # Plugin lifecycle
│   ├── character.py            # Character management
│   ├── worldview.py            # World-building
│   ├── event.py                # Plot events
│   ├── foreshadow.py           # Foreshadow tracking
│   ├── timeline.py             # Timeline consistency
│   ├── scene.py                # Scene descriptions
│   └── dialogue.py             # Dialogue consistency
├── storage/
│   ├── session.py              # SQLAlchemy models
│   ├── vector_store.py         # ChromaDB integration
│   └── file_store.py           # File-based storage
├── utils/
│   ├── llm_client.py           # Multi-LLM routing
│   ├── config.py               # Configuration
│   └── logger.py               # Logging setup
├── prompts/
│   ├── manager.py              # Prompt template manager
│   └── feedback_transformer.py # User feedback integration
├── modes/
│   ├── base.py                 # Base mode class
│   └── novel.py                # Novel writing mode
└── api/schemas/
    ├── session.py              # Session Pydantic models
    ├── task.py                 # Task Pydantic models
    └── response.py             # Response models
```

## API Routes

### Sessions API (api/routes/sessions.py)

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/sessions | Create new writing session |
| GET | /api/sessions | List all sessions (paginated) |
| GET | /api/sessions/{id} | Get session details |
| PUT | /api/sessions/{id} | Update session |
| DELETE | /api/sessions/{id} | Delete session |
| GET | /api/sessions/{id}/progress | Get execution progress |
| POST | /api/sessions/{id}/export | Export session content |

**Key Dependencies:**
- `get_session_storage()` - SessionStorage instance
- `get_llm_client()` - MultiLLMClient instance
- `get_memory_manager()` - VectorMemoryManager instance

**Response Models:**
- `SessionResponse` - Session details with stats
- `SessionProgress` - Real-time progress tracking
- `SessionListResponse` - Paginated session list

### WebSocket API (api/routes/websocket.py)

**Endpoint:** `WS /ws/ws`

**Connection Manager:**
```python
class ConnectionManager:
    - active_connections: Dict[client_id -> WebSocket]
    - session_subscribers: Dict[session_id -> Set[client_id]]
```

**Event Handlers:**

| Event | Handler | Purpose |
|-------|---------|---------|
| `connect` | websocket_endpoint | Initial connection handshake |
| `subscribe` | handle_subscribe | Subscribe to session updates |
| `start` | handle_start | Create LoopEngine, register in EngineRegistry |
| `pause` | handle_pause | Pause engine via EngineRegistry |
| `resume` | handle_resume | Resume engine via EngineRegistry |
| `stop` | handle_stop | Stop engine, unregister |
| `approve_task` | handle_approve_task | User approves current task |
| `feedback` | handle_feedback | Submit user feedback |
| `preview` | handle_preview | Get current task preview |
| `ping` | websocket_endpoint | Heartbeat check |

**WebSocket Message Flow:**
```
Client → {"event": "start", "session_id": "...", "goal": {...}}
        ↓
    Verify session exists
        ↓
    Create LoopEngine(session_id, llm_client, memory, evaluator)
        ↓
    EngineRegistry.register(session_id, engine)
        ↓
    await engine.run(goal, chapter_count)
        ↓
    [Broadcast progress updates to subscribers]
        ↓
Client ← {"event": "progress", "progress": {...}}
```

### Prompts API (api/routes/prompts.py)

**Endpoints:**
- `GET /api/prompts` - List all prompt templates
- `GET /api/prompts/{name}` - Get specific template
- `PUT /api/prompts/{name}` - Update template
- `POST /api/prompts/evolve` - Evolve prompt based on feedback

**Purpose:** Dynamic prompt management for runtime optimization

## Core Execution Engine

### LoopEngine (core/loop_engine.py)

**Initialization:**
```python
engine = LoopEngine(
    session_id=str,
    llm_client=MultiLLMClient,
    memory=VectorMemoryManager,
    evaluator=EvaluationEngine,
    config=Dict  # Optional configuration
)
```

**Execution Flow:**
```
run(goal, chapter_count)
    │
    ├─ Phase 1: Planning
    │   └─ tasks = planner.plan(goal, chapter_count)
    │
    ├─ Phase 2: Execution Loop
    │   │
    │   └─ While is_running:
    │       ├─ task = planner.get_next_task()
    │       ├─ _execute_task(task, goal)
    │       │   ├─ PluginManager.before_task()
    │       │   ├─ context = memory.get_context()
    │       │   ├─ response = llm_client.generate()
    │       │   ├─ evaluation = evaluator.evaluate()
    │       │   ├─ If score < threshold: _attempt_rewrite()
    │       │   └─ PluginManager.after_task()
    │       │
    │       └─ broadcast(progress)
    │
    └─ Phase 3: Completion
        └─ return ExecutionResult
```

**Control Methods:**
- `pause()` - Set is_paused=True, status=PAUSED
- `resume()` - Set is_paused=False, status=RUNNING
- `stop()` - Set is_running=False, status=STOPPED

**Callback System:**
```python
engine.set_callbacks(
    on_task_start=Callable,
    on_task_complete=Callable,
    on_task_fail=Callable,
    on_progress=Callable,
    on_task_approval_needed=Callable
)
```

### TaskPlanner (core/task_planner.py)

**Task Definition:**
```python
@dataclass
class Task:
    task_id: str
    task_type: NovelTaskType
    description: str
    status: str  # pending, ready, running, completed, failed
    depends_on: List[str]  # Task IDs
    is_foundation: bool  # Stored in vector DB for retrieval
    retry_count: int
    max_retries: int = 3
```

**Dependency Resolution:**
```python
# Short novel (<=3 chapters): 5 base tasks
创意脑暴 → 故事核心 → 大纲 → 世界观规则 → 人物设计

# Full flow: 15+ tasks with chapter generation
创意脑暴 → 故事核心 → 大纲 → 世界观规则 → 人物设计
→ 主题确认 → 风格元素 → 市场定位
→ 事件 → 场景物品冲突 → 伏笔列表
→ 一致性检查
→ [Chapter N tasks: 章节大纲 → 章节内容 → 章节润色]
```

**Methods:**
- `plan(goal, chapter_count)` - Generate task DAG
- `get_next_task()` - Get next ready task
- `update_task_status(task_id, status, result)` - Mark task complete
- `get_progress()` - Return progress statistics

### EvaluationEngine (core/evaluator.py)

**Evaluation Criteria:**
```python
class EvaluationCriterion(str, Enum):
    COHERENCE = "coherence"
    CREATIVITY = "creativity"
    QUALITY = "quality"
    CONSISTENCY = "consistency"
    GOAL_ALIGNMENT = "goal_alignment"
    CHARACTER_VOICE = "character_voice"
    PLOT_PROGRESSION = "plot_progression"
    DIALOGUE_QUALITY = "dialogue_quality"
```

**Evaluation Process:**
```python
evaluate(task_type, content, context, goal)
    │
    ├─ Determine criteria for task_type
    │   └─ CONTENT_TYPE_CRITERIA.get(task_type, DEFAULT_CRITERIA)
    │
    ├─ If llm_client:
    │   └─ _llm_evaluate() → DeepSeek, temp=0.3
    │
    └─ Else:
        └─ _rule_based_evaluate() → Heuristics

return EvaluationResult(
    passed: bool,
    score: float (0-1),
    dimension_scores: Dict[str, DimensionScore],
    reasons: List[str],
    suggestions: List[str]
)
```

**Passing Threshold:** Default 0.7 (configurable)

## Plugin System

### Plugin Base Class (plugins/base.py)

**Abstract Methods:**
```python
class NovelElementPlugin(ABC):
    @abstractmethod
    async def on_init(self, context: WritingContext) -> None

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]

    @abstractmethod
    def get_prompts(self) -> Dict[str, str]

    @abstractmethod
    def get_tasks(self) -> List[Dict[str, Any]]

    @abstractmethod
    async def validate(self, data, context) -> ValidationResult
```

**Optional Hooks:**
```python
async def on_before_task(task, context) -> Dict
async def on_after_task(task, result, context) -> str
async def on_finalize(context) -> None
async def enrich_context(task, context) -> Dict
```

### Plugin Manager (plugins/manager.py)

**Registration:**
```python
manager = PluginManager()
manager.register(plugin_instance)
manager.enable(plugin_name)
manager.disable(plugin_name)
```

**Execution:**
```python
# Execute hooks in priority order
await manager.run_hook("on_init", context)
await manager.before_task(task, context)
await manager.after_task(task, result, context)
```

**Priority System:**
- Higher priority = executed first
- Default: 50
- Range: 0-100

### Implemented Plugins

| Plugin | Purpose | Key Methods |
|--------|---------|-------------|
| CharacterPlugin | Character profiles, relationships, arcs | validate_characters(), get_relationships() |
| WorldViewPlugin | World settings, power systems, locations | validate_rules(), get_locations() |
| EventPlugin | Plot events, conflicts, pacing | validate_timeline(), get_conflicts() |
| ForeshadowPlugin | Plant/payoff tracking | validate_payoffs(), get_unresolved() |
| TimelinePlugin | Chronology consistency | validate_order(), get_timeline() |
| ScenePlugin | Scene descriptions, atmosphere | validate_atmosphere(), get_scenes() |
| DialoguePlugin | Dialogue consistency, voice | validate_voice(), get_dialogue_samples() |

## Multi-LLM Client

### Client Architecture (utils/llm_client.py)

**Supported Providers:**
```python
class LLMProvider(str, Enum):
    ALIYUN = "aliyun"    # Qwen (dashscope)
    DEEPSEEK = "deepseek"
    ARK = "ark"          # Doubao (VolcEngine)
    NVIDIA = "nvidia"
```

**Task Type Routing:**
```python
DEFAULT_TASK_TYPE_MAP = {
    # Qwen (Long context, global planning)
    "大纲": LLMProvider.ALIYUN,
    "风格元素": LLMProvider.ALIYUN,
    "人物设计": LLMProvider.ALIYUN,
    "主题确认": LLMProvider.ALIYUN,
    "世界观": LLMProvider.ALIYUN,

    # DeepSeek (Logic, cost-effective)
    "事件": LLMProvider.DEEPSEEK,
    "场景物品": LLMProvider.DEEPSEEK,
    "评估": LLMProvider.DEEPSEEK,
    "一致性检查": LLMProvider.DEEPSEEK,
    "时间线": LLMProvider.DEEPSEEK,
    "伏笔": LLMProvider.DEEPSEEK,

    # Doubao (Creative writing)
    "章节内容": LLMProvider.ARK,
    "修订": LLMProvider.ARK,
    "润色": LLMProvider.ARK,
    "对话检查": LLMProvider.ARK,
}
```

**Retry Logic:**
- Max retries: 5 (increased from default)
- Exponential backoff: min(2^attempt * 2, 60) seconds
- Special handling for RateLimitError, APIConnectionError, TimeoutError

### Usage Example
```python
client = MultiLLMClient()
response = await client.generate(
    prompt="Write chapter 1...",
    task_type="章节内容",  # Routes to Doubao
    temperature=0.8,
    max_tokens=4000
)
```

## Storage Layer

### SessionStorage (storage/session.py)

**SQLAlchemy Models:**
```python
class SessionModel(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)
    goal = Column(JSON)
    config = Column(JSON)
    # Statistics
    total_tasks = Column(Integer)
    completed_tasks = Column(Integer)
    tokens_used = Column(Integer)

class TaskResultModel(Base):
    __tablename__ = "task_results"
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    task_id = Column(String, index=True)
    task_type = Column(String)
    result = Column(Text)
    evaluation = Column(JSON)
    chapter_index = Column(Integer)
```

**Methods:**
- `create_session(title, mode, goal, config)` → session_id
- `get_session(session_id)` → SessionModel
- `update_session_progress(session_id, stats)`
- `save_task_result(session_id, task_id, result, evaluation)`
- `get_session_results(session_id)` → List[TaskResult]

### VectorStore (storage/vector_store.py)

**ChromaDB Integration:**
```python
class VectorStore:
    collection: Collection  # ChromaDB collection
    embedding_function: EmbeddingFunction

    async def add(content, memory_type, metadata, task_id, chapter_id)
    async def search(query, top_k, memory_type, chapter_index) → List[SearchResult]
    async def delete_by_task(task_id)
```

**Memory Types:**
```python
class MemoryType(str, Enum):
    CHARACTER = "character"
    PLOT = "plot"
    WORLDVIEW = "worldview"
    FORESHADOW = "foreshadow"
    SCENE = "scene"
    CHAPTER = "chapter"
    OUTLINE = "outline"
    GENERAL = "general"
```

**Embedding Function:**
- Primary: Aliyun DashScope (text-embedding-v3)
- Fallback: sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)

## Engine Registry (core/engine_registry.py)

**Singleton Pattern:**
```python
registry = EngineRegistry()  # Global singleton

# In WebSocket handler
await registry.register(session_id, engine)
await registry.pause(session_id)
await registry.resume(session_id)
await registry.stop(session_id)
```

**Thread-Safe Operations:**
- All mutations protected by `asyncio.Lock`
- Background cleanup task (runs every 60s)
- Removes completed engines after 5 minutes

## Dependency Injection (api/dependencies.py)

**FastAPI Dependencies:**
```python
async def get_session_storage() → SessionStorage
async def get_llm_client() → MultiLLMClient
async def get_memory_manager() → VectorMemoryManager
async def get_evaluator(llm_client) → EvaluationEngine
async def get_plugin_manager() → PluginManager
```

**Lifecycle:**
- Created on app startup via `lifespan()` context manager
- Cached as singletons for request duration
- Cleaned up on app shutdown

## Middleware & Error Handling

**CORS Middleware (api/main.py):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Global Exception Handler:**
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc)
    → JSONResponse(status_code=500, detail=...)
```

**Request Logging:**
```python
@app.middleware("http")
async def log_requests(request, call_next)
    → Logs: METHOD PATH - STATUS
```

## Background Tasks

**Engine Cleanup (EngineRegistry):**
```python
async def _cleanup_loop():
    while True:
        await asyncio.sleep(60)
        # Remove completed/failed/stopped engines
        # Check completion time (5 min threshold)
```

## Configuration

**Settings (utils/config.py):**
```python
class Settings(BaseSettings):
    # API Keys
    aliyun_api_key: str
    deepseek_api_key: str
    ark_api_key: str

    # Database
    database_url: str = "sqlite+aiosqlite:///./sessions.db"

    # ChromaDB
    chroma_persist_directory: str = "./data/chroma"

    # API Settings
    cors_origins: List[str] = ["http://localhost:5173"]
    is_development: bool = True
```

**Environment:** `.env` file with `ALIYUN_API_KEY`, `DEEPSEEK_API_KEY`, `ARK_API_KEY`

## Key Backend Patterns

1. **Async/Await Throughout:** All I/O operations are async
2. **Dependency Injection:** FastAPI dependencies for testability
3. **Singleton Services:** EngineRegistry, PromptEvolver
4. **Plugin Architecture:** Extensible via NovelElementPlugin
5. **Event Broadcasting:** WebSocket pub/sub pattern
6. **Repository Pattern:** Storage abstraction (SessionStorage, VectorStore)
7. **Strategy Pattern:** MultiLLMClient routing

---

**Related Codemaps:**
- [Architecture Overview](architecture.md) - System-wide architecture
- [Data Models](data.md) - Schemas and storage models
- [Frontend Structure](frontend.md) - Client-side architecture
