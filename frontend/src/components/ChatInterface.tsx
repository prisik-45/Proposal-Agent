import React, { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import Message from './Message'
import ParametersDisplay from './ParametersDisplay'
import { ProposalResponse } from '../types'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello! 👋 I\'m your Proposal Agent. Describe your proposal requirements in natural language, and I\'ll generate a professional PDF proposal for you.\n\nExample: "Create proposal for TechCorp to build an AI agent in 60 days, budget ₹40,000-60,000, includes AI model development • API integration • 3 months support"',
      timestamp: new Date(),
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [extractedParams, setExtractedParams] = useState<any>(null)
  const [currentState, setCurrentState] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
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
    setError(null)

    try {
      // Call the conversational API
      const response = await axios.post('http://localhost:8000/proposals/converse', {
        session_id: sessionId,
        user_message: input
      })

      const result = response.data

      // Update session ID on first message
      if (!sessionId && result.session_id) {
        setSessionId(result.session_id)
      }

      // Store results
      setExtractedParams(result.current_params)
      setCurrentState(result.current_state)

      // Add assistant message with result
      let assistantContent = ''
      
      if (result.success) {
        assistantContent = `${result.message}\n\n`
        
        if (result.is_modification) {
          assistantContent += `📝 **Modified Fields:**\n`
          Object.entries(result.changes_detected).forEach(([key, value]) => {
            assistantContent += `- ${key}: ${value}\n`
          })
        }
        
        if (result.drive_link) {
          assistantContent += `\n📥 [Download PDF from Google Drive](${result.drive_link})`
        }
      } else {
        assistantContent = `❌ Error: ${result.error || 'Unknown error occurred'}`
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to process request'
      setError(errorMessage)

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `❌ Error: ${errorMessage}`,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } finally {
      setLoading(false)
    }
  }

      // Store results
      setExtractedParams(result.extracted_params)
      setProposalResult(result)

      // Add assistant message with result
      let assistantContent = ''
      
      if (result.success) {
        assistantContent = `**Proposal Generated Successfully!**\n\nYour proposal has been created and saved to Google Drive.\n\n📊 **Extracted Parameters:**\n- Client: ${result.extracted_params?.client_business_name || 'N/A'}\n- Timeline: ${result.extracted_params?.timeline_days || 'N/A'} days\n- Budget: ₹${result.extracted_params?.price_min || 'N/A'} - ₹${result.extracted_params?.price_max || 'N/A'}`
      } else {
        assistantContent = `**Failed to Generate Proposal**\n\nError: ${result.error || 'Unknown error occurred'}`
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to generate proposal'
      setError(errorMessage)

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: ` Error: ${errorMessage}`,
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
      <div className="border-b border-gray-800 bg-gray-950 px-6 py-4">
        <h1 className="text-2xl font-bold text-white">Proposal Agent</h1>
        <p className="text-sm text-gray-400">By Tarkshy Consultancy Services</p>
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
                className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-white font-medium py-3 px-6 rounded-lg transition-colors"
              >
                {loading ? 'Generating...' : 'Send'}
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar - Parameters and Result */}
        {(extractedParams || currentState) && (
          <div className="w-80 border-l border-gray-800 overflow-y-auto bg-gray-950">
            <div className="p-4 space-y-4">
              {/* Session Info */}
              {sessionId && (
                <div className="text-xs text-gray-400 truncate">
                  Session: {sessionId.substring(0, 12)}...
                </div>
              )}
              
              {/* Parameters */}
              {extractedParams && (
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                  <h3 className="font-semibold text-sm text-gray-100 mb-3">📋 Current Parameters</h3>
                  <div className="space-y-2 text-xs">
                    {extractedParams.client_business_name && (
                      <div>
                        <p className="text-gray-400">Client</p>
                        <p className="text-gray-100 font-medium">{extractedParams.client_business_name}</p>
                      </div>
                    )}
                    {extractedParams.timeline_days && (
                      <div>
                        <p className="text-gray-400">Timeline</p>
                        <p className="text-gray-100 font-medium">{extractedParams.timeline_days} days</p>
                      </div>
                    )}
                    {(extractedParams.price_min || extractedParams.price_max) && (
                      <div>
                        <p className="text-gray-400">Budget</p>
                        <p className="text-gray-100 font-medium">
                          ₹{extractedParams.price_min} - ₹{extractedParams.price_max}
                        </p>
                      </div>
                    )}
                    {extractedParams.client_requirements && (
                      <div>
                        <p className="text-gray-400">Requirements</p>
                        <p className="text-gray-300 line-clamp-2">{extractedParams.client_requirements}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatInterface
