# 快速入门指南

> 5 分钟了解 Creative AutoGPT 项目

## 什么是 Creative AutoGPT？

Creative AutoGPT 是一个专注于**长篇创意写作**的 AI Agent 系统，借鉴 AutoGPT 的核心理念，针对小说创作场景进行深度优化。

### 核心特性

- 🎯 **专注写作**：小说、剧本、剧本杀等创意写作
- 🧠 **多模型协作**：Qwen + DeepSeek + Doubao 智能分工
- 📚 **长篇支持**：支持 10-500 万字网络小说
- 🔌 **可扩展**：插件化的元素管理系统
- ✅ **一致性保障**：自动检测和修复逻辑冲突

## 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+ (前端)

### 2. 安装依赖

```bash
cd creative_autogpt

# 后端
pip install -r requirements.txt

# 前端
cd frontend && npm install
```

### 3. 配置 API Key

```bash
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
ALIYUN_API_KEY=sk-xxx      # Qwen
DEEPSEEK_API_KEY=sk-xxx    # DeepSeek  
ARK_API_KEY=xxx            # Doubao
```

### 4. 启动服务

```bash
# 后端
python app.py

# 前端（新终端）
cd frontend && npm run dev
```

### 5. 访问

打开浏览器访问 http://localhost:3000

## 系统架构一览

```
┌─────────────────────────────────────────────────────────────┐
│                     Creative AutoGPT                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│  │ 前端    │───▶│ API     │───▶│ 引擎    │                 │
│  │ React   │    │ FastAPI │    │LoopEngine│                │
│  └─────────┘    └─────────┘    └────┬────┘                 │
│                                      │                       │
│         ┌───────────────────────────┬┴──────────────┐       │
│         │                           │               │       │
│         ▼                           ▼               ▼       │
│  ┌─────────────┐          ┌─────────────┐   ┌───────────┐  │
│  │ TaskPlanner │          │ VectorMemory│   │ Evaluator │  │
│  │ 任务规划     │          │ 向量记忆    │   │ 质量评估  │  │
│  └─────────────┘          └─────────────┘   └───────────┘  │
│         │                           │               │       │
│         └───────────────────────────┴───────────────┘       │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MultiLLMClient (多模型)                 │   │
│  │  ┌───────┐     ┌──────────┐     ┌────────┐         │   │
│  │  │ Qwen  │     │ DeepSeek │     │ Doubao │         │   │
│  │  │规划    │     │逻辑      │     │创作     │         │   │
│  │  └───────┘     └──────────┘     └────────┘         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 核心概念

### 1. 任务流水线

小说创作按照固定流程执行：

```
风格 → 主题 → 大纲 → 人物 → 事件 → 一致性检查 → 章节循环
```

### 2. 多模型分工

| 模型 | 角色 | 负责任务 |
|------|------|----------|
| 🧠 Qwen | 总览记忆 | 大纲、人物设计、风格 |
| 🔍 DeepSeek | 逻辑结构 | 事件、评估、一致性检查 |
| ✨ Doubao | 创意文笔 | 章节内容、润色修订 |

### 3. 质量评估

每个生成内容都会评估：
- 连贯性 (coherence)
- 创意性 (creativity)
- 写作质量 (quality)
- 一致性 (consistency)
- 目标对齐 (goal_alignment)

不通过会自动重写。

## 使用示例

### 通过 API 创建小说

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的悬疑小说",
    "config": {
      "theme": "悬疑推理",
      "style": "紧张刺激",
      "chapterCount": 10,
      "provider": "multi"
    }
  }'
```

### 通过 Python 脚本

```python
from creative_autogpt.utils import MultiLLMClient
from creative_autogpt.core import LoopEngine

# 创建多模型客户端
llm_client = MultiLLMClient(providers=[...])

# 创建执行引擎
engine = LoopEngine(llm_client=llm_client, ...)

# 执行创作
result = await engine.run("写一部10章的悬疑小说")
```

## 下一步

- 📖 [架构总览](./architecture/OVERVIEW.md) - 深入了解系统设计
- 🔧 [核心模块](./architecture/CORE_MODULES.md) - 了解各模块功能
- 🤖 [多 LLM 分工](./architecture/MULTI_LLM.md) - 了解模型分工策略
- 🔌 [插件系统](./architecture/PLUGIN_SYSTEM.md) - 了解扩展机制
- 📚 [长篇支持](./architecture/LONG_NOVEL_SUPPORT.md) - 了解长篇小说方案

## 常见问题

### Q: 支持多大的小说？
A: 理论上无限制。通过智能上下文管理和持久化存储，可支持 500 万字以上的超长篇。

### Q: 如何选择使用单模型还是多模型？
A: 推荐使用 `multi` 模式（智能分工），可以获得最佳的质量和性价比。

### Q: 如何添加新的 LLM 提供商？
A: 继承 `LLMClientBase` 并实现 `generate` 方法即可。

---

*有问题？查看完整文档或提交 Issue。*
