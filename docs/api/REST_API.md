# REST API 文档

> Creative AutoGPT REST API 接口规范

## 基础信息

- **基础URL**: `http://localhost:8000/api/v1`
- **认证方式**: Bearer Token (可选)
- **数据格式**: JSON
- **字符编码**: UTF-8

---

## 1. 会话管理 API

### 1.1 创建会话

创建一个新的小说创作会话。

**请求**

```http
POST /sessions
Content-Type: application/json

{
  "mode": "novel",              // 写作模式: novel/script/larp
  "config": {
    "style": "玄幻",            // 风格
    "theme": "修仙升级",        // 主题
    "target_words": 1000000,    // 目标字数
    "chapter_count": 500,       // 章节数
    "llm_config": {
      "qwen_enabled": true,
      "deepseek_enabled": true,
      "doubao_enabled": true
    }
  },
  "metadata": {
    "title": "我的玄幻小说",
    "description": "一个少年修仙的故事"
  }
}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "session_id": "sess_1234567890",
    "mode": "novel",
    "status": "created",
    "config": { /* 同请求 */ },
    "created_at": "2026-01-23T10:00:00Z",
    "updated_at": "2026-01-23T10:00:00Z"
  }
}
```

**状态码**
- `200` - 成功
- `400` - 参数错误
- `500` - 服务器错误

---

### 1.2 获取会话列表

**请求**

```http
GET /sessions?page=1&page_size=20&mode=novel&status=active
```

**查询参数**
- `page` (int, 可选): 页码，默认 1
- `page_size` (int, 可选): 每页数量，默认 20
- `mode` (string, 可选): 筛选模式
- `status` (string, 可选): 筛选状态 (created/running/paused/completed/failed)

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 42,
    "page": 1,
    "page_size": 20,
    "sessions": [
      {
        "session_id": "sess_1234567890",
        "mode": "novel",
        "title": "我的玄幻小说",
        "status": "running",
        "progress": {
          "total_tasks": 100,
          "completed_tasks": 45,
          "percentage": 45.0
        },
        "created_at": "2026-01-23T10:00:00Z",
        "updated_at": "2026-01-23T12:30:00Z"
      }
      // ... 更多会话
    ]
  }
}
```

---

### 1.3 获取会话详情

**请求**

```http
GET /sessions/{session_id}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "session_id": "sess_1234567890",
    "mode": "novel",
    "status": "running",
    "config": { /* 配置信息 */ },
    "metadata": { /* 元数据 */ },
    "stats": {
      "total_tasks": 100,
      "completed_tasks": 45,
      "failed_tasks": 2,
      "total_words": 125000,
      "chapters_completed": 45,
      "llm_calls": {
        "qwen": 120,
        "deepseek": 250,
        "doubao": 380
      }
    },
    "created_at": "2026-01-23T10:00:00Z",
    "updated_at": "2026-01-23T12:30:00Z",
    "last_checkpoint": "2026-01-23T12:30:00Z"
  }
}
```

---

### 1.4 删除会话

**请求**

```http
DELETE /sessions/{session_id}
```

**响应**

```json
{
  "code": 200,
  "message": "Session deleted successfully",
  "data": null
}
```

---

## 2. 智能提示词 API 🆕

> 让不懂提示词的用户也能轻松使用！

### 2.1 智能扩展提示词

将用户的简单描述自动扩展为完整的创作配置。

**请求**

```http
POST /prompts/enhance
Content-Type: application/json

