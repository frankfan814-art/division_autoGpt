# WebSocket API 文档

> Creative AutoGPT 实时通信接口规范

## 基础信息

- **WebSocket URL**: `ws://localhost:8000/ws`
- **协议**: WebSocket
- **消息格式**: JSON
- **心跳间隔**: 30秒

---

## 1. 连接建立

### 1.1 建立连接

**连接URL**

```
ws://localhost:8000/ws?session_id=sess_1234567890&token=optional_auth_token
```

**查询参数**
- `session_id` (必需): 会话ID
- `token` (可选): 认证令牌

**连接成功响应**

```json
{
  "type": "connection",
  "event": "connected",
  "data": {
    "session_id": "sess_1234567890",
    "client_id": "client_abc123",
    "server_time": "2026-01-23T10:00:00Z"
  },
  "timestamp": "2026-01-23T10:00:00Z"
}
```

---

### 1.2 心跳机制

**客户端发送（每30秒）**

```json
{
  "type": "ping",
  "timestamp": "2026-01-23T10:00:30Z"
}
```

**服务端响应**

```json
{
  "type": "pong",
  "timestamp": "2026-01-23T10:00:30Z"
}
```

---

## 2. 消息类型

### 2.1 消息结构

所有消息都遵循以下结构：

```json
{
  "type": "message_type",      // 消息类型
  "event": "event_name",        // 事件名称
  "data": { /* 具体数据 */ },  // 数据内容
  "timestamp": "ISO8601",       // 时间戳
  "sequence": 123               // 序列号（可选）
}
```

---

## 3. 执行进度事件

### 3.1 任务开始

**服务端推送**

```json
{
  "type": "task",
  "event": "task_started",
  "data": {
    "task_id": "task_001",
    "task_type": "outline",
    "task_name": "生成小说大纲",
    "dependencies": [],
    "estimated_time": 120,      // 预估时间（秒）
    "llm_assigned": "qwen"
  },
  "timestamp": "2026-01-23T10:05:00Z"
}
```

---

### 3.2 任务进度更新

**服务端推送**

```json
{
  "type": "task",
  "event": "task_progress",
  "data": {
    "task_id": "task_001",
    "task_type": "outline",
    "progress": 45.5,           // 进度百分比
    "status": "generating",     // 当前状态
    "current_step": "等待LLM响应",
    "elapsed_time": 55          // 已耗时（秒）
  },
  "timestamp": "2026-01-23T10:05:55Z"
}
```

---

### 3.3 任务完成

**服务端推送**

```json
{
  "type": "task",
  "event": "task_completed",
  "data": {
    "task_id": "task_001",
    "task_type": "outline",
    "status": "completed",
    "result": {
      "content": "# 小说大纲\n\n...",
      "word_count": 2500,
      "llm_used": "qwen",
      "tokens_used": 3500
    },
    "evaluation": {
      "passed": true,
      "score": 8.5,
      "comments": "结构完整，逻辑清晰"
    },
    "elapsed_time": 150         // 总耗时（秒）
  },
  "timestamp": "2026-01-23T10:07:30Z"
}
```

---

### 3.4 任务失败

**服务端推送**

```json
{
  "type": "task",
  "event": "task_failed",
  "data": {
    "task_id": "task_001",
    "task_type": "outline",
    "status": "failed",
    "error": {
      "code": "LLM_ERROR",
      "message": "LLM调用超时",
      "details": "qwen API timeout after 60s"
    },
    "retry_count": 2,
    "max_retries": 3,
    "next_retry_in": 30         // 下次重试倒计时（秒）
  },
  "timestamp": "2026-01-23T10:08:00Z"
}
```

---

### 3.5 任务评估不通过

**服务端推送**

```json
{
  "type": "task",
  "event": "task_evaluation_failed",
  "data": {
    "task_id": "task_001",
    "task_type": "outline",
    "evaluation": {
      "passed": false,
      "score": 5.2,
      "failed_criteria": {
        "structure": {
          "score": 4.0,
          "threshold": 6.0,
          "reason": "缺少高潮部分"
        }
      },
      "suggestions": [
        "增加冲突设计",
        "完善高潮情节"
      ]
    },
    "retry_count": 1,
    "action": "rewriting"       // 准备重写
  },
  "timestamp": "2026-01-23T10:07:35Z"
}
```

---

## 4. 会话事件

### 4.1 会话状态变化

