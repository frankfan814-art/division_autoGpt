# 测试会话自动启动功能

## 测试步骤

1. **打开浏览器控制台**
   - 访问 http://localhost:4173
   - 按F12打开开发者工具
   - 切换到Console标签

2. **创建新会话**
   - 点击"创建新项目"
   - 填写小说信息（任意）
   - 点击"创建项目"

3. **观察控制台日志**

   应该看到以下日志（按顺序）：
   ```
   WebSocket connected
   Waiting for WebSocket connection...
   WebSocket ready, starting session: <session-id>
   Subscribe event sent: true
   Start event sent for session: <session-id> success: true
   ```

4. **观察后端日志**

   应该看到以下事件（按顺序）：
   ```
   WebSocket event from <client-id>: connect
   WebSocket event from <client-id>: subscribe
   🔔 Subscribe request from <client-id> for session <session-id>
   ✅ Subscribed to session <session-id>
   WebSocket event from <client-id>: start
   🎬 Start request for session <session-id>
   LoopEngine started for session <session-id>
   📋 Task started: 风格元素
   ```

5. **观察UI变化**

   - 页面应该自动跳转到workspace
   - 右侧进度条应该显示"正在执行: 风格元素"
   - 左侧预览面板应该出现"🎨 风格元素"的tab
   - Tab应该显示蓝色"执行中"徽章并有脉冲动画

## 预期结果

✅ **成功标志**:
- 控制台没有错误
- Subscribe和start事件都返回true
- 后端收到subscribe和start事件
- 第一个任务开始执行
- UI实时更新

❌ **失败标志**:
- 控制台显示"WebSocket not ready"警告
- Subscribe或start返回false
- 后端没有收到事件
- UI一直显示"等待任务启动..."

## 常见问题

### 问题1: Subscribe返回false
**原因**: WebSocket连接太慢
**解决**: 增加maxWait超时时间（当前10秒）

### 问题2: 等待超时
**日志**: `WebSocket connection timeout`
**原因**: 网络问题或后端未启动
**解决**: 检查后端服务状态，刷新页面重试

### 问题3: Start发送失败
**日志**: `Failed to send start event - WebSocket not ready`
**原因**: WebSocket在500ms内断开连接
**解决**: 检查网络稳定性，查看后端错误日志

## 调试工具

### 浏览器控制台命令
```javascript
// 检查WebSocket状态
const ws = getWebSocketClient();
ws.isConnected(); // 应该返回true

// 手动发送start事件
ws.send({ event: 'start', session_id: '<your-session-id>' });

// 查看任务状态
useTaskStore.getState().tasks;

// 查看进度
useTaskStore.getState().progress;
```

### 后端日志过滤
```bash
# 查看WebSocket事件
tail -f logs/creative_autogpt.log | grep "WebSocket event"

# 查看任务启动
tail -f logs/creative_autogpt.log | grep "Task started"

# 查看subscribe/start
tail -f logs/creative_autogpt.log | grep -E "Subscribe|Start request"
```

## 性能指标

- **WebSocket连接时间**: < 1秒
- **从创建到启动**: < 3秒
- **第一个任务开始**: < 5秒
- **首次UI更新**: < 6秒

## 修复历史

**2026-01-24**: 修复WebSocket未连接就发送消息的问题
- 添加`isConnected()`检查
- 主动等待连接（最多10秒）
- 检查send返回值并处理失败情况
