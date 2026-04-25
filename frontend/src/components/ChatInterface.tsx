import React, { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import Message from './Message'
import ParametersDisplay from './ParametersDisplay'
import { ProposalConversationResponse, ExtractedParams } from '../types'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const createSessionId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `session-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello. I am your Proposal Agent. Share the client name, requirement, timeline, budget range, and deliverables, and I will prepare the proposal.',
      timestamp: new Date(),
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(createSessionId)
  const [extractedParams, setExtractedParams] = useState<ExtractedParams | null>(null)
  const [conversationResult, setConversationResult] = useState<ProposalConversationResponse | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim()) return

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await axios.post('/api/proposals/converse', {
        user_input: input,
        session_id: sessionId,
      })

      const result: ProposalConversationResponse = response.data
      setConversationResult(result)
      setExtractedParams(result.resolved_params || null)

      let assistantContent = ''
      if (result.success) {
        const changedText = result.changed_fields?.length
          ? `\n\nChanged fields:\n- ${result.changed_fields.join('\n- ')}`
          : ''

        assistantContent = `${result.message}${changedText}`
      } else {
        assistantContent = `Failed to update proposal.\n\nError: ${result.error || 'Unknown error occurred'}`
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to update proposal'

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `Error: ${errorMessage}`,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="flex h-full flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 bg-gray-950 px-6 py-4">
        <div>
          <h1 className="text-2xl text-white">Proposal Agent</h1>
          <p className="text-sm text-gray-400">By Tarkshy Consultancy Services</p>
        </div>
        <img
          src="/final_logo.png"
          alt="Tarkshy"
          className="h-14 w-14 object-contain"
        />
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map(message => (
              <Message key={message.id} message={message} />
            ))}
            {loading && (
              <div className="flex items-center justify-center py-4">
                <div className="flex space-x-2">
                  <div className="h-3 w-3 rounded-full bg-gray-500 animate-bounce"></div>
                  <div className="h-3 w-3 rounded-full bg-gray-500 animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="h-3 w-3 rounded-full bg-gray-500 animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-800 bg-gray-900 p-6">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Describe your proposal requirements..."
                disabled={loading}
                className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-600 disabled:bg-gray-700"
              />
              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim()}
                className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-white py-3 px-6 rounded-lg transition-colors"
              >
                {loading ? 'Generating...' : 'Send'}
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar - Parameters and Result */}
        {(extractedParams || conversationResult) && (
          <div className="w-80 border-l border-gray-800 overflow-y-auto bg-gray-950">
            <ParametersDisplay 
              params={extractedParams} 
              result={conversationResult}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatInterface
