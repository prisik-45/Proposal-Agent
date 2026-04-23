# FastAPI Backend - Proposal Agent

## Overview

The FastAPI backend provides a REST API for the Proposal Agent system with **Approach B: One-shot natural language input** and **Option B: Word limit via prompt instruction**.

### Key Features

✅ **Natural Language Processing**: Extract proposal parameters from conversational input  
✅ **Word Limits**: Support custom word limits for specific sections  
✅ **LangGraph Integration**: Seamless connection to proposal generation workflow  
✅ **Google Drive Upload**: Automatic PDF generation and upload  
✅ **Interactive API Docs**: Auto-generated Swagger UI  

---

## Architecture

```
User Input (Natural Language)
         ↓
NLP Parser (src/nlp_parser.py)
         ↓
Parameter Extraction & Validation
         ↓
FastAPI Endpoint (src/api.py)
         ↓
LangGraph Workflow (src/graph.py)
         ↓
PDF Generation + Google Drive Upload
         ↓
Drive Link Response
```

---

## Running the API Server

### Start the Server

```bash
uv run python run_api.py
```

The server will start on `http://0.0.0.0:8000`

### Access Interactive API Documentation

Once running, open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Endpoints

### 1. Health Check
**Endpoint**: `GET /health`

Verify the API is running.

**Response**:
```json
{
  "status": "healthy",
  "message": "Proposal Agent API is running and ready to accept requests"
}
```

---

### 2. Generate Proposal (Main Endpoint)
**Endpoint**: `POST /proposals/generate`

Generate a complete proposal from natural language input.

**Request**:
```json
{
  "user_input": "Create proposal for TechCorp to build AI agent in 60 days, ₹40,000-60,000, includes AI model development • API integration • Custom workflows • 3 months support, scope 200 words"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Proposal generated successfully!",
  "drive_link": "https://drive.google.com/file/d/...",
  "extracted_params": {
    "client_business_name": "techcorp",
    "client_requirements": "ai agent",
    "timeline_days": 60,
    "price_min": "40000",
    "price_max": "60000",
    "includes_text": "AI model development • API integration • Custom workflows • 3 months support",
    "scope_of_work_max_words": 200
  }
}
```

---

### 3. Debug: Extract Parameters
**Endpoint**: `POST /debug/extract-params`

Test NLP extraction without generating proposal (for debugging).

**Request**:
```json
{
  "user_input": "Proposal for WebDesign Inc to create e-commerce platform in 75 days, ₹35,000 to ₹50,000, with payment gateway • inventory system • user auth"
}
```

**Response**:
```json
{
  "extracted_params": {
    "client_business_name": "webdesign inc",
    "client_requirements": "e-commerce platform",
    "timeline_days": 75,
    "price_min": "35000",
    "price_max": "50000",
    "includes_text": "payment gateway • inventory system • user auth",
    "scope_of_work_max_words": null
  },
  "is_valid": true,
  "validation_error": null,
  "formatted_params": {...}
}
```

---

## Natural Language Input Format

### Supported Input Patterns

The NLP parser understands flexible, conversational inputs:

#### Pattern 1: Comprehensive One-Shot
```
"Create proposal for [Client Name] to [build/develop/create] [service type] in [X] days, 
budget ₹[min]-[max], includes [deliverables separated by •], scope [X] words"
```

**Example**:
```
"Create proposal for TechCorp to build AI agent in 60 days, ₹40,000-60,000, 
includes AI model development • API integration • Custom workflows • 3 months support, 
scope 200 words"
```

#### Pattern 2: Flexible Format
```
"Proposal for [Client] - [service type], [X] days, budget [min]k-[max]k, 
includes [deliverables separated by •]"
```

**Example**:
```
"Proposal for FashionHub - social media management, 30 days, budget 15k-25k, 
includes content strategy • instagram setup • monthly calendar • 2 months management"
```

#### Pattern 3: Service-Focused
```
"[Build/Develop] [service type] for [Client], [X] days, ₹[min]-[max], 
includes [deliverables]"
```

**Example**:
```
"Build e-commerce site for ShopHub in 75 days, ₹30,000 to ₹50,000, 
includes payment gateway and inventory system"
```

### Recognized Service Types

- Website
- Web Application / App / Application
- Platform / System / Dashboard
- Solution
- AI Agent / Chatbot
- AI Automation / Automation
- Social Media Management
- Mobile App
- E-commerce / Ecommerce

### Parameter Extraction Rules

| Parameter | Format | Example |
|-----------|--------|---------|
| **Client Business Name** | Any text after "for" | "TechCorp", "ABC Company" |
| **Requirements** | Service type mentioned | "website", "AI agent", "social media" |
| **Timeline** | Number + "days" or "d" | "60 days", "75d" |
| **Budget** | "₹min-max" or "minK-maxK" | "₹40,000-60,000", "25k-35k" |
| **Includes** | Separated by • or , | "Development • Domain • Support" |
| **Word Limit** | "scope X words" or "X words max" | "scope 200 words", "300 words" |

---

## Word Limit Support

### How Word Limits Work

Word limits are passed to the LLM via the prompt with `max_words` parameter:

```python
# In src/graph.py
def _generate_dynamic_section(..., max_words: int = None):
    word_limit_text = f"IMPORTANT: Keep content to maximum {max_words} words total." if max_words else ""
    prompt = f"""Generate content... {word_limit_text}..."""
```

### Configurable Sections

