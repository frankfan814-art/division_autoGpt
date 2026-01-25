# 插件系统架构

> 可扩展的小说元素管理系统

## 1. 设计理念

将小说创作的各个元素抽象为**独立插件**，实现：
- **高内聚低耦合**：每个插件专注于一个领域
- **可插拔**：根据小说类型选择性加载
- **可扩展**：轻松添加新的元素类型
- **可复用**：跨项目共享插件配置

## 2. 插件系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Plugin Manager (插件管理器)                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  register() / unregister() / get() / list_enabled()         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │
          │ 管理
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Element Plugins (元素插件)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  人物架构    │  │  世界观架构  │  │  事件架构    │              │
│  │  Character   │  │  WorldView   │  │  Event       │              │
│  │  Plugin      │  │  Plugin      │  │  Plugin      │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  时间线架构  │  │  节奏架构    │  │  伏笔架构    │              │
│  │  Timeline    │  │  Rhythm      │  │  Foreshadow  │              │
│  │  Plugin      │  │  Plugin      │  │  Plugin      │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  冲突架构    │  │  对话架构    │  │  场景架构    │              │
│  │  Conflict    │  │  Dialogue    │  │  Scene       │              │
│  │  Plugin      │  │  Plugin      │  │  Plugin      │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 3. 插件基类

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class PluginPhase(Enum):
    """插件介入阶段"""
    PLANNING = "planning"           # 规划阶段
    GENERATION = "generation"       # 生成阶段
    EVALUATION = "evaluation"       # 评估阶段
    POST_PROCESS = "post_process"   # 后处理阶段

@dataclass
class PluginConfig:
    """插件配置"""
    enabled: bool = True
    priority: int = 50              # 执行优先级 (0-100)
    phases: List[PluginPhase] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)

class NovelElementPlugin(ABC):
    """小说元素插件基类"""
    
    # === 元信息 ===
    name: str                       # 插件名称
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = []    # 依赖的其他插件
    
    # === 生命周期钩子 ===
    
    @abstractmethod
    async def on_init(self, context: "WritingContext") -> None:
        """初始化时调用"""
        pass
    
    async def on_before_task(self, task: "Task", context: "WritingContext") -> "Task":
        """任务执行前调用，可修改任务"""
        return task
    
    async def on_after_task(self, task: "Task", result: str, context: "WritingContext") -> str:
        """任务执行后调用，可修改结果"""
        return result
    
    async def on_finalize(self, context: "WritingContext") -> None:
        """完成时调用"""
        pass
    
    # === 核心能力 ===
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """返回该元素的数据结构定义"""
        pass
    
    @abstractmethod
    def get_prompts(self) -> Dict[str, str]:
        """返回该元素相关的提示词模板"""
        pass
    
    @abstractmethod
    def get_tasks(self) -> List["TaskDefinition"]:
        """返回该元素需要的任务定义"""
        pass
    
    @abstractmethod
    async def validate(self, data: Any, context: "WritingContext") -> "ValidationResult":
        """验证该元素数据的一致性"""
        pass
    
    @abstractmethod
    async def enrich_context(self, task: "Task", context: Dict[str, Any]) -> Dict[str, Any]:
        """为任务丰富上下文信息"""
        return context
```

## 4. 核心插件说明

### 4.1 人物插件 (CharacterPlugin)

**职责**：管理小说中的所有人物元素

```python
class CharacterPlugin(NovelElementPlugin):
    name = "character"
    description = "管理小说人物的完整生命周期"
```

**数据结构**：
```
Character
├── id: str                 # 唯一标识
├── name: str               # 姓名
├── aliases: List[str]      # 别名/外号
├── role: Enum              # protagonist/antagonist/supporting/minor
├── profile
│   ├── age: int
│   ├── gender: str
│   ├── appearance: str     # 外貌描述
│   ├── personality: List[str]
│   ├── background: str
│   └── abilities: List[str]
├── psychology
│   ├── motivation: str     # 核心动机
│   ├── fear: str
│   ├── desire: str
│   └── flaw: str           # 性格缺陷
├── arc
│   ├── start_state: str
│   ├── end_state: str
│   └── turning_points: List
└── relationships: List[Relationship]
```

**生成的任务**：
- 人物设计
- 人物关系
- 人物弧光
- 人物语言风格

---

### 4.2 世界观插件 (WorldViewPlugin)

**职责**：管理小说世界的所有设定

```python
class WorldViewPlugin(NovelElementPlugin):
    name = "worldview"
    description = "管理小说世界观的完整体系"
```

**数据结构**：
```
World
├── name: str               # 世界名称
├── type: Enum              # fantasy/scifi/modern/historical
├── era: str                # 时代背景
├── tone: str               # 世界基调
├── physics
│   ├── magic_system: Optional[MagicSystem]
│   ├── technology_level: str
│   └── special_rules: List[str]
├── society
│   ├── political_system: str
│   ├── economic_system: str
│   └── cultures: List[Culture]
├── geography
│   ├── locations: List[Location]
│   └── map_description: str
├── history
│   ├── timeline: List[HistoricalEvent]
│   └── legends: List[Legend]
└── factions: List[Faction]
```

---

### 4.3 伏笔插件 (ForeshadowPlugin)

**职责**：管理小说中的伏笔埋设与回收

```python
class ForeshadowPlugin(NovelElementPlugin):
    name = "foreshadow"
    description = "管理小说伏笔的埋设与回收"