{
  "user_input": "写一个玄幻小说，主角是废材逆袭成仙帝，100万字",
  "mode": "novel"
}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "enhanced": {
      "style": "玄幻修仙",
      "theme": "废材少年逆袭成为仙帝的热血成长故事",
      "target_words": 1000000,
      "chapter_count": 500,
      
      "protagonist": {
        "name": null,
        "gender": "男",
        "age": "16-18岁",
        "personality": "坚韧不拔、心思缜密、重情重义",
        "background": "曾被视为废材的宗门弟子，意外获得机缘",
        "growth_arc": "从被人嘲笑的废材到一步步证道成仙帝"
      },
      
      "world_setting": {
        "type": "仙侠世界",
        "era": "架空上古",
        "power_system": "炼气→筑基→金丹→元婴→化神→渡劫→大乘→仙帝",
        "key_locations": ["宗门", "秘境", "仙界"],
        "factions": ["正道宗门", "魔道势力", "上古遗族"]
      },
      
      "plot_elements": [
        "废材逆袭",
        "奇遇机缘",
        "宗门斗争",
        "感情线",
        "最终证道"
      ],
      
      "style_elements": {
        "tone": "热血励志",
        "pacing": "快节奏升级",
        "description_style": "简洁有力",
        "dialogue_style": "个性鲜明"
      },
      
      "constraints": [
        "保持主角人设一致",
        "修炼体系逻辑自洽"
      ],
      
      "special_requirements": [
        "100万字长篇"
      ],
      
      "confidence": 0.85
    },
    "raw_input": "写一个玄幻小说，主角是废材逆袭成仙帝，100万字",
    "auto_confirm_recommended": true
  }
}
```

**字段说明**
- `confidence` (float): 0-1，表示扩展的置信度。>= 0.8 建议自动确认
- `auto_confirm_recommended` (bool): 是否建议自动确认

---

### 2.2 调整提示词配置

根据用户反馈调整已生成的配置。

**请求**

```http
POST /prompts/refine
Content-Type: application/json

{
  "enhanced": { /* 2.1 返回的 enhanced 对象 */ },
  "feedback": "主角改成女的，增加更多感情线"
}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "enhanced": {
      "style": "玄幻修仙",
      "protagonist": {
        "gender": "女",
        "personality": "外柔内刚、聪慧过人、重情重义",
        /* ... 其他调整 ... */
      },
      "plot_elements": [
        "废材逆袭",
        "感情纠葛",
        "宗门斗争",
        "虐恋情深",
        "最终证道"
      ],
      /* ... 其他字段 ... */
      "confidence": 0.82
    }
  }
}
```

---

### 2.3 直接创建会话（一步到位）

结合智能扩展和会话创建，用户一句话即可开始创作。

**请求**

```http
POST /sessions/smart-create
Content-Type: application/json

{
  "user_input": "写一个都市修仙，主角重生回到高中，有系统金手指",
  "auto_confirm": true,
  "start_immediately": false
}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "session_id": "sess_9876543210",
    "mode": "novel",
    "status": "created",
    "enhanced_config": { /* 完整配置 */ },
    "confidence": 0.88,
    "message": "已为您自动生成配置并创建会话"
  }
}
```

**参数说明**
- `auto_confirm` (bool): 当置信度 >= 0.8 时自动确认，否则返回配置让用户确认
- `start_immediately` (bool): 创建后是否立即开始执行

---

## 3. 任务管理 API

### 3.1 启动执行

启动或继续会话执行。

**请求**

```http
POST /sessions/{session_id}/start
Content-Type: application/json

{
  "mode": "auto",          // auto: 自动执行, manual: 手动单步
  "checkpoint": null       // 可选，从特定检查点恢复
}
```

**响应**

```json
{
  "code": 200,
  "message": "Execution started",
  "data": {
    "session_id": "sess_1234567890",
    "status": "running",
    "execution_mode": "auto"
  }
}
```

---

### 2.2 暂停执行

**请求**

```http
POST /sessions/{session_id}/pause
```

**响应**

```json
{
  "code": 200,
  "message": "Execution paused",
  "data": {
    "session_id": "sess_1234567890",
    "status": "paused",
    "checkpoint_id": "ckpt_9876543210"
  }
}
```

---

### 2.3 执行下一步（手动模式）

**请求**

```http
POST /sessions/{session_id}/next
```

**响应**

```json
{
  "code": 200,
  "message": "Task executed",
  "data": {
    "task_id": "task_001",
    "task_type": "outline",
    "status": "completed",
    "result": {
      "content": "# 小说大纲\n\n第一卷：初入修仙...",
      "metadata": {
        "word_count": 2500,
        "llm_used": "qwen"
      }
    },
    "evaluation": {
      "passed": true,
      "score": 8.5,
      "comments": "结构完整，逻辑清晰"
    }
  }
}
```

---

### 2.4 获取任务列表

**请求**

```http
GET /sessions/{session_id}/tasks?status=completed&page=1&page_size=50
```

**查询参数**
- `status` (string, 可选): pending/running/completed/failed
- `task_type` (string, 可选): outline/character/event/chapter 等
- `page`, `page_size`: 分页参数

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "tasks": [
      {
        "task_id": "task_001",
        "task_type": "outline",
        "status": "completed",
        "llm_used": "qwen",
        "created_at": "2026-01-23T10:05:00Z",
        "completed_at": "2026-01-23T10:07:30Z",
        "retries": 0
      },
      // ... 更多任务
    ]
  }
}
```

---

### 2.5 获取任务详情

**请求**

```http
GET /sessions/{session_id}/tasks/{task_id}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "task_001",
    "task_type": "outline",
    "status": "completed",
    "dependencies": [],
    "prompt": {
      "template": "outline_template",
      "context": {
        "style": "玄幻",
        "theme": "修仙升级"
      },
      "full_prompt": "根据以下风格和主题..."
    },
    "result": {
      "content": "# 小说大纲\n\n...",
      "word_count": 2500,
      "llm_used": "qwen",
      "tokens_used": 3500
    },
    "evaluation": {
      "passed": true,
      "score": 8.5,
      "criteria": {
        "structure": 9.0,
        "creativity": 8.0,
        "consistency": 8.5
      },
      "comments": "结构完整，逻辑清晰"
    },
    "history": [
      {
        "attempt": 1,
        "status": "completed",
        "timestamp": "2026-01-23T10:07:30Z"
      }
    ],
    "created_at": "2026-01-23T10:05:00Z",
    "completed_at": "2026-01-23T10:07:30Z"
  }
}
```

---

### 2.6 重试任务

**请求**

```http
POST /sessions/{session_id}/tasks/{task_id}/retry
Content-Type: application/json

{
  "feedback": "需要增加更多细节描述",  // 可选
  "modify_prompt": {                  // 可选
    "style": "更加玄幻"
  }
}
```

**响应**

```json
{
  "code": 200,
  "message": "Task retry initiated",
  "data": {
    "task_id": "task_001",
    "status": "running",
    "retry_count": 1
  }
}
```

---

## 4. 任务预览与反馈 API 🆕

> 每一步都让用户看见、每一步都可以调整！

### 4.1 获取任务预览

获取当前任务的预览内容。

**请求**

```http
GET /sessions/{session_id}/tasks/{task_id}/preview
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "task_003",
    "task_type": "character_design",
    "task_name": "主角人物设计",
    
    "preview": {
      "content": "【主角设定】\n\n姓名：林轩\n年龄：16岁\n性格：外表冷漠，内心热血...",
      "summary": "废材少年林轩的人物设定，包含性格、背景、能力等",
      "key_points": [
        "16岁少年，宗门废材",
        "性格坚韧，心思缜密",
        "隐藏天赋：混沌体质"
      ],
      "word_count": 2350
    },
    
    "quality": {
      "score": 4.2,
      "max_score": 5.0,
      "passed": true
    },
    
    "status": "pending_review",
    "revision_count": 0,
    
    "quick_feedbacks": [
      {"id": "more_detail", "label": "内容再详细一些", "icon": "📝"},
      {"id": "more_creative", "label": "再有创意一点", "icon": "✨"},
      {"id": "shorter", "label": "精简一下", "icon": "✂️"}
    ]
  }
}
```

---

### 4.2 确认/拒绝预览

用户确认或请求重新生成。

**请求 - 确认通过**

```http
POST /sessions/{session_id}/tasks/{task_id}/preview/confirm
Content-Type: application/json

{
  "action": "approve"
}
```

**请求 - 请求重新生成**

```http
POST /sessions/{session_id}/tasks/{task_id}/preview/confirm
Content-Type: application/json

{
  "action": "regenerate",
  "reason": "内容不够详细"
}
```

**响应**

```json
{
  "code": 200,
  "message": "Preview approved",
  "data": {
    "task_id": "task_003",
    "status": "approved",
    "next_task": {
      "task_id": "task_004",
      "task_type": "event_planning",
      "task_name": "核心事件规划"
    }
  }
}
```

---

### 4.3 提交聊天反馈

用户通过聊天提交反馈意见。

**请求**

```http
POST /sessions/{session_id}/tasks/{task_id}/feedback
Content-Type: application/json

{
  "message": "主角的性格太软弱了，我想要他更霸气一点，即使被嘲笑也要冷笑回去",
  "feedback_type": "modification"
}
```

**响应**

```json
{
  "code": 200,
  "message": "Feedback received and transformed",
  "data": {
    "feedback_id": "fb_001",
    "task_id": "task_003",
    
    "original": "主角的性格太软弱了，我想要他更霸气一点，即使被嘲笑也要冷笑回去",
    
    "transformed": {
      "target": "character.protagonist.personality",
      "action": "modify",
      "prompt_patch": "主角性格调整：外表冷峻霸气，面对嘲讽时以冷笑回应...",
      "key_changes": [
        "性格从'冷漠'调整为'霸气'",
        "增加'面对嘲讽冷笑回应'的行为模式"
      ],
      "confidence": 0.85
    },
    
    "scope_required": true,
    "scope_options": [
      {
        "id": "current_task",
        "label": "只影响当前任务",
        "description": "只修改当前正在预览的内容",
        "is_default": true
      },
      {
        "id": "future",
        "label": "影响当前和后续任务",
        "description": "当前任务和之后的章节都会应用这个修改"
      },
      {
        "id": "global",
        "label": "修改全局设定",
        "description": "更新主角的基础人设，影响整个项目",
        "warning": "这可能导致已完成的内容与新设定不一致"
      }
    ],
    
    "ai_response": "收到！我会调整主角的性格表现，让他更霸气。请选择这个修改的作用范围。"
  }
}
```

---

### 4.4 选择反馈作用域

用户选择反馈的影响范围。

**请求**

```http
POST /sessions/{session_id}/tasks/{task_id}/feedback/{feedback_id}/scope
Content-Type: application/json

{
  "scope": "current_task"
}
```

**响应**

```json
{
  "code": 200,
  "message": "Scope selected, regenerating...",
  "data": {
    "feedback_id": "fb_001",
    "scope": "current_task",
    "scope_description": "修改只会影响当前的人物设计任务",
    "status": "regenerating",
    "message": "好的，这个修改只会影响当前的人物设计，不会影响其他任务。正在重新生成..."
  }
}
```

---

### 4.5 获取任务聊天历史

**请求**

```http
GET /sessions/{session_id}/tasks/{task_id}/chat
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "task_003",
    "messages": [
      {
        "role": "system",
        "content": "任务开始：主角人物设计",
        "timestamp": "2026-01-23T10:04:00Z"
      },
      {
        "role": "assistant",
        "content": "已生成主角人物设计，请查看预览。",
        "timestamp": "2026-01-23T10:05:00Z"
      },
      {
        "role": "user",
        "content": "主角的性格太软弱了，我想要他更霸气一点",
        "timestamp": "2026-01-23T10:06:00Z"
      },
      {
        "role": "assistant",
        "content": "收到！我会调整主角的性格表现，让他更霸气。",
        "timestamp": "2026-01-23T10:06:05Z"
      }
    ],
    "total_messages": 4
  }
}
```

---

### 4.6 发送快捷反馈

**请求**

```http
POST /sessions/{session_id}/tasks/{task_id}/quick-feedback
Content-Type: application/json

{
  "quick_feedback_id": "more_detail"
}
```

**响应**

```json
{
  "code": 200,
  "message": "Quick feedback applied",
  "data": {
    "feedback_id": "fb_002",
    "quick_feedback_id": "more_detail",
    "applied_prompt": "请在现有基础上增加更多细节描述，包括外貌特征、心理活动、背景故事等",
    "scope": "current_task",
    "status": "regenerating"
  }
}
```

---

### 4.7 设置交互模式

配置预览和反馈的行为模式。

**请求**

```http
PUT /sessions/{session_id}/interaction-mode
Content-Type: application/json

{
  "preview_mode": "preview_each",
  "auto_approve_timeout": 300,
  "auto_approve_on_timeout": true,
  "quality_threshold": 3.5
}
```

**参数说明**
- `preview_mode`: 
  - `preview_each`: 每步都预览
  - `preview_key`: 只预览关键步骤（大纲、人物、章节）
  - `auto`: 自动执行，只在质量不达标时暂停
- `auto_approve_timeout`: 预览超时时间（秒）
- `auto_approve_on_timeout`: 超时后是自动通过还是暂停
- `quality_threshold`: 低于此分数强制预览

**响应**

```json
{
  "code": 200,
  "message": "Interaction mode updated",
  "data": {
    "preview_mode": "preview_each",
    "auto_approve_timeout": 300,
    "auto_approve_on_timeout": true,
    "quality_threshold": 3.5
  }
}
```

---

## 5. 内容查询 API

### 5.1 获取大纲

**请求**

```http
GET /sessions/{session_id}/outline
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "content": "# 小说大纲\n\n第一卷：初入修仙...",
    "word_count": 2500,
    "created_at": "2026-01-23T10:07:30Z",
    "version": 1,
    "task_id": "task_001"
  }
}
```

---

### 3.2 获取人物列表

**请求**

```http
GET /sessions/{session_id}/characters?page=1&page_size=20
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 25,
    "characters": [
      {
        "character_id": "char_001",
        "name": "李逍遥",
        "role": "主角",
        "basic_info": {
          "age": 16,
          "gender": "男",
          "origin": "青云门"
        },
        "personality": "坚韧不拔，重情重义",
        "abilities": ["剑法", "炼丹"],
        "relationships": [
          {
            "target": "林月如",
            "relation": "道侣",
            "description": "青梅竹马"
          }
        ],
        "arc": "从凡人到仙尊的成长之路",
        "created_at": "2026-01-23T10:10:00Z"
      }
      // ... 更多人物
    ]
  }
}
```

---

### 3.3 获取章节列表

**请求**

```http
GET /sessions/{session_id}/chapters?page=1&page_size=50&status=completed
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 500,
    "chapters": [
      {
        "chapter_id": "chap_001",
        "chapter_number": 1,
        "title": "第一章 初入修仙界",
        "status": "completed",
        "word_count": 3500,
        "summary": "少年李逍遥意外进入修仙界...",
        "created_at": "2026-01-23T11:00:00Z",
        "updated_at": "2026-01-23T11:15:00Z"
      }
      // ... 更多章节
    ]
  }
}
```

---

### 3.4 获取章节内容

**请求**

```http
GET /sessions/{session_id}/chapters/{chapter_id}
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "chapter_id": "chap_001",
    "chapter_number": 1,
    "title": "第一章 初入修仙界",
    "content": "清晨的第一缕阳光洒在青云山上...\n\n（章节正文）",
    "word_count": 3500,
    "summary": "少年李逍遥意外进入修仙界...",
    "characters_involved": ["李逍遥", "林月如"],
    "events": ["初入宗门", "拜师"],
    "metadata": {
      "llm_used": "doubao",
      "tokens_used": 5200,
      "revision_count": 1
    },
    "versions": [
      {
        "version": 1,
        "content": "...",
        "created_at": "2026-01-23T11:00:00Z"
      }
    ],
    "created_at": "2026-01-23T11:00:00Z",
    "updated_at": "2026-01-23T11:15:00Z"
  }
}
```

---

## 6. 导出 API

### 4.1 导出全书

**请求**

```http
POST /sessions/{session_id}/export
Content-Type: application/json

{
  "format": "txt",              // txt/markdown/json
  "include_metadata": true,     // 是否包含元数据
  "chapter_range": {            // 可选，章节范围
    "start": 1,
    "end": 100
  }
}
```

**响应**

```json
{
  "code": 200,
  "message": "Export completed",
  "data": {
    "export_id": "exp_123456",
    "format": "txt",
    "download_url": "/api/v1/exports/exp_123456/download",
    "file_size": 2500000,        // bytes
    "expires_at": "2026-01-24T10:00:00Z"
  }
}
```

---

### 4.2 下载导出文件

**请求**

```http
GET /exports/{export_id}/download
```

**响应**
- Content-Type: `text/plain` / `application/json`
- Content-Disposition: `attachment; filename="novel.txt"`
- 文件内容流

---

## 7. 评估与审计 API

### 5.1 获取评估报告

**请求**

```http
GET /sessions/{session_id}/evaluation/summary
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "overall_score": 8.2,
    "total_evaluations": 100,
    "passed_count": 95,
    "failed_count": 5,
    "criteria_scores": {
      "structure": 8.5,
      "creativity": 8.0,
      "consistency": 8.8,
      "style": 7.5
    },
    "by_task_type": {
      "outline": {
        "avg_score": 8.5,
        "count": 1
      },
      "chapter": {
        "avg_score": 8.1,
        "count": 50
      }
    }
  }
}
```

---

### 5.2 获取一致性检查报告

**请求**

```http
GET /sessions/{session_id}/consistency/check
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_issues": 3,
    "issues": [
      {
        "issue_id": "issue_001",
        "type": "character_inconsistency",
        "severity": "medium",
        "description": "人物年龄不一致",
        "details": {
          "character": "李逍遥",
          "conflict": "第10章描述16岁，第50章描述17岁，时间跨度仅1个月"
        },
        "suggested_fix": "调整时间线或年龄描述",
        "affected_chapters": [10, 50]
      }
      // ... 更多问题
    ]
  }
}
```

---

## 8. 统计与监控 API

### 6.1 获取统计数据

**请求**

```http
GET /sessions/{session_id}/stats
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_words": 125000,
    "chapters_completed": 45,
    "characters_count": 25,
    "events_count": 120,
    "llm_usage": {
      "qwen": {
        "calls": 120,
        "tokens_used": 850000
      },
      "deepseek": {
        "calls": 250,
        "tokens_used": 1200000
      },
      "doubao": {
        "calls": 380,
        "tokens_used": 2500000
      }
    },
    "time_stats": {
      "total_time_seconds": 7200,
      "avg_task_time": 72,
      "started_at": "2026-01-23T10:00:00Z",
      "last_active": "2026-01-23T12:30:00Z"
    }
  }
}
```

---

## 9. 配置管理 API

### 7.1 获取 LLM 配置

**请求**

```http
GET /sessions/{session_id}/config/llm
```

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "qwen": {
      "enabled": true,
      "model": "qwen-max",
      "temperature": 0.7,
      "max_tokens": 4000
    },
    "deepseek": {
      "enabled": true,
      "model": "deepseek-chat",
      "temperature": 0.5,
      "max_tokens": 2000
    },
    "doubao": {
      "enabled": true,
      "model": "doubao-pro",
      "temperature": 0.8,
      "max_tokens": 4000
    }
  }
}
```

---

### 7.2 更新 LLM 配置

**请求**

```http
PUT /sessions/{session_id}/config/llm
Content-Type: application/json

{
  "qwen": {
    "temperature": 0.8
  },
  "doubao": {
    "enabled": false
  }
}
```

**响应**

```json
{
  "code": 200,
  "message": "LLM configuration updated",
  "data": {
    // 更新后的完整配置
  }
}
```

---

## 10. 错误处理

### 错误响应格式

```json
{
  "code": 400,
  "message": "Invalid request parameters",
  "error": {
    "type": "ValidationError",
    "details": {
      "field": "config.target_words",
      "message": "must be greater than 0"
    }
  }
}
```

### 常见状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器错误 |
| 503 | 服务不可用（LLM调用失败） |

---

## 11. 速率限制

- **全局限制**: 100 请求/分钟
- **创建会话**: 10 次/小时
- **LLM调用**: 根据各平台限制

超出限制时返回 `429 Too Many Requests`。

---

## 附录：完整示例流程

```bash
# 1. 创建会话
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "novel",
    "config": {
      "style": "玄幻",
      "target_words": 100000,
      "chapter_count": 50
    }
  }'

# 2. 启动执行
curl -X POST http://localhost:8000/api/v1/sessions/sess_123/start

# 3. 查看进度
curl http://localhost:8000/api/v1/sessions/sess_123

# 4. 获取章节
curl http://localhost:8000/api/v1/sessions/sess_123/chapters

# 5. 导出全书
curl -X POST http://localhost:8000/api/v1/sessions/sess_123/export \
  -H "Content-Type: application/json" \
  -d '{"format": "txt"}'
```

---

*版本: 1.0*  
*最后更新: 2026-01-23*
