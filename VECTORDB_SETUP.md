# VectorDB + LLM Conversation Memory System

## 🧠 Architecture Overview

The Proposal Agent now uses **Pinecone VectorDB + LLM** for intelligent conversational memory. This enables ChatGPT-like interactions where the bot understands context and can make targeted modifications to proposals.

```
User Input
    ↓
Session Memory (Pinecone)
    ↓
LLM Understanding (Modification Detection)
    ↓
Targeted Regeneration (Only affected sections)
    ↓
Drive Upload + Context Storage
```

---

## 🔧 Setup Instructions

### Step 1: Get Pinecone API Key

1. Go to [Pinecone Dashboard](https://console.pinecone.io/)
2. Sign up for a free account (if needed)
3. Create a new project or use default
4. Get your **API Key**
5. Create an **Index**:
   - Name: `proposal-agent`
   - Dimension: `1536` (for embeddings)
   - Metric: `cosine`
   - Environment: `us-east-1` (or your preferred region)

### Step 2: Update `.env` File

Add these lines to your `.env` file:

```bash
# Pinecone Vector Memory
PINECONE_API_KEY=your_api_key_here
PINECONE_INDEX_NAME=proposal-agent
PINECONE_ENVIRONMENT=us-east-1
PINECONE_NAMESPACE=default
```

### Step 3: Install Dependencies

```bash
uv sync
# or if you already have it installed:
pip install pinecone-client>=3.0.0
```

---

## 🚀 API Endpoints

### 1. Start New Session
```bash
POST /proposals/session/start

Response:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Conversational session started",
  "initial_prompt": "Welcome! Describe your proposal..."
}
```

### 2. Conversational Proposal (Main Endpoint)
```bash
POST /proposals/converse

Request:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",  // Optional on first message
  "user_message": "Create proposal for TechCorp to build AI agent in 60 days..."
}

Response:
{
  "success": true,
  "message": "✅ Proposal generated successfully!",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_modification": false,
  "changes_detected": {},
  "current_params": { /* all proposal parameters */ },
  "current_state": { /* full proposal state */ },
  "drive_link": "https://drive.google.com/..."
}
```

### 3. Get Session History
```bash
GET /proposals/session/{session_id}/history

Response:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_count": 3,
  "history": [
    {
      "turn_number": 1,
      "user_message": "Create proposal for...",
      "assistant_response": "✅ Proposal generated!",
      "timestamp": "2024-04-23T10:30:00"
    },
    ...
  ],
  "current_proposal_state": { /* latest state */ }
}
```

### 4. Delete Session
```bash
DELETE /proposals/session/{session_id}

Response:
{
  "success": true,
  "message": "Session deleted"
}
```

---

## 💬 Usage Examples

### Example 1: Initial Proposal Generation

```bash
curl -X POST http://localhost:8000/proposals/converse \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Create proposal for ABC Company to build website in 45 days, budget ₹30,000-50,000, includes full development • domain setup • 3 months support"
  }'
```

**Bot Response:**
```
✅ Proposal generated successfully! You can now make modifications like 'Change timeline to X days' or 'Update budget to Y'

Session ID: 550e8400-e29b-41d4-a716-446655440000
Drive Link: https://drive.google.com/...
```

### Example 2: Modification (Change Timeline)

```bash
curl -X POST http://localhost:8000/proposals/converse \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_message": "Change timeline to 60 days"
  }'
```

**Bot Response:**
```
✅ Got it! ⏱️ Timeline updated to 60 days
Regenerated proposal with updates!

Modified Fields:
- timeline_days: 60

Drive Link: https://drive.google.com/...
```

### Example 3: Modification (Update Budget)

```bash
curl -X POST http://localhost:8000/proposals/converse \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_message": "Increase budget to 40k - 70k"
  }'
```

**Bot Response:**
```
✅ Understood. 💰 Budget updated to ₹40000 - ₹70000
Regenerating proposal...
```

---

## 🧠 How It Works

### Conversation Flow

```
Turn 1: User provides initial proposal details
├─ Extract parameters (client, timeline, budget, etc.)
├─ Generate full proposal
├─ Store in Pinecone with embeddings
└─ Return drive link

Turn 2: User says "Change timeline to 40 days"
├─ Retrieve conversation context from Pinecone
├─ LLM understands: "timeline_days = 40"
├─ Update only that field
├─ Regenerate affected sections
├─ Store new turn in Pinecone
└─ Return updated proposal

Turn 3: User says "Actually, make it 3 months"
├─ Find previous timeline references (40 days, 60 days original)
├─ LLM converts "3 months" → 90 days
├─ Update and regenerate
└─ Return final proposal
```

### Memory System

**Pinecone Storage Structure:**
```
Vector ID: {session_id}_turn_{turn_number}_{random_id}

Metadata:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_number": "1",
  "timestamp": "2024-04-23T10:30:00",
  "user_message": "Create proposal for...",
  "assistant_response": "✅ Proposal generated!",
  "proposal_params": {...},  // JSON stringified
  "proposal_state": {...},   // Full proposal state
  "type": "conversation_turn"
}
```

**Semantic Search:**
- When user makes a modification, the system searches Pinecone for similar previous turns
- Uses embeddings to find related context
- Passes relevant context to LLM for better understanding

---

## 🔍 Modification Detection

### How LLM Understands Changes

The system uses two-tier detection:

**Tier 1: Keyword Extraction**
- Regex patterns for numbers: `\d+` (timeline, budget)
- Currency patterns: `₹\d+k?`
- Keywords: "change", "update", "modify", "increase"

**Tier 2: LLM Understanding** (if Tier 1 fails)
- Passes conversation context to Groq LLM
- LLM identifies changed fields
- LLM converts natural language to values ("3 months" → 90 days)

Example modifications supported:
```
"Change timeline to 40 days" → timeline_days: 40
"Increase budget to ₹80k" → price_max: "80000"
"Update client to NewCorp" → client_business_name: "NewCorp"
"Add mobile app to deliverables" → includes_text: (appended)
"Make it 3 months" → timeline_days: 90
```

---

## 🎯 Key Features

### 1. **Session Continuity**
- Each conversation gets a unique `session_id`
- All turns stored in Pinecone with full context
- Can retrieve history anytime

### 2. **Smart Modification Detection**
- Understands what fields changed
- Regenerates only affected sections
- Maintains consistency across turns

### 3. **Semantic Search**
- Finds similar previous turns
- Provides context to LLM
- Better understanding of user intent

### 4. **LLM Context Awareness**
- Passes conversation history to Groq
- Understands references to previous statements
- Handles ambiguous inputs better

### 5. **Drive Integration**
- Each modification uploads new PDF
- Maintains history of all versions
- Always provides download link

---

## 📝 Frontend Integration

The React frontend automatically:

1. **Creates session on first message**
   - Session ID stored in component state
   - Displayed in sidebar (first 12 chars)

2. **Tracks modifications**
   - Shows "Modified Fields" when changes detected
   - Displays emoji indicators (⏱️ timeline, 💰 budget)

3. **Maintains conversation flow**
   - Dark theme (ChatGPT style)
   - Message history with timestamps
   - Real-time parameter display in sidebar

4. **Handles drive links**
   - Direct links to PDFs in messages
   - Easy download/sharing

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required for Pinecone
PINECONE_API_KEY=                    # Your Pinecone API key
PINECONE_INDEX_NAME=proposal-agent   # Index name (create in Pinecone)
PINECONE_ENVIRONMENT=us-east-1       # Pinecone region
PINECONE_NAMESPACE=default            # Namespace for data isolation

# For LLM (already configured)
GROQ_API_KEY=                        # Groq API key
GROQ_MODEL=mixtral-8x7b-32768        # Model for understanding modifications
```

### Scaling Considerations

**For Production:**
- Pinecone Serverless (auto-scaling)
- Namespaces for different clients
- Vector caching for common queries
- Session cleanup after 30 days

**For Development:**
- Use free Pinecone tier (1GB storage)
- Local testing with session memories

---

## 🚨 Troubleshooting

### Pinecone Connection Error
```
Error: "PINECONE_API_KEY not set"
```
**Solution:** Add `PINECONE_API_KEY` to `.env` file

### Index Not Found
```
Error: "Index proposal-agent not found"
```
**Solution:** 
1. Create index in Pinecone dashboard
2. Wait 30 seconds for index to be ready
3. Restart API server

### LLM Understanding Issues
```
Error: "Could not parse modification"
```
**Solution:** 
- Check Groq API key
- Ensure natural language is clear
- Try being more specific: "Change timeline to 45 days" instead of "Make it longer"

### Session Memory Not Persisting
```
- Session works but history lost after restart
```
**Note:** By design, in-memory vectors are lost on restart. For production, enable Pinecone persistence.

---

## 📚 Files Reference

- `src/pinecone_memory.py` - Pinecone integration & vector storage
- `src/conversation_manager.py` - LLM-based modification understanding  
- `src/api.py` - Conversational endpoints (`/proposals/converse`, etc.)
- `frontend/src/components/ChatInterface.tsx` - React UI for conversations

---

## 🔮 Future Enhancements

- [ ] Multi-user collaboration on same proposal
- [ ] Proposal version control with diffs
- [ ] A/B testing different proposals
- [ ] Advanced analytics on modification patterns
- [ ] Voice-to-text modification support
- [ ] Batch modifications from CSV

---

**Ready to use!** 🚀 Start with: `POST /proposals/session/start` → Get session ID → `POST /proposals/converse`
