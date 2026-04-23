import React, { useState } from 'react'
import axios from 'axios'
import ChatInterface from './components/ChatInterface'

function App() {
  return (
    <div className="h-screen bg-gray-50">
      <ChatInterface />
    </div>
  )
}

export default App
