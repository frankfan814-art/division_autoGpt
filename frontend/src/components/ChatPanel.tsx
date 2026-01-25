/**
 * ChatPanel component for user feedback with quick actions and scope selection
 */

import { useState, useRef, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { ScopeSelector, ScopeOption } from './ScopeSelector';

interface ChatPanelProps {
  sessionId: string | null;
}

interface QuickFeedback {
  id: string;
  label: string;
  icon: string;
}

const quickFeedbacks: QuickFeedback[] = [
  { id: 'more_detail', label: '太简略', icon: '📝' },
  { id: 'too_long', label: '太冗长', icon: '✂️' },
  { id: 'tone_issue', label: '风格不对', icon: '🎨' },
  { id: 'logic_issue', label: '逻辑问题', icon: '🤔' },
];

const scopeOptions: ScopeOption[] = [
  {
    id: 'current_task',
    label: '仅当前任务',
    description: '只修改当前任务的内容，不影响其他部分',
    isDefault: true,
  },
  {
    id: 'future',
    label: '当前及后续任务',
    description: '修改当前任务，并影响后续相关内容的生成',
    warning: '会影响后续内容的连贯性',
  },
  {
    id: 'global',
    label: '全局设定',
    description: '修改整体创作设定，可能需要重新规划大纲',
    warning: '需要重新规划，可能影响已生成的内容',
  },
];

export const ChatPanel = ({ sessionId }: ChatPanelProps) => {
  const { messages, sendMessage, sendQuickFeedback, isLoading } = useChat(sessionId);
  const [input, setInput] = useState('');
  const [showScopeSelector, setShowScopeSelector] = useState(false);
  const [pendingMessage, setPendingMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !sessionId) return;

    // 显示作用域选择器（如果需要）
    setPendingMessage(input);
    setShowScopeSelector(true);
  };

  const handleScopeSelect = async (scope: string) => {
    setShowScopeSelector(false);
    
    try {
      await sendMessage(pendingMessage, scope as 'current_task' | 'chapter' | 'all');
      setInput('');
      setPendingMessage('');
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  };

  const handleQuickFeedback = async (feedbackId: string) => {
    if (!sessionId) return;
    
    try {
      await sendQuickFeedback(feedbackId);
    } catch (err) {
      console.error('Failed to send quick feedback:', err);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="border-b p-4">
        <h2 className="text-lg font-semibold text-gray-900">用户反馈</h2>
        <p className="text-sm text-gray-500 mt-1">
          向AI提供反馈，指导创作方向
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <svg className="w-12 h-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p>暂无反馈记录</p>
            <p className="text-sm mt-2">输入反馈内容，帮助AI更好地理解您的需求</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                <p className={`text-xs mt-1 ${
                  message.role === 'user' ? 'text-blue-200' : 'text-gray-500'
                }`}>
                  {new Date(message.timestamp).toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Feedbacks */}
      <div className="border-t p-3 bg-white">
        <div className="text-xs font-medium text-gray-600 mb-2">📊 快捷反馈</div>
        <div className="grid grid-cols-2 gap-2">
          {quickFeedbacks.map((fb) => (
            <button
              key={fb.id}
              onClick={() => handleQuickFeedback(fb.id)}
              disabled={!sessionId || isLoading}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors border border-gray-200"
            >
              <span>{fb.icon}</span>
              <span className="text-gray-700">{fb.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="border-t p-4 bg-white space-y-3">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的反馈意见..."
            disabled={!sessionId || isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || !sessionId || isLoading}
            isLoading={isLoading}
          >
            发送
          </Button>
        </div>
      </div>

      {/* Scope Selector Modal */}
      <ScopeSelector
        isOpen={showScopeSelector}
        options={scopeOptions}
        onSelect={handleScopeSelect}
        onCancel={() => {
          setShowScopeSelector(false);
          setPendingMessage('');
        }}
      />
    </div>
  );
};
