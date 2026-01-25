# Data Models & Schemas

**Last Updated:** 2025-01-25
**Purpose:** Shared data structures across frontend and backend

## Overview

The system uses three primary data representation layers:
1. **SQLAlchemy Models** - Database persistence (backend)
2. **Pydantic Schemas** - API validation and serialization (backend)
3. **TypeScript Interfaces** - Frontend type safety (client)

## Session Data Models

### SQLAlchemy Model (storage/session.py)

```python
class SessionModel(Base_Model):
    __tablename__ = "sessions"

    # Primary Key
    id: str = Column(String, primary_key=True)

    # Core Fields
    title: str = Column(String, nullable=False)
    mode: str = Column(String, nullable=False, default="novel")
    status: str = Column(String, nullable=False, default=SessionStatus.CREATED.value)

    # JSON Fields
    goal: Dict[str, Any] = Column(JSON, nullable=True)
    config: Dict[str, Any] = Column(JSON, nullable=True)

    # Timestamps
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: datetime = Column(DateTime, nullable=True)

    # Statistics
    total_tasks: int = Column(Integer, default=0)
    completed_tasks: int = Column(Integer, default=0)
    failed_tasks: int = Column(Integer, default=0)
    llm_calls: int = Column(Integer, default=0)
    tokens_used: int = Column(Integer, default=0)
```

### Pydantic Schema (api/schemas/session.py)

```python
class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    mode: str = Field(default="novel")
    goal: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)

class SessionResponse(BaseModel):
    id: str
    title: str
    mode: str
    status: SessionStatus
    goal: Dict[str, Any]
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    llm_calls: int
    tokens_used: int

class SessionProgress(BaseModel):
    session_id: str
    status: SessionStatus
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    percentage: float
    current_task: Optional[str]
    estimated_remaining: Optional[int]  # seconds
```

### TypeScript Interface (frontend/src/types/index.ts)

```typescript
enum SessionStatus {
  CREATED = 'created',
  RUNNING = 'running',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

interface Session {
  id: string
  title: string
  mode: string
  status: SessionStatus
  goal: Goal
  config: Config
  created_at: string  // ISO datetime
  updated_at: string  // ISO datetime
  completed_at: string | null
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  llm_calls: number
  tokens_used: number
}

interface Goal {
  title?: string
  genre?: string
  theme?: string
  style?: string
  length?: string  // "短篇", "中篇", "长篇"
  chapter_count?: number
  target_audience?: string
  // Additional custom fields
}

interface Config {
  approval_mode?: boolean  // Require user approval for tasks
  high_score_threshold?: number  // Minimum score for "best examples"
  enable_self_evolution?: boolean  // Enable prompt evolution
  max_retries?: number
  quality_threshold?: number  // Minimum passing score
  // Additional config options
}
```

## Task Data Models

### Task Definition (core/task_planner.py)

```python
class NovelTaskType(str, Enum):
    # Phase 0: Creative Brainstorm
    CREATIVE_BRAINSTORM = "创意脑暴"
    STORY_CORE = "故事核心"

    # Phase 1: Planning
    STYLE_ELEMENTS = "风格元素"
    THEME_CONFIRMATION = "主题确认"
    MARKET_POSITIONING = "市场定位"
    OUTLINE = "大纲"

    # Phase 2: Element Creation
    CHARACTER_DESIGN = "人物设计"
    WORLDVIEW_RULES = "世界观规则"
    EVENTS = "事件"
    SCENES_ITEMS_CONFLICTS = "场景物品冲突"
    FORESHADOW_LIST = "伏笔列表"

    # Phase 3: Consistency
    CONSISTENCY_CHECK = "一致性检查"

    # Phase 4: Chapter Generation
    CHAPTER_OUTLINE = "章节大纲"
    SCENE_GENERATION = "场景生成"
    CHAPTER_CONTENT = "章节内容"
    CHAPTER_POLISH = "章节润色"

    # Phase 5: Evaluation & Revision
    EVALUATION = "评估"
    REVISION = "修订"

@dataclass
class TaskDefinition:
    task_type: NovelTaskType
    description: str
    depends_on: List[str]
    metadata: Dict[str, Any]
    optional: bool
    can_parallel: bool
    is_foundation: bool  # Stored in vector DB for retrieval
```

