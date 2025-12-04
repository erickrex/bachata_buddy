// ChatMessages Component
// Displays user and assistant messages in a chat interface
// Auto-scrolls to latest message

import { useEffect, useRef } from 'react';

function ChatMessages({ messages = [] }) {
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  
  // Auto-scroll to latest message when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  if (messages.length === 0) {
    return null;
  }
  
  return (
    <div 
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-6 space-y-4"
      style={{ maxHeight: '500px' }}
    >
      {messages.map((message, index) => (
        <MessageBubble 
          key={index} 
          message={message} 
          isLast={index === messages.length - 1}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}

function MessageBubble({ message, isLast }) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isSystem = message.role === 'system';
  
  return (
    <div 
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div 
        className={`
          max-w-[80%] rounded-2xl px-4 py-3 shadow-sm
          ${isUser ? 'bg-purple-600 text-white' : ''}
          ${isAssistant ? 'bg-gray-100 text-gray-900' : ''}
          ${isSystem ? 'bg-blue-50 text-blue-900 border border-blue-200' : ''}
        `}
      >
        {/* Message Header */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold opacity-70">
              {isAssistant ? '🤖 Assistant' : '💡 System'}
            </span>
          </div>
        )}
        
        {/* Message Content */}
        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
        
        {/* Timestamp */}
        {message.timestamp && (
          <div className={`text-xs mt-1 ${isUser ? 'text-purple-200' : 'text-gray-500'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatMessages;