**服务端推送**

```json
{
  "type": "session",
  "event": "status_changed",
  "data": {
    "session_id": "sess_1234567890",
    "old_status": "created",
    "new_status": "running",
    "reason": "用户启动执行"
  },
  "timestamp": "2026-01-23T10:00:00Z"
}
```

**可能的状态**
- `created` - 已创建
- `running` - 执行中
- `paused` - 已暂停
- `completed` - 已完成
- `failed` - 失败

---

### 4.2 全局进度更新

**服务端推送（每完成一个任务）**

```json
{
  "type": "session",
  "event": "progress_updated",
  "data": {
    "session_id": "sess_1234567890",
    "total_tasks": 100,
    "completed_tasks": 46,
    "failed_tasks": 2,
    "running_tasks": 1,
    "percentage": 46.0,
    "current_phase": "章节生成",
    "estimated_completion": "2026-01-23T15:30:00Z"
  },
  "timestamp": "2026-01-23T10:07:30Z"
}
```

---

### 4.3 检查点保存

**服务端推送**

```json
{
  "type": "session",
  "event": "checkpoint_saved",
  "data": {
    "session_id": "sess_1234567890",
    "checkpoint_id": "ckpt_9876543210",
    "completed_tasks": 46,
    "saved_state": {
      "outline": true,
      "characters": true,
      "chapters": [1, 2, 3, /* ... */ 46]
    }
  },
  "timestamp": "2026-01-23T10:07:30Z"
}
```

---

## 5. 内容生成事件

### 5.1 章节生成开始

**服务端推送**

```json
{
  "type": "content",
  "event": "chapter_generation_started",
  "data": {
    "chapter_id": "chap_001",
    "chapter_number": 1,
    "title": "第一章 初入修仙界",
    "outline": "少年李逍遥意外进入修仙界...",
    "target_words": 3000
  },
  "timestamp": "2026-01-23T11:00:00Z"
}
```

---

### 5.2 章节内容流式输出

**服务端推送（实时流）**

```json
{
  "type": "content",
  "event": "chapter_content_chunk",
  "data": {
    "chapter_id": "chap_001",
    "chunk_index": 0,
    "content": "清晨的第一缕阳光洒在青云山上，",
    "is_complete": false
  },
  "timestamp": "2026-01-23T11:00:05Z"
}
```

```json
{
  "type": "content",
  "event": "chapter_content_chunk",
  "data": {
    "chapter_id": "chap_001",
    "chunk_index": 1,
    "content": "少年李逍遥伸了个懒腰，从床上坐起。",
    "is_complete": false
  },
  "timestamp": "2026-01-23T11:00:06Z"
}
```

```json
{
  "type": "content",
  "event": "chapter_content_chunk",
  "data": {
    "chapter_id": "chap_001",
    "chunk_index": 2,
    "content": "今天是他入门的第一天。",
    "is_complete": true,            // 最后一个分块
    "total_words": 3500
  },
  "timestamp": "2026-01-23T11:15:00Z"
}
```

---

### 5.3 章节生成完成

**服务端推送**

```json
{
  "type": "content",
  "event": "chapter_completed",
  "data": {
    "chapter_id": "chap_001",
    "chapter_number": 1,
    "title": "第一章 初入修仙界",
    "word_count": 3500,
    "summary": "少年李逍遥初入修仙界，拜师青云门...",
    "evaluation": {
      "passed": true,
      "score": 8.2
    }
  },
  "timestamp": "2026-01-23T11:15:00Z"
}
```

---

## 6. 评估事件

### 6.1 质量评估开始

**服务端推送**

```json
{
  "type": "evaluation",
  "event": "evaluation_started",
  "data": {
    "task_id": "task_001",
    "task_type": "chapter",
    "evaluator": "deepseek",
    "criteria": ["structure", "creativity", "consistency", "style"]
  },
  "timestamp": "2026-01-23T11:15:05Z"
}
```

---

### 6.2 评估结果

**服务端推送**

```json
{
  "type": "evaluation",
  "event": "evaluation_completed",
  "data": {
    "task_id": "task_001",
    "task_type": "chapter",
    "passed": true,
    "overall_score": 8.2,
    "scores": {
      "structure": 8.5,
      "creativity": 8.0,
      "consistency": 8.8,
      "style": 7.5
    },
    "comments": "整体质量良好，文笔流畅，情节紧凑。",
    "suggestions": []
  },
  "timestamp": "2026-01-23T11:15:10Z"
}
```

