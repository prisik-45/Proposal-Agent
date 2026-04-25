import React from 'react'

interface MessageProps {
  message: {
    id: string
    type: 'user' | 'assistant'
    content: string
    timestamp: Date
    pdfUrl?: string | null
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
          <div className="space-y-3">
            <div className="text-sm whitespace-pre-wrap break-words">
              {message.content}
            </div>
            {message.pdfUrl && (
              <a
                href={message.pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center rounded-md bg-gray-700 px-3 py-2 text-xs font-medium text-white hover:bg-gray-600 transition-colors"
              >
                View PDF
              </a>
            )}
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
