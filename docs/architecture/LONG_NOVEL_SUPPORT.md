# 长篇网络小说支持架构

> 支持 10-500 万字长篇小说的存储、上下文和一致性保障方案

## 1. 挑战分析

### 1.1 规模与挑战

| 规模 | 字数 | 章节数 | 主要挑战 |
|-----|------|--------|---------|
| **中篇** | 10-30万字 | 50-150章 | 人物一致性、伏笔回收 |
| **长篇** | 50-150万字 | 200-600章 | 设定遗忘、时间线混乱、人物关系复杂 |
| **超长篇** | 150-500万字 | 600-2000章 | 大量角色管理、多线叙事、读者记忆负担 |

### 1.2 六大核心痛点

```
┌─────────────────────────────────────────────────────────────────────┐
│                     中长篇小说的六大挑战                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. LLM上下文窗口限制                                               │
│     └─ 即使200K tokens也无法装下整本小说                            │
│     └─ 需要智能的上下文检索和压缩                                    │
│                                                                      │
│  2. 设定一致性                                                       │
│     └─ 第500章可能忘记第10章的设定                                  │
│     └─ 人物性格、能力、关系可能前后矛盾                              │
│                                                                      │
│  3. 伏笔管理                                                         │
│     └─ 跨越几百章的伏笔容易遗忘                                      │
│     └─ 需要精确追踪埋设和回收                                        │
│                                                                      │
│  4. 时间线复杂度                                                     │
│     └─ 多条时间线交织                                                │
│     └─ 角色年龄、事件先后容易出错                                    │
│                                                                      │
│  5. 人物关系网络                                                     │
│     └─ 几十上百个角色                                                │
│     └─ 关系随剧情动态变化                                            │
│                                                                      │
│  6. 内存无法承载                                                     │
│     └─ 当前VectorMemoryManager基于内存                              │
│     └─ 无法持久化，重启丢失                                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. 存储架构设计

### 2.1 分层存储架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        存储架构分层设计                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Application Layer                         │   │
│  │              (LoopEngine / PluginManager)                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  Storage Abstraction Layer                   │   │
│  │                    (NovelStorageManager)                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │   │
│  │  │ 元数据   │  │ 结构化   │  │ 向量     │  │ 全文     │    │   │
│  │  │ 存储     │  │ 数据存储 │  │ 存储     │  │ 存储     │    │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │   │
│  └───────┼─────────────┼─────────────┼─────────────┼───────────┘   │
│          │             │             │             │                 │
│          ▼             ▼             ▼             ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Physical Storage Layer                    │   │
│  │                                                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │   │
│  │  │ SQLite/  │  │PostgreSQL│  │ Chroma/  │  │ File/    │    │   │
│  │  │ JSON     │  │ /MySQL   │  │ Qdrant   │  │ S3       │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │   │
│  │   项目配置      人物/设定      语义检索      章节正文        │   │
│  │   会话状态      关系/事件      上下文匹配    完整小说        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据库选型

| 数据类型 | 开发环境 | 生产环境 | 说明 |
|---------|---------|---------|------|
| 元数据 | SQLite | PostgreSQL | 项目配置、会话状态 |
| 结构化数据 | SQLite | PostgreSQL | 人物、设定、关系 |
| 向量索引 | Chroma | Qdrant | 语义检索 |
| 全文内容 | 文件系统 | MinIO/S3 | 章节正文 |

### 2.3 向量数据库设计

**为什么需要向量数据库？**

```python
# 问题场景：第500章需要引用第50章的一个细节

# ❌ 传统方法：全文搜索
result = search("主角的剑")  # 返回几百个匹配，无法精确定位

# ✅ 向量检索：语义搜索
result = vector_search(
    query="主角第一次获得那把能斩断因果的神剑是什么情况",
    filters={"type": "item", "owner": "protagonist"},
    top_k=3
)
# 精确返回第50章神剑出场的相关内容
```

**向量存储数据类型**：

```python
class NovelElementType(Enum):
    # 结构元素
    CHAPTER = "chapter"
    SCENE = "scene"
    PARAGRAPH = "paragraph"
    
    # 核心元素
    CHARACTER = "character"
    CHARACTER_STATE = "character_state"
    RELATIONSHIP = "relationship"
    
    # 世界观元素
    WORLDVIEW = "worldview"
    LOCATION = "location"
    ITEM = "item"
    FACTION = "faction"
    
    # 情节元素
    EVENT = "event"
    PLOT_POINT = "plot_point"
    CONFLICT = "conflict"
    FORESHADOW = "foreshadow"