---

### 6.3 一致性检查发现问题

**服务端推送**

```json
{
  "type": "evaluation",
  "event": "consistency_issue_detected",
  "data": {
    "issue_id": "issue_001",
    "type": "character_inconsistency",
    "severity": "medium",
    "description": "人物年龄不一致",
    "details": {
      "character": "李逍遥",
      "conflict": "第10章描述16岁，第50章描述17岁，时间跨度仅1个月"
    },
    "affected_tasks": ["task_010", "task_050"],
    "suggested_fix": "调整时间线或年龄描述",
    "auto_fixable": false
  },
  "timestamp": "2026-01-23T12:00:00Z"
}
```

---

## 7. LLM 调用事件

### 7.1 LLM 调用开始

**服务端推送**

```json
{
  "type": "llm",
  "event": "llm_call_started",
  "data": {
    "call_id": "llm_call_001",
    "task_id": "task_001",
    "provider": "qwen",
    "model": "qwen-max",
    "prompt_tokens": 1200,
    "purpose": "生成大纲"
  },
  "timestamp": "2026-01-23T10:05:30Z"
}
```

---

### 7.2 LLM 流式响应

**服务端推送**

```json
{
  "type": "llm",
  "event": "llm_streaming_chunk",
  "data": {
    "call_id": "llm_call_001",
    "chunk": "# 小说大纲\n\n",
    "chunk_index": 0
  },
  "timestamp": "2026-01-23T10:05:35Z"
}
```

---

### 7.3 LLM 调用完成

**服务端推送**

```json
{
  "type": "llm",
  "event": "llm_call_completed",
  "data": {
    "call_id": "llm_call_001",
    "task_id": "task_001",
    "provider": "qwen",
    "success": true,
    "tokens_used": {
      "prompt_tokens": 1200,
      "completion_tokens": 2300,
      "total_tokens": 3500
    },
    "elapsed_time": 120,        // 秒
    "cost": 0.035               // 美元（估算）
  },
  "timestamp": "2026-01-23T10:07:30Z"
}
```

---

### 7.4 LLM 调用失败

**服务端推送**

```json
{
  "type": "llm",
  "event": "llm_call_failed",
  "data": {
    "call_id": "llm_call_002",
    "task_id": "task_002",
    "provider": "deepseek",
    "error": {
      "code": "TIMEOUT",
      "message": "API request timeout",
      "details": "Request exceeded 60s timeout"
    },
    "will_retry": true,
    "retry_in": 30
  },
  "timestamp": "2026-01-23T10:10:00Z"
}
```

---

## 8. 实时预览与聊天反馈事件 🆕

> 每一步都让用户看见、每一步都可以调整！

### 8.1 任务预览推送

任务执行完成后，推送预览给用户。

**服务端推送**

```json
{
  "type": "preview",
  "event": "task_preview",
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
        "隐藏天赋：混沌体质",
        "家族被灭，身世神秘"
      ],
      "word_count": 2350
    },
    
    "quality": {
      "score": 4.2,
      "max_score": 5.0,
      "details": {
        "completeness": 4.5,
        "consistency": 4.0,
        "creativity": 4.1
      }
    },
    
    "status": "pending_review",
    "requires_confirmation": true,
    "auto_approve_timeout": 300
  },
  "timestamp": "2026-01-23T10:05:00Z"
}
```

---

### 8.2 预览确认

用户确认或请求修改。

**客户端发送 - 确认通过**

```json
{
  "type": "preview",
  "event": "preview_confirm",
  "data": {
    "task_id": "task_003",
    "action": "approve"
  },
  "timestamp": "2026-01-23T10:05:30Z"
}
```

**客户端发送 - 请求重新生成**

```json
{
  "type": "preview",
  "event": "preview_confirm",
  "data": {
    "task_id": "task_003",
    "action": "regenerate",
    "reason": "内容不够详细"
  },
  "timestamp": "2026-01-23T10:05:30Z"
}
```

**服务端响应**

```json
{
  "type": "preview",
  "event": "preview_confirmed",
  "data": {
    "task_id": "task_003",
    "action": "approve",
    "status": "approved",
    "next_task": "task_004"
  },
  "timestamp": "2026-01-23T10:05:31Z"
}
```

---

### 8.3 聊天反馈消息