```

**数据结构**：
```
Foreshadow
├── id: str
├── name: str
├── type: Enum              # plot/character/worldview/dialogue/item
├── plant                   # 埋设信息
│   ├── chapter: int
│   ├── scene: Optional[int]
│   ├── method: str         # 埋设方式
│   ├── content: str
│   └── subtlety: Enum      # obvious/subtle/hidden
├── payoffs: List           # 回收信息（可多次）
│   ├── chapter: int
│   ├── method: str
│   └── impact: str
├── status: Enum            # planted/partially_paid/fully_paid/abandoned
└── importance: Enum        # major/moderate/minor
```

**特殊钩子**：
```python
async def on_before_task(self, task, context):
    if task.type in ["章节", "场景"]:
        chapter = task.metadata.get("chapter_index")
        # 注入需要埋设的伏笔
        task.metadata["foreshadows_to_plant"] = self._get_foreshadows(chapter, "plant")
        # 注入需要回收的伏笔
        task.metadata["foreshadows_to_payoff"] = self._get_foreshadows(chapter, "payoff")
    return task
```

---

### 4.4 时间线插件 (TimelinePlugin)

**职责**：管理小说的时间结构

**功能**：
- 故事时间线（故事内时间）
- 叙事时间线（叙述顺序）
- 时间跳跃与闪回
- 时间一致性检查

---

### 4.5 事件插件 (EventPlugin)

**职责**：管理小说中的情节事件

**功能**：
- 主线/支线事件
- 事件因果链
- 冲突管理
- 转折点设计

---

## 5. 插件管理器

```python
class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self._plugins: Dict[str, NovelElementPlugin] = {}
        self._enabled: Set[str] = set()
        self._load_order: List[str] = []
    
    def register(self, plugin: NovelElementPlugin) -> None:
        """注册插件"""
        # 检查依赖
        for dep in plugin.dependencies:
            if dep not in self._plugins:
                raise PluginDependencyError(f"Plugin {plugin.name} requires {dep}")
        
        self._plugins[plugin.name] = plugin
        self._recalculate_load_order()
    
    def enable(self, name: str, config: Optional[PluginConfig] = None) -> None:
        """启用插件"""
        if name in self._plugins:
            if config:
                self._plugins[name].config = config
            self._enabled.add(name)
    
    def disable(self, name: str) -> None:
        """禁用插件"""
        self._enabled.discard(name)
    
    async def run_hook(self, hook_name: str, *args, **kwargs) -> Any:
        """执行所有启用插件的指定钩子"""
        results = []
        for name in self._load_order:
            if name in self._enabled:
                plugin = self._plugins[name]
                hook = getattr(plugin, hook_name, None)
                if hook:
                    result = await hook(*args, **kwargs)
                    results.append(result)
        return results
```

## 6. 与执行引擎集成

```python
class LoopEngine:
    def __init__(self, plugin_manager: PluginManager, ...):
        self.plugin_manager = plugin_manager
    
    async def run(self, goal: str, ...) -> Dict:
        context = WritingContext(goal=goal)
        
        # 初始化钩子
        await self.plugin_manager.run_hook("on_init", context)
        
        # 执行任务
        for task in tasks:
            # 任务前钩子
            task = await self.plugin_manager.run_hook("on_before_task", task, context)
            
            # 执行任务
            result = await self._execute_task(task)
            
            # 任务后钩子
            result = await self.plugin_manager.run_hook("on_after_task", task, result, context)
            
            # 验证
            for plugin in self.plugin_manager.list_enabled():
                validation = await plugin.validate(context.get_results(), context)
                if not validation.valid:
                    # 处理验证失败
                    ...
        
        # 完成钩子
        await self.plugin_manager.run_hook("on_finalize", context)
        
        return context.get_results()
```

## 7. 插件目录结构

```
creative_autogpt/
├── plugins/
│   ├── __init__.py
│   ├── base.py                 # 插件基类
│   ├── manager.py              # 插件管理器
│   │
│   ├── core/                   # 核心插件（内置）
│   │   ├── character.py        # 人物架构
│   │   ├── worldview.py        # 世界观架构
│   │   ├── event.py            # 事件架构
│   │   ├── timeline.py         # 时间线架构
│   │   ├── foreshadow.py       # 伏笔架构
│   │   ├── rhythm.py           # 节奏架构
│   │   ├── dialogue.py         # 对话架构
│   │   └── scene.py            # 场景架构
│   │
│   ├── genre/                  # 类型插件
│   │   ├── suspense.py         # 悬疑专用
│   │   ├── romance.py          # 言情专用
│   │   └── xianxia.py          # 仙侠专用
│   │
│   └── community/              # 社区插件
│       └── README.md
```

## 8. 开发新插件

### 8.1 步骤

1. 继承 `NovelElementPlugin`
2. 实现所有抽象方法
3. 注册到 `PluginManager`

### 8.2 示例

```python
class MyCustomPlugin(NovelElementPlugin):
    name = "my_plugin"
    version = "1.0.0"
    description = "我的自定义插件"
    dependencies = ["character"]  # 依赖人物插件
    
    async def on_init(self, context):
        print(f"Plugin {self.name} initialized")
    
    def get_schema(self) -> Dict:
        return {
            "MyElement": {
                "id": "str",
                "name": "str",
                "data": "Any"
            }
        }
    
    def get_prompts(self) -> Dict:
        return {
            "my_prompt": "这是我的提示词模板: {variable}"
        }
    
    def get_tasks(self) -> List:
        return [
            TaskDefinition(
                type="我的任务",
                description="执行自定义任务",
                depends_on=["人物设计"]
            )
        ]
    
    async def validate(self, data, context):
        # 验证逻辑
        return ValidationResult(valid=True)
    
    async def enrich_context(self, task, context):
        context["my_data"] = "enriched"
        return context

# 注册使用
plugin_manager.register(MyCustomPlugin())
plugin_manager.enable("my_plugin")
```

---

*插件系统是支撑长篇小说扩展性的关键架构，按需加载，灵活组合。*
