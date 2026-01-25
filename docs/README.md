# Creative AutoGPT 技术文档

> 专注于长篇创意写作的 AI Agent 系统

## 📚 文档目录

### 🚀 快速开始
- [**快速入门指南**](./guides/QUICKSTART.md) - 5分钟了解项目
- [**开发环境搭建**](./guides/DEVELOPMENT.md) - 环境配置和运行

### 🏗️ 架构文档
- [**架构总览**](./architecture/OVERVIEW.md) - 系统整体架构和设计理念
- [**核心模块详解**](./architecture/CORE_MODULES.md) - LoopEngine、TaskPlanner、Memory 等
- [**多 LLM 分工**](./architecture/MULTI_LLM.md) - DeepSeek/Qwen/Doubao 智能分工
- [**插件系统**](./architecture/PLUGIN_SYSTEM.md) - 插件架构和开发指南
- [**长篇小说支持**](./architecture/LONG_NOVEL_SUPPORT.md) - 存储、上下文、一致性保障

### 📖 使用指南
- [**多 LLM 使用指南**](./guides/MULTI_LLM_GUIDE.md) - 如何配置和使用多模型
- [**提示词系统**](./guides/PROMPT_SYSTEM.md) - 提示词模板和风格注入
- [**会话管理**](./guides/SESSION_MANAGEMENT.md) - 创建、恢复、导出会话

### 🔧 API 文档
- [**REST API**](./api/REST_API.md) - HTTP 接口文档
- [**WebSocket API**](./api/WEBSOCKET_API.md) - 实时通信接口

---

## 📊 架构能力评估

### 长篇网络小说支持能力

| 能力维度 | 当前状态 | 目标状态 | 支持规模 |
|---------|---------|---------|---------|
| **存储** | ✅ 支持 | SQLite + Chroma | 无限章节 |
| **上下文** | ✅ 支持 | 智能窗口管理 | 200K tokens 优化 |
| **一致性** | ✅ 支持 | 自动校验 | 实时冲突检测 |
| **多模型** | ✅ 支持 | 智能分工 | 3大模型协作 |
| **断点续写** | 🔄 进行中 | 检查点系统 | 随时恢复 |
| **插件系统** | 🔄 设计中 | 可插拔架构 | 无限扩展 |

### 三大模型分工

```
┌─────────────────────────────────────────────────────────────────┐
│                    多 LLM 智能分工架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🧠 Qwen (Aliyun)          🔍 DeepSeek           ✨ Doubao      │
│  ┌───────────────┐       ┌───────────────┐     ┌───────────────┐│
│  │ 总览记忆专家   │       │ 逻辑结构专家  │     │ 创意文笔专家  ││
│  ├───────────────┤       ├───────────────┤     ├───────────────┤│
│  │ • 大纲        │       │ • 事件       │     │ • 章节内容    ││
│  │ • 人物设计    │       │ • 场景物品    │     │ • 润色修订    ││
│  │ • 风格元素    │       │ • 评估       │     │ • 对话生成    ││
│  └───────────────┘       └───────────────┘     └───────────────┘│
│  长上下文、全局一致      逻辑推理、性价比高      文笔优美、创意强 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ 项目结构

```
creative_autogpt/
├── docs/                    # 📚 技术文档（你在这里）
│   ├── architecture/        # 架构文档
│   ├── guides/              # 使用指南
│   └── api/                 # API 文档
│
├── src/creative_autogpt/    # 🔧 源代码
│   ├── core/                # 核心模块
│   │   ├── loop_engine.py   # 执行引擎
│   │   ├── task_planner.py  # 任务规划
│   │   ├── evaluator.py     # 质量评估
│   │   └── vector_memory.py # 向量记忆
│   ├── modes/               # 写作模式
│   ├── utils/               # 工具类（LLM客户端等）
│   └── api/                 # API 服务
│
├── prompts/                 # 📝 提示词模板
├── frontend/                # 🖥️ 前端界面
├── examples/                # 📖 示例代码
└── ARCHITECTURE.md          # 📄 完整架构文档（详细版）
```

---

## 🔗 相关资源

- [完整架构文档](../ARCHITECTURE.md) - 3000+ 行的详细架构说明
- [LLM 分工总结](../LLM_DIVISION_SUMMARY.md) - 多模型分工方案
- [智能路由验证](../SMART_ROUTING_VALIDATION.md) - 路由策略验证

---

*文档版本: 1.0*  
*最后更新: 2026-01-23*