### Task Instance (core/task_planner.py)

```python
@dataclass
class Task:
    task_id: str
    task_type: NovelTaskType
    description: str
    status: str  # pending, ready, running, completed, failed, skipped
    depends_on: List[str]
    dependencies_met: bool
    metadata: Dict[str, Any]
    optional: bool
    can_parallel: bool
    result: Optional[str]
    error: Optional[str]
    retry_count: int
    max_retries: int

    # Statistics
    started_at: Optional[str]  # ISO datetime
    completed_at: Optional[str]  # ISO datetime
    execution_time_seconds: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    failed_attempts: int
    is_foundation: bool
```

### Pydantic Schema (api/schemas/task.py)

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    description: str
    status: TaskStatus
    depends_on: List[str]
    metadata: Dict[str, Any]
    optional: bool
    is_foundation: bool
    result: Optional[str]
    error: Optional[str]
    retry_count: int
    chapter_index: Optional[int]
    started_at: Optional[str]
    completed_at: Optional[str]
    execution_time_seconds: float

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int
```

### TypeScript Interface

```typescript
enum TaskStatus {
  PENDING = 'pending',
  READY = 'ready',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped'
}

type TaskType =
  | '创意脑暴' | '故事核心'
  | '风格元素' | '主题确认' | '市场定位' | '大纲'
  | '人物设计' | '世界观规则'
  | '事件' | '场景物品冲突' | '伏笔列表'
  | '一致性检查'
  | '章节大纲' | '场景生成' | '章节内容' | '章节润色'
  | '评估' | '修订'

interface Task {
  task_id: string
  task_type: TaskType
  description: string
  status: TaskStatus
  depends_on: string[]
  metadata: TaskMetadata
  optional: boolean
  can_parallel: boolean
  is_foundation: boolean
  result?: string
  error?: string
  retry_count: number
  max_retries: number
  chapter_index?: number

  // Statistics
  started_at?: string  // ISO datetime
  completed_at?: string  // ISO datetime
  execution_time_seconds: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  cost_usd: number
  failed_attempts: number
}

