"""
FastAPI Backend for Proposal Agent - Chatbot Integration
Approach B: One-shot natural language input with conversational responses
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import traceback

from src.graph import build_graph
from src.nlp_parser import extract_proposal_params, validate_extracted_params, format_extracted_params
from src.pinecone_memory import get_memory
from src.conversation_manager import get_manager

import uuid


# ========== Pydantic Models ==========

class ProposalRequest(BaseModel):
    """One-shot natural language proposal request"""
    user_input: str = Field(
        ...,
        description="Natural language input describing the proposal requirements",
        example="Create proposal for TechCorp to build AI agent in 60 days, budget ₹40,000-60,000, includes AI model development • API integration • Custom workflows • 3 months support, scope limit 200 words"
    )


class ProposalResponse(BaseModel):
    """Proposal generation response"""
    success: bool
    message: str
    drive_link: Optional[str] = None
    extracted_params: Optional[dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str


# ========== Conversational Proposal Models ==========

class ConversationRequest(BaseModel):
    """Conversational proposal message with session tracking"""
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation continuity (auto-generated if not provided)"
    )
    user_message: str = Field(
        ...,
        description="User message - can be initial proposal request or modification",
        example="Change the timeline to 40 days"
    )


class ConversationResponse(BaseModel):
    """Response from conversational proposal endpoint"""
    success: bool
    message: str
    session_id: str
    is_modification: bool
    changes_detected: dict
    current_params: Optional[dict] = None
    current_state: Optional[dict] = None
    drive_link: Optional[str] = None
    error: Optional[str] = None


class SessionStartResponse(BaseModel):
    """Response when starting a new session"""
    session_id: str
    message: str
    initial_prompt: str


class SessionHistoryResponse(BaseModel):
    """Response containing session conversation history"""
    session_id: str
    turn_count: int
    history: list
    current_proposal_state: Optional[dict] = None


# ========== FastAPI App ==========

app = FastAPI(
    title="Proposal Agent API",
    description="Generate professional proposals using natural language input",
    version="1.0.0"
)

# ========== CORS Middleware ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (can be restricted to ["http://localhost:3000"] for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Health Check ==========

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify API is running.
    """
    return HealthResponse(
        status="healthy",
        message="Proposal Agent API is running and ready to accept requests"
    )


# ========== Proposal Generation Endpoint ==========

@app.post("/proposals/generate", response_model=ProposalResponse)
async def generate_proposal(request: ProposalRequest):
    """
    Generate a proposal from natural language input.
    
    Accepts one-shot natural language input and extracts:
    - Client business name
    - Project requirements
    - Timeline (days)
    - Budget range
    - Deliverables/Includes
    - Optional word limits
    
    Returns:
    - PDF link from Google Drive
    - Extracted parameters
    - Success status
    
    Example input:
    "Create proposal for ABC Company to build website in 45 days, 
     budget ₹30,000-50,000, includes full development • domain setup • 3 months support, 
     scope of work 200 words"
    """
    try:
        # Extract parameters from natural language
        extracted = extract_proposal_params(request.user_input)
        
        # Validate extracted parameters
        is_valid, error_msg = validate_extracted_params(extracted)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Format for consistency
        extracted = format_extracted_params(extracted)
        
        # Build and invoke the proposal graph
        graph = build_graph()
        result = graph.invoke({
            "input": extracted
        })
        
        # Extract results
        drive_link = result.get("drive_public_link", "")
        
        return ProposalResponse(
            success=True,
            message="Proposal generated successfully!",
            drive_link=drive_link,
            extracted_params=extracted,
            error=None
        )
        
    except HTTPException as he:
        return ProposalResponse(
            success=False,
            message="Failed to generate proposal",
            drive_link=None,
            extracted_params=extracted if 'extracted' in locals() else None,
            error=he.detail
        )
    
    except Exception as e:
        error_trace = traceback.format_exc()
        return ProposalResponse(
            success=False,
            message="Failed to generate proposal",
            drive_link=None,
            extracted_params=extracted if 'extracted' in locals() else None,
            error=f"{str(e)}\n{error_trace}"
        )


# ========== Parameter Extraction Endpoint (For Testing/Debugging) ==========

class ParamExtractionResponse(BaseModel):
    """Parameter extraction response"""
    extracted_params: dict
    is_valid: bool
    validation_error: Optional[str] = None
    formatted_params: Optional[dict] = None


@app.post("/debug/extract-params", response_model=ParamExtractionResponse)
async def debug_extract_params(request: ProposalRequest):
    """
    Debug endpoint: Extract and validate parameters without generating proposal.
    Useful for testing NLP parser.
    
    Example input:
    "Proposal for WebDesign Inc to create e-commerce platform in 75 days, 
     ₹35,000 to ₹50,000, with payment gateway • inventory system • user auth"
    """
    extracted = extract_proposal_params(request.user_input)
    is_valid, error_msg = validate_extracted_params(extracted)
    formatted = format_extracted_params(extracted) if is_valid else None
    
    return ParamExtractionResponse(
        extracted_params=extracted,
        is_valid=is_valid,
        validation_error=error_msg,
        formatted_params=formatted
    )


# ========== Conversational Proposal Endpoints ==========

