# 已知问题与解决方案

本文档记录项目开发过程中遇到的常见问题及其解决方案，避免重复踩坑。

---

## 问题索引

1. [任务列表显示为空](#1-任务列表显示为空)
2. [任务不自动启动（卡在等待状态）](#2-任务不自动启动卡在等待状态)
3. [PreviewPanel Tab栏过长挤压右侧](#3-previewpanel-tab栏过长挤压右侧)
4. [生成内容为学术论文而非小说](#4-生成内容为学术论文而非小说)

---

## 1. 任务列表显示为空

### 问题描述
- 任务正在执行，但前端任务列表一直显示空白
- WebSocket收到task事件，但UI不更新

### 根本原因
`useTasks` hook使用 `setTasks()` 直接替换整个任务数组，导致WebSocket添加的任务被API返回的空数组覆盖。

### 解决方案
**文件**: `frontend/src/hooks/useTask.ts`

修改前:
```typescript
const { data: tasks, isLoading, error } = useQuery({
  queryKey: ['tasks', sessionId],
  queryFn: () => sessionId ? getTasks(sessionId) : Promise.resolve([]),
  enabled: !!sessionId,
});

useEffect(() => {
  if (tasks) {
    setTasks(tasks); // ❌ 替换整个数组，丢失WebSocket数据
  }
}, [tasks, setTasks]);

return { tasks, isLoading, error };
```

修改后:
```typescript
const { data: tasks, isLoading, error } = useQuery({
  queryKey: ['tasks', sessionId],
  queryFn: () => sessionId ? getTasks(sessionId) : Promise.resolve([]),
  enabled: !!sessionId,
});

useEffect(() => {
  if (tasks) {
    tasks.forEach(task => upsertTask(task)); // ✅ 合并数据
  }
}, [tasks, upsertTask]);

return { tasks: storeTasks, isLoading, error }; // ✅ 返回store数据
```

### 影响范围
- 前端任务列表显示
- PreviewPanel tab显示

### 修复日期
2026-01-24

---

## 2. 任务不自动启动（卡在等待状态）

### 问题描述
- 创建会话后，任务一直显示"等待任务启动..."
- WebSocket已订阅，但没有发送start事件
- 日志显示subscribe成功，但无start日志

### 根本原因
**文件**: `frontend/src/pages/Workspace/Workspace.tsx`

有三个问题：

**问题1: 变量引用错误**
```typescript
const hasStarted = sessionId ? hasStartedRef.current[sessionId] : false;

useEffect(() => {
  if (!sessionId || hasStarted) return; // ❌ Bug在这里！
  
  hasStartedRef.current[sessionId] = true;
  // ... start logic
}, [sessionId, hasStarted, toast]); // ❌ hasStarted在依赖数组中会导致问题
```

**问题2: WebSocket未连接就发送消息**
```typescript
const startSession = async () => {
  const ws = getWebSocketClient();
  await new Promise(resolve => setTimeout(resolve, 1000)); // ❌ 固定等待1秒，不保证连接成功
  
  ws.send({ event: 'subscribe', session_id: sessionId }); // ❌ 可能此时WebSocket还在CONNECTING状态
  ws.send({ event: 'start', session_id: sessionId }); // ❌ 消息被丢弃，返回false
};
```

**问题3: React StrictMode下setTimeout被清除**
```typescript
// 在setTimeout中发送start事件
startTimeout = setTimeout(() => {
  if (!mounted) return;  // ❌ StrictMode会在500ms内卸载组件，mounted变为false
  ws.send({ event: 'start', ... });
}, 500);

// cleanup函数
return () => {
  mounted = false;  // ❌ StrictMode立即执行这个
  clearTimeout(startTimeout);  // ❌ start事件被取消！
};
```

问题分析:
1. **变量命名混淆**: `hasStarted` 是从ref读取的值，但在依赖数组中使用
2. **WebSocket时序问题**: 
   - 用户创建session后立即导航到workspace
   - useEffect等待1秒后尝试发送
   - 但WebSocket可能仍在CONNECTING状态（不是OPEN）
   - `ws.send()` 检查readyState，返回false但没有处理错误
3. **StrictMode双重渲染**:
   - React StrictMode会执行两次effect（mount-unmount-mount）
   - 第一次执行：发送subscribe，设置setTimeout
   - cleanup立即执行：mounted=false，clearTimeout
   - 第二次执行：hasStartedRef已经是true，跳过
   - 结果：subscribe发了，但start在cleanup时被取消！

### 解决方案

**最终方案: 同步发送subscribe和start，不使用setTimeout**
```typescript
const hasStartedRef = useRef<Record<string, boolean>>({});

useEffect(() => {
  if (!sessionId) return;
  
  // ✅ 直接在effect内部读取和判断
  if (hasStartedRef.current[sessionId]) {
    console.log('Session already started, skipping');
    return;
  }
  
  // Mark as started immediately
  hasStartedRef.current[sessionId] = true;
  
  let mounted = true;

  const startSession = async () => {
    try {
      const ws = getWebSocketClient();
      
      // ✅ 等待WebSocket连接成功（最多10秒）
      const maxWait = 10000;
      const startTime = Date.now();
      
      while (!ws.isConnected() && (Date.now() - startTime < maxWait)) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      if (!ws.isConnected()) {
        throw new Error('WebSocket connection timeout');
      }
      
      if (!mounted) return;

      // ✅ 检查发送结果
      const subscribeSent = ws.send({ event: 'subscribe', session_id: sessionId });
      if (!subscribeSent) {
        throw new Error('Failed to send subscribe event');
      }

      // ✅ 立即发送start，不用setTimeout（避免StrictMode问题）
      const startSent = ws.send({ event: 'start', session_id: sessionId });
      if (!startSent) {
        toast.error('启动失败，请刷新页面重试');
      }
    } catch (error) {
      console.error('Failed to start session:', error);
      toast.error('启动会话失败，请刷新重试');
    }
  };

  startSession();

  return () => {
    mounted = false;
    // ✅ 不需要clearTimeout了
  };
}, [sessionId, toast]); // ✅ 只依赖sessionId和toast
```

### 推荐方案
最终方案，原因：
- 避免不必要的re-render
- Ref更适合存储"启动标志"这种不影响UI的状态
- **等待WebSocket连接确保消息不会丢失**
- **subscribe和start同步发送，避免StrictMode清除setTimeout**
- 检查发送结果，失败时有错误提示
- 更简单，减少state管理复杂度

### 关键改进
1. **主动等待WebSocket连接**: 使用`while`循环轮询`isConnected()`，最多等待10秒
2. **检查发送结果**: `ws.send()`返回false时抛出错误
3. **同步发送**: subscribe和start连续发送，不使用setTimeout
4. **避免StrictMode问题**: 不依赖setTimeout和cleanup中的clearTimeout
5. **错误处理**: 显示toast提示用户刷新重试
6. **超时保护**: 10秒后仍未连接则报错，避免无限等待

### WebSocketClient 新增方法
```typescript
// frontend/src/api/websocket.ts

isConnected(): boolean {
  return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
}

send(data: any): boolean {
  if (this.ws && this.ws.readyState === WebSocket.OPEN) {
    this.ws.send(JSON.stringify(data));
    return true;
  }
  console.warn('WebSocket not ready, readyState:', this.ws?.readyState);
  return false;
}
```

### 影响范围
- 所有新创建的会话自动启动
- 会话切换时的重复启动防护

### 修复日期
2026-01-24

---

## 3. PreviewPanel Tab栏过长挤压右侧

### 问题描述
- 任务很多时，tab按钮挤在一起或溢出
- 右侧Chat面板被挤压变窄

### 解决方案
**文件**: `frontend/src/components/PreviewPanel.tsx`

```tsx
<div className="border-b bg-gray-50 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
  <div className="flex items-center gap-1 p-2 min-w-min">
    {tasks.map((task) => (
      <button
        className="... flex-shrink-0" // ✅ 防止按钮被压缩
      >
        {getTaskTypeLabel(task.task_type)}
        {getStatusBadge(task)}
      </button>
    ))}
  </div>
</div>
```

关键点:
- 外层添加 `overflow-x-auto` 启用横向滚动
- 内层使用 `min-w-min` 允许内容自然宽度
- 按钮添加 `flex-shrink-0` 防止压缩
- 添加滚动条样式类（已在全局CSS定义）

### 影响范围
- PreviewPanel UI

### 修复日期
2026-01-24

---

## 4. 生成内容为学术论文而非小说

### 问题描述
- 生成的"风格元素"、"大纲"等包含学术论文格式
- 示例: "I. Structural Anchor: Vacuum Decay Front as Narrative Metric Tensor φ₀ = 246.2 GeV"
- 评估系统让这类内容通过，没有拒绝

### 根本原因
提示词中缺少对小说写作的强调，LLM默认生成学术性内容

### 解决方案（第一版）
**文件**: 
- `src/creative_autogpt/core/evaluator.py`
- `src/creative_autogpt/core/loop_engine.py`
- `src/creative_autogpt/core/task_planner.py`

添加严格的小说写作要求和学术内容拒绝规则。

### 后续优化（科幻小说特例）
**问题**: 第一版过于严格，连科幻小说的科学设定都被拒绝

**用户需求**: 
- 允许硬科幻内容（参考《三体》《流浪地球》）
- 但必须通俗易懂，面向大众读者
- 拒绝纯学术论文、公式推导

**解决方案（第二版）**:

1. **evaluator.py** - 添加科幻例外规则:
```python
📖 科幻小说特殊规则（参考《三体》《流浪地球》标准）：
- ✅ 允许：适度的科学概念、技术设定、必要科学术语（通过故事呈现）
- ✅ 允许：用通俗易懂的方式解释科学原理（像刘慈欣的写法）
- ❌ 禁止：堆砌复杂公式、学术论文式的理论推导
- ❌ 禁止：纯技术文档式的描述、缺乏故事性
- ❌ 禁止：面向专业研究者的学术写作风格

核心标准：科学设定服务于故事，而不是展示学术研究。
```

2. **loop_engine.py** - 目标段落和输出要求:
```python
📚 写作标准（参考《三体》《流浪地球》等大众科幻作品）：
✅ 必须做到：
- 故事性优先：一切设定服务于故事情节
- 通俗易懂：面向大众读者，不是专业研究者
- 科学融入：科技设定通过对话、情节自然呈现
- 文学性强：使用生动的叙事语言和文学手法

❌ 严格禁止：
- 学术论文格式（摘要、引言、方法论、参考文献等）
- 纯公式推导或数学方程式罗列
- 面向专业研究者的学术写作风格

💡 科幻小说要点：
- 科学设定要用故事讲出来（像刘慈欣的写法）
- 技术细节融入对话、情节、场景描写中
- 复杂概念用通俗易懂的方式解释
- 目标读者是科幻爱好者，不是物理学家
```

### 质量标准
- ✅ **好的硬科幻**: 科学概念融入故事，通过角色对话/行动展现，读者能理解
- ❌ **不合格**: 罗列公式、学术推导、技术文档、专业术语堆砌

### 参考作品
- 刘慈欣《三体》系列
- 刘慈欣《流浪地球》
- 特点：复杂科学原理用故事讲述，面向科幻爱好者而非物理学家

### 影响范围
- 所有任务的生成内容
- 评估标准

### 修复日期
- 第一版: 2026-01-24
- 第二版(科幻优化): 2026-01-24

---

## 常见排查步骤

### WebSocket连接问题
```bash
# 检查服务状态
ps aux | grep -E "uvicorn|vite" | grep -v grep

# 查看后端日志
tail -f logs/creative_autogpt.log

# 检查WebSocket连接
# 浏览器控制台应显示: WebSocket client connected
```

### 任务不执行
1. 检查WebSocket是否订阅: 日志应显示 "Subscribed to session"
2. 检查是否发送start事件: 日志应显示 "Start event sent"
3. 检查后端是否收到start: 日志应显示 "handle_start"
4. 检查session状态: GET /sessions/:id 看status字段

### 前端状态调试
```javascript
// 浏览器控制台
useTaskStore.getState().tasks // 查看任务列表
useSessionStore.getState().currentSession // 查看当前会话
```

---

## 文档维护
- 每次修复bug后，及时更新此文档
- 包含: 问题描述、根本原因、解决方案、影响范围、修复日期
- 代码示例要完整，方便直接参考
