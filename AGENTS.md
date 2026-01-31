# AGENTS.md

This file provides guidelines for agentic coding agents operating in this repository.

## Quick Start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py init
python scripts/run_server.py
```

## Build/Lint/Test Commands

### Backend (Python)

```bash
# Format (line length: 120)
black src/

# Lint
pylint src/
ruff check src/

# Type check
mypy src/

# Run all tests
pytest tests/ -v

# Run single test
pytest tests/test_loop_engine.py::test_pause_resume -v

# Run by marker
pytest tests/ -m unit
pytest tests/ -m integration
pytest tests/ -m "not slow"

# Coverage
pytest tests/ --cov=src/creative_autogpt --cov-report=html
```

### Frontend (TypeScript/React)

```bash
cd frontend

# Install dependencies
npm install

# Dev server (port 5173)
npm run dev

# Build
npm run build

# Type check
npm run type-check

# Lint
npm run lint

# E2E tests
npm run test:e2e
npm run test:e2e:ui
npm run test:e2e:debug
```

**Frontend Pages Implemented:**

| Page | Route | Status | Description |
|------|-------|--------|-------------|
| Dashboard | `/dashboard/:sessionId` | ✅ Complete | Project overview, progress stats, quality overview, warnings |
| ChapterList | `/dashboard/:sessionId/chapters` | ✅ Complete | Filter/sort chapters, export |
| ChapterDetail | `/dashboard/:sessionId/chapters/:index` | ✅ Complete | Version history, rewrite, manual edit |
| Characters | `/dashboard/:sessionId/characters` | ✅ Complete | CRUD, filter by role, statistics |
| Foreshadow | `/dashboard/:sessionId/foreshadow` | ✅ Complete | CRUD, filter by status/importance, warnings |
| Create | `/create` | ✅ Complete | Project creation, smart enhancement, derivative mode |
| Sessions | `/sessions` | ✅ Complete | Session list, create/manage sessions |
| Workspace | `/workspace/:sessionId` | ✅ Complete | Real-time execution, task approval |

## System Implementation Status

### ✅ Progressive Writing Plan - 100% Implemented

All features from `docs/progressive_writing_plan.md` have been fully implemented.

### Task Flow (14 Tasks - All Implemented)

| Phase | Task | Status | Description |
|-------|------|--------|-------------|
| Phase 0 | Creative Brainstorm | ✅ | Generate 3-5 story ideas |
| Phase 1 | Outline | ✅ | Complete story outline with events, foreshadowing, chapter planning |
| Phase 2 | Worldview Rules | ✅ | World operating rules, limitations, possibilities |
| Phase 2 | Faction Design | ✅ | Sects, families, organizations (beliefs, goals, abilities) |
| Phase 3 | Scene Design | ✅ | Secret realms, forbidden lands, relics, cave dwellings |
| Phase 3 | Character Design | ✅ | Character profiles, relationships, growth arcs |
| Phase 3 | Power System | ✅ | Techniques, magical treasures, cultivation realms |
| Phase 3 | Protagonist Growth | ✅ | Realm progression, breakthroughs, awakening moments |
| Phase 4 | Villain Design | ✅ | Ultimate villain, mid-tier villains, episodic opponents |
| Phase 4 | Events | ✅ | Detailed event planning (chapters, characters, causes, outcomes) |
| Phase 4 | Timeline | ✅ | Event sequence, character age changes, cultivation time spans |
| Phase 5 | Foreshadow List | ✅ | Systematic foreshadowing management |
| Phase 5 | Story Unit Plan | ✅ | Detailed planning for each story module (100-200 chapters) |
| Phase 6 | Chapter Content | ✅ | Chapter-by-chapter generation with dependency tracking |
| Phase 7 | Quality Check | ✅ | Consistency check + Dialogue check (auto-run after each chapter) |

### Plugin System (11 Plugins - All Implemented)

| Plugin | File | Purpose | Status |
|--------|------|---------|--------|
| CharacterPlugin | `plugins/character.py` | Character profiles, relationships, voice styles | ✅ |
| WorldViewPlugin | `plugins/worldview.py` | World settings, factions, locations | ✅ |
| EventPlugin | `plugins/event.py` | Event chains, conflict design | ✅ |
| ForeshadowPlugin | `plugins/foreshadow.py` | Foreshadow tracking, plant/payoff records | ✅ |
| TimelinePlugin | `plugins/timeline.py` | Timeline management, flashback/flashforward tracking | ✅ |
| ScenePlugin | `plugins/scene.py` | Scene descriptions, atmosphere | ✅ |
| DialoguePlugin | `plugins/dialogue.py` | Dialogue styles, consistency checking | ✅ |
| PowerPlugin | `plugins/power.py` | Techniques, magical treasures, power systems | ✅ |
| GrowthPlugin | `plugins/growth.py` | Protagonist cultivation, breakthroughs | ✅ |
| VillainPlugin | `plugins/villain.py` | Antagonist hierarchy, development arcs | ✅ |
| StoryUnitPlugin | `plugins/story_unit.py` | Story module planning, unit-level plot architecture | ✅ |
| ExampleExtractorPlugin | `plugins/example_extractor.py` | High-quality content examples | ✅ |

### Core Features (All Implemented)

- ✅ **Progressive Building**: 14 task stages with automatic dependency handling
- ✅ **Three-Layer Context**: Task dependencies + Plugin enrichment + Vector semantic search
- ✅ **Multi-dimensional Evaluation**: Coherence (20%), Creativity (20%), Quality (20%), Consistency (20%), Goal Alignment (20%) - 70-point threshold
- ✅ **Auto-Rewrite**: Up to 3 automatic rewrites with feedback
- ✅ **Quality Gate**: Automatic rewrite if score < 0.7
- ✅ **Plugin Validation**: Internal validation + Cross-plugin consistency + State sync + Foreshadow tracking
- ✅ **Pause/Resume**: Complete state preservation for long-term writing
- ✅ **Single Chapter Rewrite**: Version history with v1/v2/v3 tracking
- ✅ **LLM Routing**: Qwen (long context) / DeepSeek (logic) / Doubao (creativity)
- ✅ **Vector Semantic Search**: ChromaDB integration for long-form memory

### Pause/Resume Functionality

The system fully supports long-term, intermittent novel writing (e.g., writing 1-2 chapters per day):

**Pause (`pause_and_save`):**
- Saves completed task IDs
- Saves current task status
- Saves all plugin states (characters, factions, foreshadowing, etc.)
- Saves execution statistics
- Updates session status to "paused"

**Resume (`resume_from_checkpoint`):**
- Loads engine state from database
- Restores completed task list
- Restores plugin states via `on_init()` hooks
- Restores vector memory from task results
- Continues from exact breakpoint

**State Persistence:**
```
session_storage saves:
- session: Basic info (id, title, status, total_chapters, current_chapter)
- task_results: All task outputs
- chapter_versions: Chapter version history
- plugin_data: Plugin states via save_plugin_data/load_plugin_data
- engine_state: LoopEngine execution state
- vector_memory: Semantic embeddings in ChromaDB
```

### Other Commands

```bash
# Database
python scripts/init_db.py init|reset|clear