用户通过聊天窗口发送反馈。

**客户端发送**

```json
{
  "type": "chat",
  "event": "user_feedback",
  "data": {
    "task_id": "task_003",
    "message": "主角的性格太软弱了，我想要他更霸气一点，即使被嘲笑也要冷笑回去",
    "feedback_type": "modification"
  },
  "timestamp": "2026-01-23T10:06:00Z"
}
```

**服务端响应 - 反馈确认**

```json
{
  "type": "chat",
  "event": "feedback_received",
  "data": {
    "task_id": "task_003",
    "feedback_id": "fb_001",
    "message": "收到您的反馈，正在分析..."
  },
  "timestamp": "2026-01-23T10:06:01Z"
}
```

**服务端响应 - 反馈转换完成**

```json
{
  "type": "chat",
  "event": "feedback_transformed",
  "data": {
    "task_id": "task_003",
    "feedback_id": "fb_001",
    
    "original": "主角的性格太软弱了，我想要他更霸气一点，即使被嘲笑也要冷笑回去",
    
    "transformed": {
      "target": "character.protagonist.personality",
      "action": "modify",
      "prompt_patch": "主角性格调整：外表冷峻霸气，面对嘲讽时以冷笑回应，眼神中透露出睥睨天下的气势。内心坚定，不为外界评价所动摇。",
      "key_changes": [
        "性格从'冷漠'调整为'霸气'",
        "增加'面对嘲讽冷笑回应'的行为模式",
        "强化内心坚定的特质"
      ]
    },
    
    "scope_question": {
      "required": true,
      "message": "这个修改应该影响哪些内容？",
      "options": [
        {
          "id": "current_task",
          "label": "只影响当前任务（人物设计）",
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
      ]
    },
    
    "confidence": 0.85,
    
    "ai_response": "收到！我会调整主角的性格表现，让他更霸气。请选择这个修改的作用范围。"
  },
  "timestamp": "2026-01-23T10:06:05Z"
}
```

---

### 8.4 作用域选择

用户选择反馈的作用域。

**客户端发送**

```json
{
  "type": "chat",
  "event": "scope_selection",
  "data": {
    "task_id": "task_003",
    "feedback_id": "fb_001",
    "selected_scope": "current_task"
  },
  "timestamp": "2026-01-23T10:06:30Z"
}
```

**服务端响应**

```json
{
  "type": "chat",
  "event": "scope_confirmed",
  "data": {
    "task_id": "task_003",
    "feedback_id": "fb_001",
    "scope": "current_task",
    "message": "好的，这个修改只会影响当前的人物设计，不会影响其他任务。正在重新生成...",
    "action": "regenerating"
  },
  "timestamp": "2026-01-23T10:06:31Z"
}
```

---

### 8.5 修订后预览

根据用户反馈修订后，推送新的预览。

**服务端推送**

```json
{
  "type": "preview",
  "event": "task_preview_revised",
  "data": {
    "task_id": "task_003",
    "revision_number": 1,
    
    "preview": {
      "content": "【主角设定】\n\n姓名：林轩\n年龄：16岁\n性格：外表冷峻霸气，面对嘲讽只是冷笑...",
      "summary": "调整后的主角设定，性格更加霸气",
      "key_points": [
        "16岁少年，宗门废材",
        "性格霸气，冷笑面对嘲讽",  // 已更新
        "隐藏天赋：混沌体质",
        "家族被灭，身世神秘"
      ],
      "word_count": 2480
    },
    
    "changes_applied": [
      {
        "feedback_id": "fb_001",
        "change": "性格从'冷漠'调整为'霸气'"
      }
    ],
    
    "quality": {
      "score": 4.4,
      "improved": true,
      "improvement": "+0.2"
    },
    
    "status": "pending_review",
    "ai_message": "已根据您的反馈调整了主角性格，现在他更加霸气了。请确认是否满意。"
  },
  "timestamp": "2026-01-23T10:07:00Z"
}
```

---

### 8.6 聊天历史

获取任务的聊天历史。

**客户端发送**

```json
{
  "type": "chat",
  "event": "get_history",
  "data": {
    "task_id": "task_003"
  },
  "timestamp": "2026-01-23T10:08:00Z"
}
```

**服务端响应**

