# 多 LLM 使用指南

> 如何配置和使用 Qwen、DeepSeek、Doubao 三大模型协作

## 1. 设计理念

Creative AutoGPT 采用**多 LLM 智能分工**策略，让不同模型发挥各自优势：

```
🧠 Qwen (Aliyun)     → 总览规划、长期记忆
🔍 DeepSeek          → 逻辑推理、质量评估
✨ Doubao (火山引擎) → 创意文笔、内容生成
```

---

## 2. 快速开始

### 2.1 获取 API Keys

#### Qwen (阿里云通义千问)

1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
2. 开通服务并创建 API Key
3. 复制 API Key

#### DeepSeek

1. 访问 [DeepSeek 平台](https://platform.deepseek.com/)
2. 注册并充值（性价比极高，建议充值 ￥50）
3. 创建 API Key

#### Doubao (火山引擎豆包)

1. 访问 [火山引擎控制台](https://console.volcengine.com/ark)
2. 开通模型推理服务
3. 创建 API Key

---

### 2.2 配置 API Keys

编辑 `.env` 文件：

```bash
# Qwen (Aliyun)
ALIYUN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALIYUN_MODEL=qwen-max                # 推荐模型

# DeepSeek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat         # 推荐模型

# Doubao (火山引擎)
ARK_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=doubao-pro-32k            # 推荐模型

# 启用配置
ENABLE_QWEN=true
ENABLE_DEEPSEEK=true
ENABLE_DOUBAO=true
```

---

## 3. 任务分工详解

### 3.1 任务路由表

| 任务类型 | 分配模型 | 原因 |
|---------|---------|------|
| **大纲** | Qwen | 需要全局视野和长上下文 |
| **风格元素** | Qwen | 需要保持全书风格一致性 |
| **人物设计** | Qwen | 需要记住所有人物关系网 |
| **世界观规则** | Qwen | 需要构建完整设定体系 |
| **事件** | DeepSeek | 需要逻辑推理和因果链 |
| **场景物品冲突** | DeepSeek | 需要结构化思考 |
| **评估** | DeepSeek | 需要客观分析能力 |
| **一致性检查** | DeepSeek | 需要检测逻辑漏洞 |
| **章节内容** | Doubao | 需要优美文笔和创意 |
| **修订润色** | Doubao | 需要文学创作能力 |
| **对话生成** | Doubao | 需要生动自然的对话 |

---

### 3.2 模型特性对比

#### 🧠 Qwen - 总览记忆专家

**核心优势**
- ✅ 长上下文窗口（200K+ tokens）
- ✅ 强大的长期记忆能力
- ✅ 全局一致性把控好

**适合场景**
```python
# 生成大纲
outline = await generate_outline(
    style="玄幻修仙",
    theme="少年成长",
    chapter_count=500,
    llm="qwen"  # 使用 Qwen
)

# 设计人物
characters = await design_characters(
    count=25,
    relationships_complex=True,
    llm="qwen"  # 需要记住所有关系
)
```

**参数建议**
```python
{
    "model": "qwen-max",
    "temperature": 0.7,      # 创造性适中
    "max_tokens": 4000,      # 大纲通常较长
    "top_p": 0.9
}
```

---

#### 🔍 DeepSeek - 逻辑结构专家

**核心优势**
- ✅ 强大的逻辑推理能力
- ✅ 因果关系分析准确
- ✅ **性价比极高**（重要！）

**适合场景**
```python
# 设计事件链
events = await design_events(
    chapter_range=(1, 10),
    ensure_causality=True,
    llm="deepseek"  # 逻辑推理强
)

# 评估内容质量
evaluation = await evaluate_content(
    content=chapter_content,
    criteria=["structure", "consistency"],
    llm="deepseek"  # 客观分析
)
```

**参数建议**
```python
{
    "model": "deepseek-chat",
    "temperature": 0.5,      # 逻辑任务需要稳定
    "max_tokens": 2000,
    "top_p": 0.85
}
```

---

#### ✨ Doubao - 创意文笔专家

**核心优势**
- ✅ 文学创作能力强
- ✅ 文笔优美流畅
- ✅ 对话生动自然

**适合场景**
```python
# 生成章节内容
chapter = await generate_chapter(
    outline="少年初入修仙界...",
    target_words=3000,
    style="优美抒情",
    llm="doubao"  # 文笔最好
)

# 润色修订
polished = await polish_content(
    content=draft_content,
    improvements=["增强描写", "丰富对话"],
    llm="doubao"  # 创意强
)
```

**参数建议**
```python
{
    "model": "doubao-pro-32k",
    "temperature": 0.8,      # 创作需要高创造性
    "max_tokens": 4000,
    "top_p": 0.95
}
```

---

## 4. 配置示例

### 4.1 项目配置文件

**config/llm_config.yaml**

```yaml
llm:
  # Qwen 配置
  qwen:
    enabled: true
    provider: aliyun
    model: qwen-max
    api_key_env: ALIYUN_API_KEY
    default_params:
      temperature: 0.7
      max_tokens: 4000
      top_p: 0.9
    rate_limit:
      rpm: 60          # 每分钟请求数
      tpm: 200000      # 每分钟 tokens
    timeout: 120       # 秒
    
  # DeepSeek 配置
  deepseek:
    enabled: true
    provider: openai_compatible
    model: deepseek-chat
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
    default_params:
      temperature: 0.5
      max_tokens: 2000
      top_p: 0.85
    rate_limit:
      rpm: 100
      tpm: 500000
    timeout: 90
    
  # Doubao 配置
  doubao:
    enabled: true
    provider: volcengine
    model: doubao-pro-32k
    base_url: https://ark.cn-beijing.volces.com/api/v3
    api_key_env: ARK_API_KEY
    default_params:
      temperature: 0.8
      max_tokens: 4000
      top_p: 0.95
    rate_limit:
      rpm: 60
      tpm: 150000
    timeout: 150

# 任务路由配置
routing:
  # 规划类任务
  planning:
    - outline
    - style_elements
    - character_design
    - worldview
    default_llm: qwen
    
  # 逻辑类任务
  logic:
    - events
    - scenes
    - conflicts
    - evaluation
    - consistency_check
    default_llm: deepseek
    
  # 创作类任务
  creation:
    - chapter_content
    - revision
    - polish
    - dialogue
    default_llm: doubao
```

---

### 4.2 Python 代码配置

**使用配置文件**

```python
from creative_autogpt.config import LLMConfig

# 加载配置
config = LLMConfig.from_yaml("config/llm_config.yaml")

# 获取特定模型配置
qwen_config = config.get_llm_config("qwen")
print(f"Qwen Model: {qwen_config.model}")
print(f"Temperature: {qwen_config.default_params.temperature}")
```

**动态配置**

```python
from creative_autogpt.utils.llm_client import MultiLLMClient

# 创建客户端
client = MultiLLMClient()

# 为特定会话自定义配置
client.configure_session(
    session_id="sess_123",
    overrides={
        "qwen": {
            "temperature": 0.8,  # 提高创造性
        },
        "deepseek": {
            "enabled": False,    # 临时禁用
        }
    }
)
```

---

## 5. 使用示例

### 5.1 基础使用

```python
from creative_autogpt.core.loop_engine import LoopEngine
from creative_autogpt.modes.novel import NovelMode

# 初始化引擎
engine = LoopEngine(
    mode=NovelMode(),
    session_id="sess_123"
)

# 创建小说
result = await engine.run(
    goal={
        "style": "玄幻修仙",
        "theme": "少年成长",
        "target_words": 100000,
        "chapter_count": 50
    }
)

# 引擎会自动路由任务到合适的 LLM
# - 大纲 → Qwen
# - 事件 → DeepSeek
# - 章节 → Doubao
```

---

### 5.2 手动指定模型

```python
from creative_autogpt.utils.llm_client import MultiLLMClient

client = MultiLLMClient()

# 强制使用特定模型
outline = await client.generate(
    task_type="outline",
    prompt="创作一个玄幻小说大纲...",
    llm="qwen",              # 明确指定
    temperature=0.8
)

# 尝试多个模型（容错）
chapter = await client.generate_with_fallback(
    task_type="chapter",
    prompt="写第一章...",
    preferred_llm="doubao",
    fallback_llms=["qwen", "deepseek"]  # 失败时尝试备选
)
```

---

### 5.3 批量任务

```python
from creative_autogpt.utils.llm_client import MultiLLMClient
import asyncio

client = MultiLLMClient()

# 并发调用不同模型
tasks = [
    client.generate(task_type="outline", llm="qwen", ...),
    client.generate(task_type="events", llm="deepseek", ...),
    client.generate(task_type="chapter", llm="doubao", ...)
]

results = await asyncio.gather(*tasks)
```

---

## 6. 成本优化

### 6.1 成本对比

| 模型 | 输入价格 | 输出价格 | 相对成本 |
|------|---------|---------|---------|
| **Qwen Max** | ￥0.04/1K | ￥0.12/1K | 中等 |
| **DeepSeek** | ￥0.001/1K | ￥0.002/1K | **极低** ⭐ |
| **Doubao Pro** | ￥0.008/1K | ￥0.008/1K | 低 |

### 6.2 优化策略

**策略 1：高频任务用 DeepSeek**

```python
# 评估任务非常频繁，使用 DeepSeek
routing_config = {
    "evaluation": "deepseek",      # 每个任务都评估
    "consistency_check": "deepseek" # 频繁检查
}
```

**策略 2：限制 token 使用**

```python
# 控制输出长度
client.generate(
    task_type="chapter",
    llm="doubao",
    max_tokens=3500,     # 限制最大 tokens
    target_words=3000    # 明确字数要求
)
```

**策略 3：缓存常用结果**

```python
from creative_autogpt.utils.cache import LLMCache

cache = LLMCache()

# 尝试从缓存获取
cached_result = cache.get(prompt_hash)
if cached_result:
    return cached_result

# 未命中缓存才调用 LLM
result = await client.generate(...)
cache.set(prompt_hash, result)
```

**策略 4：智能重试**

```python
# 先用便宜的模型，失败再用贵的
result = await client.generate_with_fallback(
    task_type="chapter",
    preferred_llm="deepseek",     # 先用 DeepSeek（便宜）
    fallback_llms=["doubao"],     # 失败再用 Doubao
    quality_threshold=7.0          # 质量阈值
)
```

---

## 7. 监控与调试

### 7.1 查看 LLM 调用统计

```python
from creative_autogpt.utils.monitoring import LLMMonitor

monitor = LLMMonitor()

# 获取统计
stats = monitor.get_stats(session_id="sess_123")

print(f"Qwen 调用次数: {stats['qwen']['calls']}")
print(f"DeepSeek 总成本: ￥{stats['deepseek']['total_cost']:.2f}")
print(f"Doubao 平均响应时间: {stats['doubao']['avg_latency']:.2f}s")
```

---

### 7.2 实时监控

**WebSocket 事件**

```javascript
// 前端监听 LLM 调用事件
ws.on('llm.llm_call_completed', (data) => {
  console.log(`${data.provider} 完成调用`);
  console.log(`耗时: ${data.elapsed_time}s`);
  console.log(`Tokens: ${data.tokens_used.total_tokens}`);
  console.log(`成本: $${data.cost.toFixed(4)}`);
});
```

---

### 7.3 日志查看

```bash
# 查看 LLM 调用日志
tail -f logs/app.log | grep "LLM_CALL"

# 示例输出
# 2026-01-23 10:05:30 | INFO | LLM_CALL | qwen | outline | START
# 2026-01-23 10:07:30 | INFO | LLM_CALL | qwen | outline | SUCCESS | 120s | 3500 tokens | ￥0.42
```

---

## 8. 故障处理

### 8.1 模型不可用

**问题**：某个模型 API 失败

**自动容错**

```python
# 系统会自动使用备选模型
result = await client.generate(
    task_type="chapter",
    llm="doubao",
    auto_fallback=True  # 启用自动容错
)

# 如果 Doubao 失败，会尝试：
# 1. Qwen (同样擅长创作)
# 2. DeepSeek (最后的备选)
```

---

### 8.2 频率限制

**问题**：超出 API 调用频率限制

**解决方案**

```python
# 配置频率限制器
client.configure_rate_limiter(
    "qwen",
    max_rpm=60,        # 每分钟最多 60 次
    max_tpm=200000,    # 每分钟最多 200K tokens
    strategy="wait"    # 超限时等待（而非失败）
)
```

---

### 8.3 质量不达标

**问题**：生成内容质量不符合预期

**切换模型**

```python
# 如果 DeepSeek 生成的章节质量不够
# 可以临时改用 Doubao
session_config = {
    "chapter_content": "doubao"  # 覆盖默认路由
}

engine.update_routing(session_config)
```

---

## 9. 最佳实践

### 9.1 任务分配原则

✅ **DO**
- 大纲、设定 → Qwen（需要全局视野）
- 评估、检查 → DeepSeek（客观且便宜）
- 章节、润色 → Doubao（文笔最好）

❌ **DON'T**
- 不要用 Qwen 生成所有内容（成本高）
- 不要用 DeepSeek 写章节（文笔不如 Doubao）
- 不要忽略模型优势，随意分配

---

### 9.2 参数调优

```python
# 规划类任务（Qwen）
planning_params = {
    "temperature": 0.7,    # 适中
    "top_p": 0.9,
    "max_tokens": 4000
}

# 逻辑类任务（DeepSeek）
logic_params = {
    "temperature": 0.5,    # 较低，保证稳定
    "top_p": 0.85,
    "max_tokens": 2000
}

# 创作类任务（Doubao）
creation_params = {
    "temperature": 0.8,    # 较高，增强创造力
    "top_p": 0.95,
    "max_tokens": 4000
}
```

---

### 9.3 成本控制

```python
# 预算控制器
from creative_autogpt.utils.budget import BudgetController

budget = BudgetController(
    total_budget=100.0,      # 总预算 ￥100
    alerts=[50.0, 80.0]      # 使用50%和80%时预警
)

# 执行前检查
if budget.can_execute(estimated_cost=2.5):
    result = await client.generate(...)
    budget.record_cost(actual_cost=2.3)
else:
    print("预算不足，请充值或优化配置")
```

---

## 10. 常见问题

### Q1: 可以只用一个模型吗？

**A**: 可以，但不推荐。

```python
# 只用 Doubao（适合小项目）
config = {
    "default_llm": "doubao",
    "enable_routing": False
}

# 但会损失：
# - Qwen 的长上下文优势
# - DeepSeek 的成本优势
```

---

### Q2: 如何判断模型分工是否合理？

**A**: 查看评估报告

```bash
# 生成报告
python scripts/analyze_llm_usage.py --session sess_123

# 输出示例
# ✅ Qwen: 12次调用，质量评分 8.5
# ✅ DeepSeek: 50次调用，质量评分 8.2，成本仅 ￥0.15
# ⚠️ Doubao: 45次调用，质量评分 8.8，但3次重试
```

---

### Q3: 模型返回内容不符合要求怎么办？

**A**: 调整 Prompt 或切换模型

```python
# 方案1：优化 Prompt
result = await client.generate(
    prompt="""
你是一位专业小说作家。
要求：
1. 文笔优美流畅
2. 情节紧凑
3. 字数控制在3000字
""",
    llm="doubao"
)

# 方案2：切换模型
result = await client.generate(
    prompt=same_prompt,
    llm="qwen"  # 换个模型试试
)
```

---

## 11. 参考资源

- [多 LLM 架构文档](../architecture/MULTI_LLM.md)
- [API 文档](../api/REST_API.md)
- [成本优化指南](./COST_OPTIMIZATION.md)

---

*版本: 1.0*  
*最后更新: 2026-01-23*