# LLM connectivity test
python scripts/test_llm.py --test llm
python scripts/test_llm.py --test embeddings

# System integration test
python scripts/test_system.py
```

## Code Style Guidelines

### General

- **Python version**: 3.10 or higher
- **Line length**: 120 characters
- **All I/O must be async**: Use `async/await` consistently

### Imports

- Use absolute imports from package root
- Group imports: standard library, third-party, local
- Example:
  ```python
  from typing import Dict, List, Optional
  import asyncio
  
  from fastapi import APIRouter
  
  from creative_autogpt.core.loop_engine import LoopEngine
  ```

### Formatting

- Use black for automatic formatting
- Configure editor to use 120-character line width
- No trailing whitespace
- Use 4 spaces for indentation (no tabs)

### Types

- Use type hints for all function signatures
- Prefer `Optional[X]` over `Union[X, None]`
- Use `Dict[K, V]` and `List[T]` from typing
- Complex generic types: use `TypeVar` and `Generic`

### Naming Conventions

- **Files**: snake_case for Python, kebab-case for config
- **Classes**: PascalCase (e.g., `LoopEngine`, `ChapterRewriter`)
- **Functions/variables**: snake_case (e.g., `get_registry`, `task_results`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`)
- **Private methods**: `_leading_underscore`

### Error Handling

- Use try/except with specific exception types
- Log errors before re-raising
- Let caller handle business logic errors
- LLM client implements automatic retry (max 5 attempts, exponential backoff)
- Validate plugin data via `validate()` method returning `ValidationResult`

### Async Patterns

- Never block in async functions; use `await` or `asyncio.to_thread()`
- Use `asyncio.gather()` for concurrent operations
- Handle cancellation gracefully in loops

### Testing

- Place tests in `tests/` mirroring source structure
- Use pytest fixtures for setup/teardown
- Mark slow tests with `@pytest.mark.slow`
- Mock LLM calls in unit tests

## Architecture

### Modular Three-Act Structure for Long-Form Web Novels

The system implements an "infinite repeating three-act structure" specifically optimized for long-form web novels (300-1000 chapters).