```json
{
  "type": "chat",
  "event": "history",
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
      },
      {
        "role": "system",
        "content": "用户选择作用域：仅当前任务",
        "timestamp": "2026-01-23T10:06:30Z"
      },
      {
        "role": "assistant",
        "content": "已根据您的反馈调整了主角性格，请确认。",
        "timestamp": "2026-01-23T10:07:00Z"
      }
    ]
  },
  "timestamp": "2026-01-23T10:08:01Z"
}
```

---

### 8.7 快捷反馈

预设的快捷反馈选项。

**服务端推送（随预览一起）**

```json
{
  "type": "preview",
  "event": "task_preview",
  "data": {
    "task_id": "task_003",
    /* ... 其他预览数据 ... */
    
    "quick_feedbacks": [
      {
        "id": "more_detail",
        "label": "内容再详细一些",
        "icon": "📝"
      },
      {
        "id": "more_creative",
        "label": "再有创意一点",
        "icon": "✨"
      },
      {
        "id": "shorter",
        "label": "内容太长，精简一下",
        "icon": "✂️"
      },
      {
        "id": "different_style",
        "label": "换一种风格",
        "icon": "🎨"
      }
    ]
  }
}
```

**客户端发送快捷反馈**

```json
{
  "type": "chat",
  "event": "quick_feedback",
  "data": {
    "task_id": "task_003",
    "quick_feedback_id": "more_detail"
  },
  "timestamp": "2026-01-23T10:09:00Z"
}
```

---

## 9. 用户交互事件

### 9.1 需要用户确认

**服务端推送**

```json
{
  "type": "interaction",
  "event": "user_confirmation_required",
  "data": {
    "confirmation_id": "confirm_001",
    "task_id": "task_050",
    "message": "检测到人物关系冲突，是否继续生成？",
    "options": [
      {
        "id": "continue",
        "label": "继续生成",
        "is_default": true
      },
      {
        "id": "fix_manually",
        "label": "手动修复"
      },
      {
        "id": "cancel",
        "label": "取消任务"
      }
    ],
    "timeout": 300              // 超时时间（秒），超时则选择默认
  },
  "timestamp": "2026-01-23T12:00:00Z"
}
```

**客户端响应**

```json
{
  "type": "interaction",
  "event": "user_confirmation_response",
  "data": {
    "confirmation_id": "confirm_001",
    "selected_option": "continue"
  },
  "timestamp": "2026-01-23T12:00:30Z"
}
```

---

### 8.2 需要用户输入

**服务端推送**

```json
{
  "type": "interaction",
  "event": "user_input_required",
  "data": {
    "input_id": "input_001",
    "task_id": "task_001",
    "prompt": "请为主角命名",
    "input_type": "text",
    "default_value": "李逍遥",
    "validation": {
      "min_length": 2,
      "max_length": 10,
      "pattern": "^[\\u4e00-\\u9fa5]+$"  // 仅中文
    },
    "timeout": 600
  },
  "timestamp": "2026-01-23T10:02:00Z"
}
```

**客户端响应**

```json
{
  "type": "interaction",
  "event": "user_input_response",
  "data": {
    "input_id": "input_001",
    "value": "李逍遥"
  },
  "timestamp": "2026-01-23T10:02:30Z"
}
```

---

## 10. 系统通知

### 9.1 警告通知

**服务端推送**

```json
{
  "type": "notification",
  "event": "warning",
  "data": {
    "level": "warning",
    "title": "LLM 调用频率过高",
    "message": "当前调用频率接近限制，建议降低并发任务数",
    "action": {
      "type": "link",
      "label": "查看配置",
      "url": "/config/llm"
    }
  },
  "timestamp": "2026-01-23T12:30:00Z"
}
```

---

### 9.2 错误通知

**服务端推送**

```json
{
  "type": "notification",
  "event": "error",
  "data": {
    "level": "error",
    "title": "会话执行失败",
    "message": "多次重试后仍然失败，已暂停执行",
    "error_code": "MAX_RETRIES_EXCEEDED",
    "action": {
      "type": "button",
      "label": "查看详情",
      "url": "/sessions/sess_123/errors"
    }
  },
  "timestamp": "2026-01-23T13:00:00Z"
}
```

---

### 9.3 信息通知

**服务端推送**

```json
{
  "type": "notification",
  "event": "info",
  "data": {
    "level": "info",
    "title": "小说生成完成",
    "message": "恭喜！您的小说《我的玄幻小说》已生成完成，共50章，125000字",
    "action": {
      "type": "button",
      "label": "导出小说",
      "url": "/sessions/sess_123/export"
    }
  },
  "timestamp": "2026-01-23T15:30:00Z"
}
```

