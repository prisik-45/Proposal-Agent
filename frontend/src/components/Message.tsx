import React from 'react'
import Markdown from 'react-markdown'

interface MessageProps {
  message: {
    id: string
    type: 'user' | 'assistant'
    content: string
    timestamp: Date
  }
}

const Message: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.type === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-md rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-gray-700 text-white'
            : 'bg-gray-800 text-gray-100'
        }`}
      >
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <div className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </div>
        )}
        <p className={`text-xs mt-2 ${isUser ? 'text-gray-300' : 'text-gray-400'}`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  )
}

export default Message