| Section | Input Parameter | Default |
|---------|-----------------|---------|
| Project Objective (2) | `project_objective_max_words` | None |
| Scope of Work (3) | `scope_of_work_max_words` | None |
| Technology Stack (4) | `technology_stack_max_words` | None |
| Additional Notes (11) | `additional_notes_max_words` | None |

### Usage Example

```
"Create proposal for TechCorp to build website in 45 days, ₹30k-50k, 
includes development • domain • SEO, scope 200 words, tech 150 words"
```

This will:
- Limit Scope of Work section to 200 words
- Limit Technology Stack section to 150 words

---

## Testing the API

### Using the Test Script

```bash
uv run python test_api.py
```

This runs three tests:
1. Health check
2. Parameter extraction
3. Proposal generation (commented out by default)

### Example cURL Commands

**Health Check**:
```bash
curl http://localhost:8000/health
```

**Extract Parameters**:
```bash
curl -X POST http://localhost:8000/debug/extract-params \
  -H "Content-Type: application/json" \
  -d '{"user_input":"Create proposal for ABC to build website in 45 days, ₹30k-50k, includes development • domain • SEO"}'
```

**Generate Proposal**:
```bash
curl -X POST http://localhost:8000/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{"user_input":"Create proposal for XYZ Co to build AI chatbot in 60 days, ₹40k-60k, includes AI development • integration • 3 months support"}'
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Generate proposal
response = requests.post(
    f"{BASE_URL}/proposals/generate",
    json={
        "user_input": "Create proposal for TechCorp to build AI agent in 60 days, "
                      "₹40,000-60,000, includes AI development • API integration • support"
    }
)

result = response.json()
if result['success']:
    print(f"✅ Proposal generated!")
    print(f"Drive link: {result['drive_link']}")
    print(f"Extracted params: {result['extracted_params']}")
else:
    print(f"❌ Error: {result['error']}")
```

---

## NLP Parser Details

### File: `src/nlp_parser.py`

**Functions**:

#### `extract_proposal_params(user_input: str) -> Dict`
Extracts parameters from natural language.

**Returns**:
```python
{
    "client_business_name": str,
    "client_requirements": str,
    "timeline_days": int,
    "price_min": str,
    "price_max": str,
    "includes_text": str,
    "scope_of_work_max_words": int or None
}
```

#### `validate_extracted_params(params: Dict) -> Tuple[bool, Optional[str]]`
Validates extracted parameters.

**Returns**: `(is_valid: bool, error_message: Optional[str])`

#### `format_extracted_params(params: Dict) -> Dict`
Formats parameters for consistency (removes commas from prices, standardizes bullet separators).

---

## Error Handling

### Validation Errors

If extracted parameters are invalid:

```json
{
  "success": false,
  "message": "Failed to generate proposal",
  "drive_link": null,
  "extracted_params": {...},
  "error": "Missing required fields: client_business_name, client_requirements"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Missing required fields | NLP parser couldn't extract all parameters | Use clearer language in input |
| Timeline must be 1-365 days | Invalid timeline | Specify between 1-365 days |
| Prices must be positive | Invalid budget | Use positive numbers |
| Min price > max price | Budget range wrong | Ensure min ≤ max |
| Word limit 50-1000 | Invalid word limit | Use 50-1000 words |

---

## Integration with React Frontend

### Example React Component

```jsx
import { useState } from 'react';

export function ProposalChat() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/proposals/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: input })
      });

      const data = await response.json();
      setResult(data);
      
      if (data.success) {
        console.log('✅ PDF generated!');
        console.log('Drive link:', data.drive_link);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe your proposal requirements..."
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Generating...' : 'Generate Proposal'}
        </button>
      </form>

      {result && (
        <div>
          {result.success ? (
            <>
              <p>✅ Proposal generated successfully!</p>
              <a href={result.drive_link} target="_blank">
                Download PDF
              </a>
            </>
          ) : (
            <p>❌ Error: {result.error}</p>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## Deployment Considerations

### Environment Variables

The API uses the same `.env` file as the CLI:

```env
GROQ_API_KEY=...
GROQ_MODEL=mixtral-8x7b-32768
SERPER_API_KEY=...
GOOGLE_DRIVE_FOLDER_ID=...
```

### Production Setup

For production deployment:

1. **Use ASGI server** (already using Uvicorn)
2. **Enable CORS** for frontend integration
3. **Add authentication** if needed
4. **Use environment variables** for configuration
5. **Deploy to**: Render, Railway, Fly.io, or AWS Lambda

### Example Uvicorn Configuration for Production

```bash
uv run python -m uvicorn src.api:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

---

## Dependencies

The API requires these additional packages (already installed via `pyproject.toml`):

```
fastapi>=0.104.0
uvicorn>=0.24.0
```

---

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Verify all dependencies are installed: `uv sync`
- Check `.env` file is properly configured

### NLP not extracting parameters correctly
- Use the `/debug/extract-params` endpoint to test
- Try different input formats
- Check the test examples in `test_api.py`

### PDF generation fails
- Verify Google Drive credentials in `.env`
- Check if folder ID is correct
- Ensure all required APIs are enabled

### API returns 500 error
- Check server logs for detailed error
- Verify LangGraph configuration
- Test with `/debug/extract-params` first

---

## Next Steps

1. **Frontend Integration**: Create React chatbot UI
2. **Authentication**: Add user/session management
3. **History**: Store generated proposals in database
4. **Analytics**: Track proposal generation metrics
5. **Customization**: Allow custom section templates

