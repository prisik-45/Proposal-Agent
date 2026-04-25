# 📋 AI Proposal Agent

An intelligent conversational system that generates professional PDF proposals using natural language input. It features session-based memory for real-time iterative modifications.

## ✨ Key Features
- **Conversational UI**: Chat with the AI (ChatGPT-style interface) to build proposals.
- **Smart Memory**: Incremental updates driven by context (e.g., "Change the timeline to 40 days").
- **Dynamic Workflows**: Orchestrates 12-section structured proposals using LangGraph.
- **Automated Delivery**: Real-time PDF generation and automatic Google Drive uploads.

## 🛠️ Stack
- **Backend API**: FastAPI, LangGraph, Groq LLM, Python (`uv` package manager)
- **Frontend UI**: React 18, Tailwind CSS, Vite
- **PDF Engine**: WeasyPrint & Jinja2 Templates

## 🚀 Quick Setup

### 1. Backend 
```bash
# Install dependencies using uv
uv pip install -e .

# Setup environment variables
cp .env.example .env
# Edit .env to add your GROQ_API_KEY and GOOGLE_DRIVE_FOLDER_ID

# Start the API server
uv run python run_api.py
```
*API will run at `http://localhost:8000`*

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
*UI will run at `http://localhost:5173`*

## 💡 Usage Example
1. Start a new session:
> *"Create a proposal for TCS to build an AI chatbot in 60 days, budget ₹40,000-60,000, includes AI model dev • API integration • 3 months support."*
2. Regenerate portions of the proposal by chatting: 
> *"Change the timeline to 45 days and add payment gateways to deliverables."*