---

## 11. 客户端命令

### 10.1 控制执行

**客户端发送（暂停）**

```json
{
  "type": "command",
  "action": "pause",
  "data": {
    "session_id": "sess_1234567890"
  },
  "timestamp": "2026-01-23T12:00:00Z"
}
```

**服务端确认**

```json
{
  "type": "command",
  "event": "pause_acknowledged",
  "data": {
    "session_id": "sess_1234567890",
    "status": "paused"
  },
  "timestamp": "2026-01-23T12:00:01Z"
}
```

---

**客户端发送（继续）**

```json
{
  "type": "command",
  "action": "resume",
  "data": {
    "session_id": "sess_1234567890"
  },
  "timestamp": "2026-01-23T12:05:00Z"
}
```

---

**客户端发送（停止）**

```json
{
  "type": "command",
  "action": "stop",
  "data": {
    "session_id": "sess_1234567890",
    "save_checkpoint": true
  },
  "timestamp": "2026-01-23T12:10:00Z"
}
```

---

### 10.2 订阅事件

**客户端发送**

```json
{
  "type": "command",
  "action": "subscribe",
  "data": {
    "events": ["task", "content", "llm"],  // 订阅特定事件类型
    "filters": {
      "task_types": ["chapter"],           // 仅章节任务
      "llm_providers": ["doubao"]          // 仅 Doubao 调用
    }
  },
  "timestamp": "2026-01-23T10:00:00Z"
}
```

---

### 10.3 取消订阅

**客户端发送**

```json
{
  "type": "command",
  "action": "unsubscribe",
  "data": {
    "events": ["llm"]
  },
  "timestamp": "2026-01-23T12:00:00Z"
}
```

---

## 12. 连接管理

### 11.1 断线重连

**客户端行为**
1. 检测到连接断开
2. 尝试重连（指数退避）
3. 重连成功后请求同步状态

**客户端发送（请求同步）**

```json
{
  "type": "command",
  "action": "sync_state",
  "data": {
    "last_sequence": 123,      // 最后收到的序列号
    "last_timestamp": "2026-01-23T12:00:00Z"
  },
  "timestamp": "2026-01-23T12:05:00Z"
}
```

**服务端响应（状态同步）**

```json
{
  "type": "sync",
  "event": "state_snapshot",
  "data": {
    "session_id": "sess_1234567890",
    "current_status": "running",
    "current_task": {
      "task_id": "task_052",
      "task_type": "chapter",
      "progress": 35.0
    },
    "missed_events": [
      { /* 错过的事件1 */ },
      { /* 错过的事件2 */ }
    ]
  },
  "timestamp": "2026-01-23T12:05:01Z"
}
```

---

### 11.2 主动断开

**客户端发送**

```json
{
  "type": "command",
  "action": "disconnect",
  "data": {
    "reason": "用户关闭页面"
  },
  "timestamp": "2026-01-23T15:00:00Z"
}
```

**服务端响应**

```json
{
  "type": "connection",
  "event": "disconnected",
  "data": {
    "message": "Connection closed successfully"
  },
  "timestamp": "2026-01-23T15:00:01Z"
}
```

---

## 13. 完整示例

### 12.1 JavaScript 客户端示例