```

## 3. 智能上下文管理

### 3.1 分层上下文策略

```
┌─────────────────────────────────────────────────────────────────────┐
│                      分层上下文策略                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Layer 1: 固定上下文 (Always Present)                         │   │
│  │ ~5K tokens                                                   │   │
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │   │
│  │ │ 风格    │ │ 主题    │ │ 核心    │ │ 主角    │            │   │
│  │ │ 定义    │ │ 设定    │ │ 设定    │ │ 简介    │            │   │
│  │ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Layer 2: 章节上下文 (Chapter-Specific)                       │   │
│  │ ~20K tokens                                                  │   │
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │   │
│  │ │ 章节    │ │ 涉及    │ │ 场景    │ │ 伏笔    │            │   │
│  │ │ 大纲    │ │ 人物    │ │ 设定    │ │ 任务    │            │   │
│  │ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Layer 3: 动态上下文 (Task-Specific)                          │   │
│  │ ~30K tokens                                                  │   │
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │   │
│  │ │ 语义    │ │ 前文    │ │ 相关    │ │ 回忆    │            │   │
│  │ │ 检索    │ │ 摘要    │ │ 伏笔    │ │ 片段    │            │   │
│  │ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  总预算: ~55K tokens (留出生成空间)                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 上下文窗口管理器

```python
class ContextWindowManager:
    """上下文窗口管理器"""
    
    def __init__(
        self,
        max_tokens: int = 128000,           # 模型最大上下文
        reserved_for_output: int = 8000,     # 预留给输出
        fixed_context_budget: int = 5000,    # 固定上下文预算
        chapter_context_budget: int = 20000, # 章节上下文预算
        dynamic_context_budget: int = 30000, # 动态上下文预算
    ):
        self.budgets = {...}
    
    async def build_context(
        self,
        task: Task,
        storage: NovelStorageManager,
    ) -> str:
        """为任务构建最优上下文"""
        
        context_parts = []
        
        # Layer 1: 固定上下文
        fixed = await self._get_fixed_context(storage)
        context_parts.append(("fixed", fixed, self.budgets["fixed"]))
        
        # Layer 2: 章节上下文
        chapter = await self._get_chapter_context(task, storage)
        context_parts.append(("chapter", chapter, self.budgets["chapter"]))
        
        # Layer 3: 动态上下文
        dynamic = await self._get_dynamic_context(task, storage)
        context_parts.append(("dynamic", dynamic, self.budgets["dynamic"]))
        
        # 组装并控制总长度
        return self._assemble_context(context_parts)
```

### 3.3 智能压缩策略

```python
class CompressionStrategy:
    """上下文压缩策略"""
    
    async def compress_chapter(self, chapter_content: str, target_tokens: int) -> str:
        """压缩章节内容到目标长度"""
        
        if count_tokens(chapter_content) <= target_tokens:
            return chapter_content
        
        # 策略1: 提取关键段落
        key_paragraphs = self._extract_key_paragraphs(chapter_content)
        
        # 策略2: 生成摘要
        summary = await self._generate_summary(chapter_content, target_tokens // 2)
        
        # 策略3: 保留对话
        dialogues = self._extract_dialogues(chapter_content)
        
        return self._compose(summary, key_paragraphs, dialogues, target_tokens)
```

## 4. 一致性保障

### 4.1 自动校验系统