interface TaskMetadata {
  chapter_index?: number
  genre?: string
  goal_style?: string
  goal_theme?: string
  goal_length?: string
  [key: string]: any
}
```

## Task Result Models

### SQLAlchemy Model (storage/session.py)

```python
class TaskResultModel(Base_Model):
    __tablename__ = "task_results"

    id: str = Column(String, primary_key=True)
    session_id: str = Column(String, nullable=False, index=True)
    task_id: str = Column(String, nullable=False, index=True)
    task_type: str = Column(String, nullable=False)
    status: str = Column(String, nullable=False)
    result: str = Column(Text, nullable=True)
    error: str = Column(Text, nullable=True)
    task_metadata: Dict[str, Any] = Column(JSON, nullable=True)
    evaluation: Dict[str, Any] = Column(JSON, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    chapter_index: int = Column(Integer, nullable=True)
```

### In-Memory Result (core/vector_memory.py)

```python
@dataclass
class TaskResult:
    task_id: str
    task_type: str
    content: str
    memory_type: MemoryType
    metadata: Dict[str, Any]
    chapter_index: Optional[int]
    created_at: datetime
    evaluation: Optional[Dict[str, Any]]
```

## Evaluation Data Models

### Evaluation Result (core/evaluator.py)

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

@dataclass
class DimensionScore:
    dimension: str
    score: float  # 0.0 to 1.0
    reason: str
    suggestions: List[str]

@dataclass
class EvaluationResult:
    passed: bool
    score: float  # Overall score 0.0 to 1.0
    dimension_scores: Dict[str, DimensionScore]
    reasons: List[str]
    suggestions: List[str]
    evaluated_at: datetime
    evaluator: str  # "llm_deepseek", "rule_based"
    metadata: Dict[str, Any]
```

### TypeScript Interface

```typescript
enum EvaluationCriterion {
  COHERENCE = 'coherence',
  CREATIVITY = 'creativity',
  QUALITY = 'quality',
  CONSISTENCY = 'consistency',
  GOAL_ALIGNMENT = 'goal_alignment',
  CHARACTER_VOICE = 'character_voice',
  PLOT_PROGRESSION = 'plot_progression',
  DIALOGUE_QUALITY = 'dialogue_quality'
}

interface DimensionScore {
  dimension: EvaluationCriterion
  score: number  // 0.0 to 1.0
  reason: string
  suggestions: string[]
}

interface Evaluation {
  passed: boolean
  score: number  // 0.0 to 1.0
  dimension_scores: Record<string, DimensionScore>
  reasons: string[]
  suggestions: string[]
  evaluated_at: string  // ISO datetime
  evaluator: string
  metadata?: Record<string, any>
}

// Helper to convert score to percentage
function scoreToPercentage(score: number): number {
  return Math.round(score * 100)
}
```

## Vector Memory Models

### Memory Item (storage/vector_store.py)

```python
class MemoryType(str, Enum):
    CHARACTER = "character"
    PLOT = "plot"
    SETTING = "setting"
    DIALOGUE = "dialogue"
    WORLDVIEW = "worldview"
    FORESHADOW = "foreshadow"
    SCENE = "scene"
    CHAPTER = "chapter"
    OUTLINE = "outline"
    GENERAL = "general"

@dataclass
class VectorMemoryItem:
    id: str
    content: str
    memory_type: MemoryType
    metadata: Dict[str, Any]
    task_id: Optional[str]
    chapter_index: Optional[int]
    created_at: datetime
    embedding: Optional[List[float]]
```

### Memory Context (core/vector_memory.py)

```python
@dataclass
class MemoryContext:
    task_id: str
    task_type: str
    recent_results: List[Dict[str, Any]]  # Last N tasks
    relevant_memories: List[Dict[str, Any]]  # Semantic search
    chapter_context: List[Dict[str, Any]]  # Chapter-scoped
    task_memories: List[Dict[str, Any]]  # Previous attempts
```

### TypeScript Interface

```typescript
enum MemoryType {
  CHARACTER = 'character',
  PLOT = 'plot',
  SETTING = 'setting',
  DIALOGUE = 'dialogue',
  WORLDVIEW = 'worldview',
  FORESHADOW = 'foreshadow',
  SCENE = 'scene',
  CHAPTER = 'chapter',
  OUTLINE = 'outline',
  GENERAL = 'general'
}

interface VectorMemoryItem {
  id: string
  content: string
  memory_type: MemoryType
  metadata: Record<string, any>
  task_id?: string
  chapter_index?: number
  created_at: string  // ISO datetime
}

interface MemoryContext {
  task_id: string
  task_type: string
  recent_results: VectorMemoryItem[]
  relevant_memories: SearchResult[]
  chapter_context: SearchResult[]
  task_memories: VectorMemoryItem[]
}

interface SearchResult {
  item: VectorMemoryItem
  score: number  // Similarity score
  distance?: number
}
```

## Plugin Data Models

### Plugin Configuration (plugins/base.py)

```python
@dataclass
class PluginConfig:
    enabled: bool
    priority: int  # 0-100, higher first
    phases: List[PluginPhase]
    settings: Dict[str, Any]

class PluginPhase(str, Enum):
    PLANNING = "planning"
    GENERATION = "generation"
    EVALUATION = "evaluation"
    POST_PROCESS = "post_process"
```

### Validation Result (plugins/base.py)

```python
@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
```

### Writing Context (plugins/base.py)

```python
@dataclass
class WritingContext:
    session_id: str
    goal: Dict[str, Any]
    current_task: Optional[Dict[str, Any]]
    current_chapter: Optional[int]
    results: Dict[str, Any]  # task_id -> result
    metadata: Dict[str, Any]
```

### TypeScript Interface

```typescript
enum PluginPhase {
  PLANNING = 'planning',
  GENERATION = 'generation',
  EVALUATION = 'evaluation',
  POST_PROCESS = 'post_process'
}

interface PluginConfig {
  enabled: boolean
  priority: number  // 0-100
  phases: PluginPhase[]
  settings: Record<string, any>
}

interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  suggestions: string[]
}

interface WritingContext {
  session_id: string
  goal: Goal
  current_task?: Task
  current_chapter?: number
  results: Record<string, any>  // task_id -> result
  metadata: Record<string, any>
}
```

## WebSocket Event Models

### Event Types

```typescript
type WebSocketEvent =
  | { event: 'connected'; client_id: string }
  | { event: 'subscribed'; session_id: string }
  | { event: 'progress'; data: ProgressData }
  | { event: 'task_complete'; data: TaskCompleteData }
  | { event: 'task_failed'; data: TaskFailedData }
  | { event: 'approval_needed'; data: ApprovalData }
  | { event: 'error'; message: string }
  | { event: 'pong' }

interface ProgressData {
  session_id: string
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  running_tasks: number
  ready_tasks: number
  percentage: number
  current_task: string
  is_completed: boolean
}

interface TaskCompleteData {
  session_id: string
  task_id: string
  task_type: string
  result: string
  evaluation: Evaluation
}

interface TaskFailedData {
  session_id: string
  task_id: string
  task_type: string
  error: string
  retry_count: number
}

interface ApprovalData {
  session_id: string
  task_id: string
  task_type: string
  result: string
  evaluation: Evaluation
}
```

## LLM Response Models

### LLM Response (utils/llm_client.py)

```python
class LLMProvider(str, Enum):
    ALIYUN = "aliyun"
    DEEPSEEK = "deepseek"
    ARK = "ark"
    NVIDIA = "nvidia"

@dataclass
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: LLMProvider
    usage: LLMUsage
    raw_response: Optional[Dict[str, Any]]
    cached: bool
    generation_time: float
```

### TypeScript Interface

```typescript
enum LLMProvider {
  ALIYUN = 'aliyun',
  DEEPSEEK = 'deepseek',
  ARK = 'ark',
  NVIDIA = 'nvidia'
}

interface LLMUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

interface LLMResponse {
  content: string
  model: string
  provider: LLMProvider
  usage: LLMUsage
  raw_response?: Record<string, any>
  cached: boolean
  generation_time: number
}
```

## Prompt Template Models

### Prompt Template (prompts/manager.py)

```python
@dataclass
class PromptTemplate:
    name: str
    task_type: str
    template: str
    variables: List[str]  # Required variables
    metadata: Dict[str, Any]
    version: str
    evolved_from: Optional[str]  # Parent template
    performance_score: Optional[float]  # Average evaluation score
    created_at: datetime
    updated_at: datetime
```

### TypeScript Interface

```typescript
interface PromptTemplate {
  name: string
  task_type: TaskType
  template: string
  variables: string[]
  metadata: Record<string, any>
  version: string
  evolved_from?: string  // Parent template name
  performance_score?: number  // 0.0 to 1.0
  created_at: string  // ISO datetime
  updated_at: string  // ISO datetime
}
```

## Data Validation Rules

### Session Validation

**Title:** 1-200 characters, required
**Mode:** Must be one of ["novel", "story", "script"]
**Status:** Must be valid SessionStatus enum
**Chapter Count:** Must be positive integer if provided

### Task Validation

**Task Type:** Must be valid NovelTaskType enum
**Status:** Must be valid TaskStatus enum
**Dependencies:** Must reference existing task_ids
**Retry Count:** Must be <= max_retries

### Evaluation Validation

**Score:** Must be between 0.0 and 1.0
**Dimension Scores:** All dimensions must be 0.0 to 1.0
**Threshold:** Must be between 0.0 and 1.0

## Data Flow Between Layers

```
Database (SQLAlchemy)
    ↓
SessionStorage / TaskResultStorage
    ↓
Pydantic Schemas (validation)
    ↓
API Response (JSON)
    ↓
Frontend (TypeScript Interfaces)
    ↓
Zustand Stores (state)
    ↓
React Components (props)
```

## Migration Strategy

**Alembic Migrations (alembic/versions/):**
- Version-controlled schema changes
- Migration scripts for SQLAlchemy models
- Backward compatibility checks

**Type Safety:**
- Backend: Pydantic validates all API inputs/outputs
- Frontend: TypeScript ensures type correctness
- Contract: OpenAPI schema generated from Pydantic

---

**Related Codemaps:**
- [Architecture Overview](architecture.md) - System-wide data flow
- [Backend Structure](backend.md) - Storage and persistence
- [Frontend Structure](frontend.md) - Client-side state management