```javascript
class CreativeAutoGPTClient {
  constructor(sessionId, token = null) {
    this.sessionId = sessionId;
    this.token = token;
    this.ws = null;
    this.sequence = 0;
    this.eventHandlers = {};
  }

  connect() {
    const url = `ws://localhost:8000/ws?session_id=${this.sessionId}${
      this.token ? `&token=${this.token}` : ''
    }`;
    
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.startHeartbeat();
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket closed');
      this.stopHeartbeat();
      // 可以在这里实现重连逻辑
    };
  }

  handleMessage(message) {
    this.sequence = message.sequence || this.sequence + 1;
    
    const handler = this.eventHandlers[`${message.type}.${message.event}`];
    if (handler) {
      handler(message.data);
    }
    
    // 通用处理器
    const typeHandler = this.eventHandlers[message.type];
    if (typeHandler) {
      typeHandler(message);
    }
  }

  on(eventPath, handler) {
    this.eventHandlers[eventPath] = handler;
  }

  send(message) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.send({
        type: 'ping',
        timestamp: new Date().toISOString()
      });
    }, 30000);
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
  }

  pause() {
    this.send({
      type: 'command',
      action: 'pause',
      data: { session_id: this.sessionId },
      timestamp: new Date().toISOString()
    });
  }

  resume() {
    this.send({
      type: 'command',
      action: 'resume',
      data: { session_id: this.sessionId },
      timestamp: new Date().toISOString()
    });
  }

  disconnect() {
    this.send({
      type: 'command',
      action: 'disconnect',
      data: { reason: 'User initiated' },
      timestamp: new Date().toISOString()
    });
    this.ws.close();
  }
}

// 使用示例
const client = new CreativeAutoGPTClient('sess_1234567890');

// 监听任务完成事件
client.on('task.task_completed', (data) => {
  console.log('Task completed:', data.task_type);
  updateUI(data);
});

// 监听章节内容流
client.on('content.chapter_content_chunk', (data) => {
  appendContent(data.chapter_id, data.content);
});

// 监听所有任务事件
client.on('task', (message) => {
  console.log('Task event:', message.event);
});

// 连接
client.connect();
```

---

### 12.2 React Hook 示例

```javascript
import { useEffect, useRef, useState } from 'react';

export function useWebSocket(sessionId, token = null) {
  const wsRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);

  useEffect(() => {
    const url = `ws://localhost:8000/ws?session_id=${sessionId}${
      token ? `&token=${token}` : ''
    }`;
    
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setLastMessage(message);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [sessionId, token]);

  const send = (message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  };

  return { isConnected, lastMessage, send };
}

// 使用示例
function NovelGeneration({ sessionId }) {
  const { isConnected, lastMessage, send } = useWebSocket(sessionId);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (lastMessage?.type === 'session' && lastMessage?.event === 'progress_updated') {
      setProgress(lastMessage.data.percentage);
    }
  }, [lastMessage]);

  const handlePause = () => {
    send({
      type: 'command',
      action: 'pause',
      data: { session_id: sessionId },
      timestamp: new Date().toISOString()
    });
  };

  return (
    <div>
      <div>连接状态: {isConnected ? '已连接' : '未连接'}</div>
      <div>进度: {progress}%</div>
      <button onClick={handlePause}>暂停</button>
    </div>
  );
}
```

---

## 14. 错误处理

### 13.1 连接错误

| 错误码 | 说明 | 处理建议 |
|--------|------|---------|
| 1000 | 正常关闭 | 无需处理 |
| 1001 | 服务端主动关闭 | 检查会话状态 |
| 1002 | 协议错误 | 检查消息格式 |
| 1003 | 不支持的数据类型 | 检查消息内容 |
| 1006 | 异常关闭 | 尝试重连 |
| 1008 | 违反策略 | 检查认证信息 |
| 1009 | 消息过大 | 减小消息体积 |
| 1011 | 服务器错误 | 稍后重试 |

---

### 13.2 消息错误

**服务端推送**

```json
{
  "type": "error",
  "event": "message_error",
  "data": {
    "error_code": "INVALID_MESSAGE_FORMAT",
    "message": "Invalid JSON format",
    "original_message": "{ invalid json }"
  },
  "timestamp": "2026-01-23T10:00:00Z"
}
```

---

## 15. 性能优化

### 14.1 消息压缩

对于大型消息（如完整章节内容），服务端可能使用压缩：

```json
{
  "type": "content",
  "event": "chapter_completed",
  "compressed": true,
  "encoding": "gzip",
  "data": "H4sIAAAAAAAA..." // base64 encoded gzip data
}
```

客户端需要解压缩数据。

---

### 14.2 批量消息

服务端可能批量发送多个事件：

```json
{
  "type": "batch",
  "events": [
    { /* 事件1 */ },
    { /* 事件2 */ },
    { /* 事件3 */ }
  ],
  "timestamp": "2026-01-23T10:00:00Z"
}
```

---

## 16. 安全建议

1. **使用 WSS**：生产环境应使用加密的 WebSocket (wss://)
2. **认证令牌**：传递有效的认证令牌
3. **消息验证**：客户端应验证所有接收消息的格式
4. **频率限制**：客户端应限制发送消息的频率
5. **断线重连**：实现指数退避的重连策略

---

*版本: 1.0*  
*最后更新: 2026-01-23*