```
┌─────────────────────────────────────────────────────────────────────┐
│                      一致性校验系统                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    实时校验层                                │   │
│  │  在任务执行后立即检查                                        │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │   │
│  │  │ 人物    │ │ 设定    │ │ 时间线  │ │ 称谓    │           │   │
│  │  │ 行为    │ │ 一致    │ │ 冲突    │ │ 一致    │           │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    定期校验层                                │   │
│  │  每N章执行一次全局检查                                       │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │   │
│  │  │ 伏笔    │ │ 人物    │ │ 关系    │ │ 剧情    │           │   │
│  │  │ 追踪    │ │ 弧光    │ │ 演变    │ │ 连贯    │           │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    冲突处理层                                │   │
│  │  发现冲突后自动生成修复任务                                   │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  冲突检测 → 影响分析 → 修复任务生成 → 执行修复        │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 一致性管理器

```python
class ConsistencyManager:
    """一致性管理器"""
    
    async def check_after_task(self, task: Task, result: str) -> List[Conflict]:
        """任务后即时检查"""
        conflicts = []
        
        # 检查人物行为一致性
        char_conflicts = await self._check_character_behavior(task, result)
        conflicts.extend(char_conflicts)
        
        # 检查设定一致性
        setting_conflicts = await self._check_setting_consistency(task, result)
        conflicts.extend(setting_conflicts)
        
        # 检查时间线
        timeline_conflicts = await self._check_timeline(task, result)
        conflicts.extend(timeline_conflicts)
        
        return conflicts
    
    async def generate_fix_tasks(self, conflicts: List[Conflict]) -> List[Task]:
        """为冲突生成修复任务"""
        fix_tasks = []
        for conflict in conflicts:
            if conflict.severity >= ConflictSeverity.HIGH:
                fix_task = Task(
                    type="修订",
                    description=f"修复一致性问题: {conflict.description}",
                    metadata={"conflict": conflict}
                )
                fix_tasks.append(fix_task)
        return fix_tasks
```

## 5. 断点续写与版本管理

### 5.1 检查点系统

```python
class CheckpointManager:
    """检查点管理器"""
    
    async def create_checkpoint(self, session_id: str) -> str:
        """创建检查点"""
        checkpoint = {
            "session_id": session_id,
            "timestamp": datetime.now(),
            "task_queue": self._serialize_tasks(),
            "completed_tasks": self._get_completed(),
            "memory_snapshot": await self.memory.snapshot(),
            "novel_state": self._get_novel_state(),
        }
        return await self.storage.save_checkpoint(checkpoint)
    
    async def restore_checkpoint(self, checkpoint_id: str) -> Session:
        """恢复检查点"""
        checkpoint = await self.storage.load_checkpoint(checkpoint_id)
        session = Session.from_checkpoint(checkpoint)
        return session
```

### 5.2 章节版本历史

```python
class ChapterVersionManager:
    """章节版本管理"""
    
    async def save_version(self, chapter_id: str, content: str, metadata: Dict) -> str:
        """保存新版本"""
        version = ChapterVersion(
            chapter_id=chapter_id,
            version_number=self._get_next_version(chapter_id),
            content=content,
            metadata=metadata,
            created_at=datetime.now(),
        )
        return await self.storage.save_version(version)
    
    async def rollback(self, chapter_id: str, version_number: int) -> str:
        """回滚到指定版本"""
        version = await self.storage.get_version(chapter_id, version_number)
        await self.storage.set_current(chapter_id, version)
        return version.content
    
    async def diff(self, chapter_id: str, v1: int, v2: int) -> str:
        """版本差异对比"""
        version1 = await self.storage.get_version(chapter_id, v1)
        version2 = await self.storage.get_version(chapter_id, v2)
        return self._compute_diff(version1.content, version2.content)
```

## 6. 能力总结

| 能力 | 当前状态 | 增强后 | 支持规模 |
|-----|---------|-------|---------|
| **存储** | 内存 | 关系DB + 向量DB | 无限 |
| **上下文** | 全量加载 | 智能窗口 | 200K tokens内优化 |
| **一致性** | 依赖记忆 | 结构化校验 | 自动检测冲突 |
| **伏笔** | 简单追踪 | 完整生命周期 | 支持几百个伏笔 |
| **人物** | 列表存储 | 关系图谱 | 支持上百角色 |
| **断点续写** | 不支持 | 检查点系统 | 随时恢复 |
| **版本管理** | 不支持 | 章节版本历史 | 可回滚 |

## 7. 实施优先级

1. **P0 - 持久化存储**：SQLite + Chroma 基础实现
2. **P1 - 智能上下文**：分层上下文管理器
3. **P2 - 一致性检查**：实时校验 + 修复任务
4. **P3 - 断点续写**：检查点系统
5. **P4 - 版本管理**：章节历史

---

*长篇小说支持是系统的核心竞争力，需要存储、上下文、一致性三大能力协同工作。*