**Core Concept**: Instead of applying one three-act structure to the entire novel (which doesn't work for 1000 chapters), the novel is divided into multiple **story modules** (100-200 chapters each), with each module using a complete three-act structure.

```
Novel Structure (1000 chapters example):
├── Module 1: "新手村篇" (Chapters 1-100)
│   ├── Act 1 (20%): Enter village, establish status quo
│   ├── Act 2 (60%): Train, conflicts, level up
│   └── Act 3 (20%): Leave village, small climax
│
├── Module 2: "宗门篇" (Chapters 101-250)  
│   ├── Act 1 (20%): Enter sect, new rules
│   ├── Act 2 (60%): Competition, breakthroughs
│   └── Act 3 (20%): Sect tournament, promoted
│
├── Module 3: "州城篇" (Chapters 251-450)
│   ├── Act 1 (20%): Enter city, bigger world
│   ├── Act 2 (60%): Faction wars, power up
│   └── Act 3 (20%): State tournament, famous
│
... (continue for 5-10 modules)
│
└── Final Module: "仙界篇" (Last 150 chapters)
    ├── Act 1: Ascend to immortal realm
    ├── Act 2: Final preparations
    └── Act 3: Ultimate boss battle
```

**Key Files**:
- `core/modular_structure.py`: Modular structure planner
- `ModularStructurePlanner`: Plans story modules and three-act breakdown
- `StoryModule`: Represents one story arc with complete three-act structure
- `NovelStructure`: Overall novel structure containing multiple modules

**Benefits**:
1. Each 100-chapter module has its own hook, development, and climax
2. Continuous small climaxes keep readers engaged
3. Level-up progression naturally connects modules
4. World-hopping (新手村→宗门→州城→上界→仙界) creates fresh excitement

**Story Unit Planning** (StoryUnitPlugin):
- **Purpose**: Detailed planning for each story module (100-200 chapters)
- **Content**: Unit-level three-act plot, local characters, factions, events, foreshadowing
- **Timing**: Executed before chapter generation for each module
- **Benefits**: Ensures coherence within unit, prevents plot holes, manages foreshadowing

**New Task Flow with Story Units**:
```
Phase 1: Outline (modular structure overview)
Phase 2: Elements (characters, world, factions)
Phase 3: Story Unit Planning (detailed per-module planning)
        ├── Unit 1 Plan (Chapters 1-100)
        ├── Unit 2 Plan (Chapters 101-200)
        └── ... (one plan per 100 chapters)
Phase 4: Chapter Generation (each chapter depends on its unit plan)
```

### Layered Architecture

```
Frontend (React/TypeScript) -> HTTP/WebSocket -> API Layer (FastAPI)
    |
    v
Application Layer (LoopEngine, TaskPlanner, Evaluator, EngineRegistry)
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
| LoopEngine | `core/loop_engine.py` | Main execution loop |
| TaskPlanner | `core/task_planner.py` | DAG-based task planning |
| Evaluator | `core/evaluator.py` | Quality assessment |
| VectorMemory | `core/vector_memory.py` | Semantic context |
| EngineRegistry | `core/engine_registry.py` | Manage running engines |
| ChapterRewriter | `core/chapter_rewriter.py` | Chapter rewrite |
| MultiLLMClient | `utils/llm_client.py` | LLM routing |

### Key Patterns

**Adding New Task Type**: Add to `TaskType` enum, map in `DEFAULT_TASK_TYPE_MAP` (`utils/llm_client.py`), add prompt template.

**Adding New Plugin**: Extend `NovelElementPlugin` in `plugins/`, implement all abstract methods, register in `PluginManager`.

**LLM Routing**: Task types routed via `DEFAULT_TASK_TYPE_MAP`; Qwen for long context tasks, DeepSeek for logic, Doubao for creativity.

**Session Isolation**: Each session gets its own ChromaDB collection; use `session_id` in all storage operations.

### Philosophy Integration (哲学思想融入)

The system integrates Chinese traditional philosophy (Confucianism, Taoism, Buddhism) into novel generation:

**Genre Support** (专注修仙类型):
- **系统专注修仙小说创作**，内置4种修仙类型：
  - **修仙** (通用修仙)：完整的升级体系、功法系统、资源争夺
  - **都市修仙** (现代修仙)：古今结合、日常修仙化、反差萌点
  - **历史修仙** (朝代修仙)：历史背景扎实、长生视角、朝代修仙差异
  - **传统修仙** (古典修仙)：融合儒道佛哲学思想、道法自然、内圣外王
- 所有类型都强调：升级体系、功法系统、心性修为、哲学思想

**Plugin Integration**:
- **WorldViewPlugin**: World rules based on "天人合一", social structure on "礼"
- **Faction Design**: Different factions represent different philosophies (Taoist, Confucian, Legalist)
- **CharacterPlugin**: Characters have philosophical positions and quote classics
- **GrowthPlugin**: Breakthroughs require philosophical enlightenment, not just power
- **VillainPlugin**: Villains represent twisted/extreme philosophies
- **PowerPlugin**: Techniques based on "阴阳五行", "以柔克刚", "厚德载物"

**Key Concepts**:
- "内圣外王": Inner cultivation matches outer power
- "知行合一": Theory and practice unified
- "德位相配": Power must match moral character
- "悟道": Enlightenment moments quote classics like 《道德经》《论语》

## Important Notes

- EngineRegistry is singleton; use `get_registry()` to access
- Quality threshold defaults to 0.7
- New task types must be added to `DEFAULT_TASK_TYPE_MAP`
- Plugin methods must implement all abstract methods from base class
- Chapter versions: auto-increment on rewrite, track `created_by` ("auto"|"manual"|"rewrite")