@app.post("/proposals/session/start", response_model=SessionStartResponse)
async def start_session():
    """
    Start a new conversational proposal session.
    
    Returns:
    - session_id: Unique identifier for conversation
    - initial_prompt: Instructions for the user
    """
    session_id = str(uuid.uuid4())
    
    return SessionStartResponse(
        session_id=session_id,
        message="Conversational session started",
        initial_prompt="Welcome! Describe your proposal requirements in natural language. Example: 'Create proposal for TechCorp to build AI agent in 60 days, budget ₹40,000-60,000, includes AI development • API integration • 3 months support'"
    )


@app.post("/proposals/converse", response_model=ConversationResponse)
async def converse_proposal(request: ConversationRequest):
    """
    Conversational proposal modification endpoint.
    Supports both initial proposal generation and iterative modifications.
    
    Features:
    - Session-based memory with Pinecone
    - Natural language modification understanding
    - LLM-powered intent recognition
    - Automatic proposal regeneration on changes
    
    Args:
        session_id: Optional - auto-generated if not provided
        user_message: User's natural language input
    
    Example flow:
        1. User: "Create proposal for ABC Company..."
        2. Bot: Generates proposal
        3. User: "Change timeline to 40 days"
        4. Bot: Detects modification, updates, regenerates
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        user_message = request.user_message.strip()
        
        if not user_message:
            raise ValueError("user_message cannot be empty")
        
        # Get Pinecone memory and conversation manager
        memory = get_memory()
        manager = get_manager()
        
        # Retrieve conversation context
        context = memory.retrieve_conversation_context(
            session_id=session_id,
            query=user_message,
            top_k=3
        )
        
        # Get current proposal state
        current_state_record = memory.get_latest_proposal_state(session_id)
        current_state = current_state_record.get("state", {}) if current_state_record else {}
        current_params = current_state_record.get("params", {}) if current_state_record else {}
        turn_number = (current_state_record.get("turn_number", 0) + 1) if current_state_record else 1
        
        # Understand if this is a modification or new proposal
        is_modification, changes, explanation = manager.understand_modification(
            user_message, 
            current_params,
            context
        )
        
        # Process based on type
        if is_modification and current_params:
            # Update existing proposal
            updated_params = current_params.copy()
            updated_params.update(changes)
            
            # Validate
            is_valid, error_msg = validate_extracted_params(updated_params)
            if not is_valid:
                raise ValueError(f"Invalid parameters after modification: {error_msg}")
            
            # Format
            updated_params = format_extracted_params(updated_params)
            
            # Regenerate proposal with updated params
            graph = build_graph()
            result = graph.invoke({"input": updated_params})
            drive_link = result.get("drive_public_link", "")
            
            assistant_response = f"✅ {explanation}\nRegenerated proposal with updates!"
            
        else:
            # Initial proposal generation
            extracted = extract_proposal_params(user_message)
            is_valid, error_msg = validate_extracted_params(extracted)
            
            if not is_valid:
                raise ValueError(f"Missing required fields: {error_msg}")
            
            extracted = format_extracted_params(extracted)
            updated_params = extracted
            
            # Generate proposal
            graph = build_graph()
            result = graph.invoke({"input": extracted})
            drive_link = result.get("drive_public_link", "")
            
            assistant_response = "✅ Proposal generated successfully! You can now make modifications like 'Change timeline to X days' or 'Update budget to Y'"
            is_modification = False
            changes = {}
        
        # Store conversation turn in memory
        memory.store_conversation_turn(
            session_id=session_id,
            turn_number=turn_number,
            user_message=user_message,
            assistant_response=assistant_response,
            proposal_params=updated_params,
            proposal_state=result if 'result' in locals() else {}
        )
        
        return ConversationResponse(
            success=True,
            message=assistant_response,
            session_id=session_id,
            is_modification=is_modification,
            changes_detected=changes,
            current_params=updated_params,
            current_state=result if 'result' in locals() else {},
            drive_link=drive_link,
            error=None
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        return ConversationResponse(
            success=False,
            message="Failed to process conversation",
            session_id=request.session_id or "unknown",
            is_modification=False,
            changes_detected={},
            current_params=None,
            current_state=None,
            drive_link=None,
            error=f"{str(e)}\n{error_trace}"
        )


@app.get("/proposals/session/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str):
    """
    Retrieve full conversation history for a session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Full conversation history and current state
    """
    try:
        memory = get_memory()
        
        history = memory.get_session_history(session_id, limit=50)
        current_state = memory.get_latest_proposal_state(session_id)
        
        return SessionHistoryResponse(
            session_id=session_id,
            turn_count=len(history),
            history=history,
            current_proposal_state=current_state.get("state") if current_state else None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/proposals/session/{session_id}")
async def delete_session(session_id: str):
    """
    Clear conversation history for a session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Confirmation message
    """
    try:
        memory = get_memory()
        success = memory.clear_session(session_id)
        
        if success:
            return {"success": True, "message": f"Session {session_id} cleared"}
        else:
            raise Exception("Failed to clear session")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Error Handler ==========

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return {
        "success": False,
        "message": "An unexpected error occurred",
        "error": str(exc)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
