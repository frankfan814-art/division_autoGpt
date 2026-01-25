# Creative AutoGPT - Codemap Index

**Last Updated:** 2025-01-25
**Documentation Version:** 1.0

## Overview

This directory contains architectural documentation (codemaps) for the Creative AutoGPT project - an AI-powered creative writing system for long-form novels.

## What are Codemaps?

Codemaps are concise, token-lean architecture diagrams that capture the essential structure of a codebase without implementation details. They serve as:

- **Navigation Guides** - Quick reference for understanding code organization
- **Onboarding Tools** - Fast path for new developers
- **Architecture Documentation** - High-level system design overview
- **Maintenance Aids** - Track architectural evolution over time

## Documentation Files

### [architecture.md](architecture.md)
**Overall System Architecture**

- Complete system architecture diagram
- Core component descriptions (LoopEngine, TaskPlanner, Evaluator, etc.)
- Multi-LLM routing strategy
- Plugin system overview
- Data flow between layers
- External dependencies
- Key design patterns

**Best for:** Understanding the big picture, system integration points

---

### [backend.md](backend.md)
**Backend API & Core Logic**

- FastAPI application structure
- API routes (sessions, websocket, prompts)
- Core execution engine details
- Plugin system implementation
- Multi-LLM client architecture
- Storage layer (SQLAlchemy, ChromaDB)
- Dependency injection
- Configuration management

**Best for:** Backend development, API integration, server-side logic

---

### [frontend.md](frontend.md)
**Frontend Client Architecture**

- React/TypeScript component structure
- Zustand state management stores
- WebSocket integration
- UI component library
- Type definitions
- Performance optimizations
- Testing strategy

**Best for:** Frontend development, UI implementation, client-side state

---

### [data.md](data.md)
**Data Models & Schemas**

- SQLAlchemy models (database)
- Pydantic schemas (API validation)
- TypeScript interfaces (frontend)
- Data validation rules
- Data flow between layers

**Best for:** Understanding data structures, API contracts, type safety

---

## Quick Navigation

### By Component Type

**Core Execution:**
- [LoopEngine](architecture.md#core-components) - AutoGPT agent loop
- [TaskPlanner](architecture.md#core-components) - DAG-based task planning
- [EvaluationEngine](architecture.md#core-components) - Quality assessment
- [VectorMemoryManager](architecture.md#core-components) - Context retrieval

**Plugin System:**
- [Plugin Base](backend.md#plugin-system) - Abstract plugin interface
- [Plugin Manager](backend.md#plugin-system) - Plugin lifecycle
- [Implemented Plugins](backend.md#implemented-plugins) - Character, WorldView, etc.

**API Layer:**
- [Sessions API](backend.md#sessions-api) - Session CRUD endpoints
- [WebSocket API](backend.md#websocket-api) - Real-time execution
- [Prompts API](backend.md#prompts-api) - Prompt templates

**Storage:**
- [SessionStorage](backend.md#storage-layer) - SQLAlchemy models
- [VectorStore](backend.md#storage-layer) - ChromaDB integration

**Frontend:**
- [State Management](frontend.md#state-management-zustand-stores) - Zustand stores
- [Component Structure](frontend.md#component-architecture) - React components
- [WebSocket Client](frontend.md#websocket-integration) - Real-time updates

### By Task

**I want to...**

- **Understand the system architecture** → Start with [architecture.md](architecture.md)
- **Add a new API endpoint** → Read [backend.md](backend.md) → API Routes section
- **Create a new plugin** → Read [backend.md](backend.md) → Plugin System section
- **Add a new UI component** → Read [frontend.md](frontend.md) → Component Architecture
- **Understand data models** → Read [data.md](data.md)
- **Integrate with the WebSocket** → Read [backend.md](backend.md) → WebSocket API
- **Debug the execution loop** → Read [architecture.md](architecture.md) → LoopEngine section
- **Modify state management** → Read [frontend.md](frontend.md) → Zustand Stores

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                       │
│              React + TypeScript + Zustand               │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                     API Layer                           │
│              FastAPI Routes + WebSockets                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  Application Layer                      │
│      LoopEngine → TaskPlanner → Evaluator → Memory      │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  Plugin System                          │
│  Character, WorldView, Event, Foreshadow, etc.         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│               Infrastructure Layer                      │
│   MultiLLMClient | VectorStore | SessionStorage         │
└─────────────────────────────────────────────────────────┘
```

## Key Concepts

### AutoGPT Agent Loop
The system implements an AutoGPT-inspired execution pattern:
1. **Plan** - Generate task DAG from goals
2. **Execute** - Run tasks in dependency order
3. **Evaluate** - Assess quality of results
4. **Rewrite** - Retry if below threshold
5. **Memory** - Store results for context

### Multi-LLM Routing
Tasks are intelligently routed to optimal LLMs:
- **Qwen (Aliyun)** - Long context, global planning
- **DeepSeek** - Logic, cost-effective evaluation
- **Doubao (Ark)** - Creative writing, dialogue

### Plugin Architecture
Extensible plugin system for novel elements:
- Base class: `NovelElementPlugin`
- Lifecycle hooks: `on_init`, `on_before_task`, `on_after_task`, `on_finalize`
- 7 implemented plugins for different story elements

### Vector Memory
ChromaDB-based semantic context retrieval:
- Memory types: CHARACTER, PLOT, WORLDVIEW, FORESHADOW, etc.
- Retrieval strategies: Recent, semantic search, chapter-scoped
- Ensures long-form consistency across chapters

## Development Workflow

### Backend Development
1. Read [backend.md](backend.md) for API structure
2. Check [data.md](data.md) for data models
3. Reference [architecture.md](architecture.md) for system integration

### Frontend Development
1. Read [frontend.md](frontend.md) for component structure
2. Check [data.md](data.md) for TypeScript interfaces
3. Reference [backend.md](backend.md) for WebSocket events

### Plugin Development
1. Read [backend.md](backend.md) → Plugin System section
2. Extend `NovelElementPlugin` base class
3. Implement required abstract methods
4. Register via `PluginManager`

## Maintenance

### freshness Timestamps
Each codemap includes a "Last Updated" timestamp. Check dates to ensure you're reading current documentation.

### Version Control
Codemaps are tracked in git. Commit history shows architectural evolution.

### Update Process
When making significant changes:
1. Update relevant codemap sections
2. Update timestamp
3. Commit with descriptive message
4. Regenerate from source if structure changes significantly

## Contributing

When adding new features:

1. **Backend:** Update [backend.md](backend.md) with new routes/components
2. **Frontend:** Update [frontend.md](frontend.md) with new components/stores
3. **Data Models:** Update [data.md](data.md) with new schemas/interfaces
4. **Architecture:** Update [architecture.md](architecture.md) if system design changes

## Additional Resources

- **Project README:** [../README.md](../README.md)
- **Project Instructions:** [../CLAUDE.md](../CLAUDE.md)
- **Diff Report:** [../.reports/codemap-diff.txt](../.reports/codemap-diff.txt)

## Metrics

- **Total Documentation:** 1,678 lines
- **Modules Covered:** 38 backend files, 30+ frontend files
- **Components Documented:** 7 core modules, 7 plugins, 3 API routes
- **Diagrams:** ASCII architecture diagrams
- **Last Full Analysis:** 2025-01-25

---

**Documentation Specialist:** Claude Code
**Analysis Method:** Static code analysis + import/export mapping
**Update Frequency:** Weekly or after major features
