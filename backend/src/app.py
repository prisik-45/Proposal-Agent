"""
FastAPI Backend for Proposal Agent - Chatbot Integration
Approach B: One-shot natural language input with conversational responses
"""

import base64
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
import re
import time
import traceback

from src.config import ALLOWED_ORIGINS
from src.graph import build_graph
from src.memory_store import MemoryStore
from src.nlp_parser import (
    extract_proposal_params,
    validate_extracted_params,
    format_extracted_params,
    extract_update_fields,
)
from src.proposal_system_prompt import PROPOSAL_AGENT_SYSTEM_PROMPT


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
    pdf_download_url: Optional[str] = None
    extracted_params: Optional[dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str


class ProposalConversationRequest(BaseModel):
    """Request structure for conversational proposal updates."""
    user_input: str = Field(
        ...,
        description="Natural language user input for proposal creation or incremental updates",
        example="Change timeline to 40 days"
    )
    session_id: Optional[str] = Field(
        default="default",
        description="Optional session identifier for conversation memory"
    )


class ProposalConversationResponse(BaseModel):
    success: bool
    message: str
    changed_fields: Optional[List[str]] = None
    resolved_params: Optional[Dict[str, Any]] = None
    pdf_download_url: Optional[str] = None
    updated_sections: Optional[Dict[str, str]] = None
    full_proposal_md: Optional[str] = None
    retrieved_context: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ========== FastAPI App ==========

app = FastAPI(
    title="Proposal Agent API",
    description="Generate professional proposals using natural language input",
    version="1.0.0"
)

# ========== CORS Middleware ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Secured for production via env vars
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """Health check endpoint for Render"""
    return {"status": "ok", "message": "Proposal Agent API is running"}

memory_store = MemoryStore()


def _format_inr(amount: int) -> str:
    """Format integer INR values with Indian comma grouping."""
    amount_str = str(amount)
    if len(amount_str) <= 3:
        return f"₹{amount_str}"

    last_three = amount_str[-3:]
    remaining = amount_str[:-3]
    groups = []
    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        groups.insert(0, remaining)
    return f"₹{','.join(groups)},{last_three}"


def _format_timeline(days: int) -> str:
    weeks = days / 7
    approx = f"{weeks:.1f}".rstrip('0').rstrip('.')
    return f"{days} days (≈ {approx} weeks)"


def _build_timeline_section(params: Dict[str, Any]) -> str:
    timeline = params.get("timeline_days", 0)
    return (
        "## Timeline\n"
        f"The project is planned for {_format_timeline(timeline)}. "
        "We will work in focused stages to deliver meaningful progress and maintain flexibility for refinement."
    )


def _build_budget_section(params: Dict[str, Any]) -> str:
    min_budget = int(str(params.get("price_min", "0")).replace(',', ''))
    max_budget = int(str(params.get("price_max", "0")).replace(',', ''))
    return (
        "## Budget Breakdown\n"
        f"Estimated project cost: {_format_inr(min_budget)} to {_format_inr(max_budget)}. "
        "This estimate covers development, integration, testing, and initial support as outlined below."
    )


def _budget_guidance_text(params: Dict[str, Any]) -> str:
    min_budget = int(str(params.get("price_min", "0")).replace(',', ''))
    max_budget = int(str(params.get("price_max", "0")).replace(',', ''))
    midpoint = (min_budget + max_budget) / 2

    if midpoint <= 50_000:
        return (
            "The scope should stay focused on essential features, a clean user experience, "
            "basic integrations, testing, and launch readiness."
        )
    if midpoint <= 150_000:
        return (
            "The scope can include a polished core build, responsive UI, practical integrations, "
            "testing, deployment support, and a reasonable refinement cycle."
        )
    return (
        "The scope can support a more comprehensive build with custom UX, richer integrations, "
        "automation, analytics, performance optimization, and stronger post-launch support."
    )


def _build_project_objective_section(params: Dict[str, Any]) -> str:
    min_budget = int(str(params.get("price_min", "0")).replace(',', ''))
    max_budget = int(str(params.get("price_max", "0")).replace(',', ''))
    return (
        "## Project Objective\n"
        f"The objective is to deliver a practical {params.get('client_requirements', 'solution')} for "
        f"{params.get('client_business_name', 'the client')} within the provided budget range of "
        f"{_format_inr(min_budget)} to {_format_inr(max_budget)}. "
        f"{_budget_guidance_text(params)}"
    )


def _build_scope_section(params: Dict[str, Any]) -> str:
    includes = params.get("includes_text", "the agreed project deliverables")
    return (
        "## Scope of Work\n"
        f"The scope will cover {includes}. "
        f"{_budget_guidance_text(params)} "
        "Any advanced items outside this agreed scope should be treated as a separate phase or estimate."
    )


def _build_technology_stack_section(params: Dict[str, Any]) -> str:
    technology = params.get("technology_stack_text")
    if technology:
        return (
            "## Technology Stack\n"
            f"The proposal will use the requested technology stack: {technology}."
        )

    requirements = str(params.get("client_requirements", "")).lower()
    if "website" in requirements or "web" in requirements or "ecommerce" in requirements or "e-commerce" in requirements:
        return (
            "## Technology Stack\n"
            "Frontend: Next.js / React. Styling: Tailwind CSS / CSS Modules / Styled Components. "
            "Backend: Node.js and Express.js if required. Database: PostgreSQL / Supabase or VPS-hosted DB as per client requirements. "
            "Hosting: Vercel / VPS."
        )
    if "ai" in requirements or "automation" in requirements or "agent" in requirements or "chatbot" in requirements:
        return (
            "## Technology Stack\n"
            "AI / LLM: OpenAI, Groq, or Anthropic as per use case. Orchestration: LangChain / LangGraph. "
            "Backend: FastAPI / Node.js. Database: PostgreSQL / Supabase, with vector database support if retrieval is required. "
            "Hosting: VPS / cloud deployment."
        )
    if "social" in requirements or "media" in requirements:
        return (
            "## Technology Stack\n"
            "Planning: Notion / Google Workspace. Design: Figma / Canva / Adobe tools. "
            "Publishing: Meta Business Suite and relevant scheduling platforms. Analytics: platform analytics and reporting dashboards. "
            "Automation: Zapier / Make where useful."
        )
    return (
        "## Technology Stack\n"
        "The technology stack will be selected according to the final project requirements, budget, integrations, and deployment needs."
    )


def _build_deliverables_section(params: Dict[str, Any]) -> str:
    includes = params.get("includes_text", "Key deliverables will be provided as part of this engagement.")
    bullets = "\n".join([f"- {item.strip()}" for item in includes.split('•') if item.strip()])
    return (
        "## Deliverables\n"
        "The proposal includes the following deliverables:\n"
        f"{bullets}"
    )


def _build_full_proposal_md(params: Dict[str, Any]) -> str:
    return "\n\n".join([
        f"# Proposal for {params.get('client_business_name', 'Client')}" ,
        "## Executive Summary\n"
        f"We propose to build a tailored {params.get('client_requirements', 'solution')} for {params.get('client_business_name', 'the client')} that delivers measurable business impact and a premium digital experience.",
        _build_project_objective_section(params),
        _build_scope_section(params),
        _build_technology_stack_section(params),
        _build_timeline_section(params),
        _build_budget_section(params),
        _build_deliverables_section(params),
        "## Team & Expertise\n"
        "Our team brings proven experience in AI-led products, API-first development, and end-to-end delivery for enterprise clients.",
        "## Terms\n"
        "A phased engagement model and milestone-based payment schedule will ensure transparency, quality, and predictable delivery."
    ])


def _generate_proposal_artifacts(extracted: Dict[str, Any]) -> Dict[str, str]:
    graph = build_graph()
    result = graph.invoke({
        "input": extracted
    })
    payload = json.dumps(extracted, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return {
        "pdf_download_url": f"/proposals/download-pdf?payload={encoded_payload}",
        "graph_error": result.get("error", ""),
    }


@app.get("/proposals/download-pdf")
async def download_pdf(payload: str):
    """Generate and stream a PDF directly from encoded proposal parameters."""
    try:
        padding = "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode((payload + padding).encode("ascii")).decode("utf-8")
        params = json.loads(raw)
        if not isinstance(params, dict):
            raise ValueError("Invalid proposal payload")

        graph = build_graph()
        result = graph.invoke({"input": params})
        pdf_bytes = result.get("pdf_bytes")
        if not pdf_bytes:
            raise FileNotFoundError("Generated PDF bytes not found")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=proposal-{params.get('client_business_name', 'client')}.pdf"
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to generate PDF download: {exc}")


def _is_new_proposal_request(user_input: str) -> bool:
    return bool(
        re.search(
            r'\b(?:create|generate|make|prepare|draft)\s+(?:a\s+)?proposal\b|\bproposal\s+for\b',
            user_input,
            re.IGNORECASE,
        )
    )


def _interpret_update_changes(current_params: Dict[str, Any], updates: Dict[str, Any]) -> List[str]:
    changed_fields: List[str] = []
    if not current_params:
        return changed_fields

    if "timeline_days" in updates and updates["timeline_days"] != current_params.get("timeline_days"):
        changed_fields.append(
            f"timeline_days: {current_params.get('timeline_days')} -> {updates['timeline_days']}"
        )
    if "price_min" in updates and str(updates["price_min"]) != str(current_params.get("price_min")):
        changed_fields.append(
            f"budget_inr.min: {current_params.get('price_min')} -> {updates['price_min']}"
        )
    if "price_max" in updates and str(updates["price_max"]) != str(current_params.get("price_max")):
        changed_fields.append(
            f"budget_inr.max: {current_params.get('price_max')} -> {updates['price_max']}"
        )
    if "includes_text" in updates and updates["includes_text"] != current_params.get("includes_text"):
        changed_fields.append("includes_text: updated deliverables")
    if (
        "technology_stack_text" in updates
        and updates["technology_stack_text"] != current_params.get("technology_stack_text")
    ):
        changed_fields.append("technology_stack: updated")
    return changed_fields


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


class SystemPromptResponse(BaseModel):
    """System prompt response"""
    system_prompt: str


@app.get("/prompt/system", response_model=SystemPromptResponse)
async def get_system_prompt():
    """Get the Proposal Agent system prompt for /v1/messages integration."""
    return SystemPromptResponse(system_prompt=PROPOSAL_AGENT_SYSTEM_PROMPT)


@app.post("/proposals/converse", response_model=Dict[str, Any])
async def converse_proposal(request: ProposalConversationRequest) -> Dict[str, Any]:
    """Handle conversational proposal updates with session memory."""
    try:
        session_id = request.session_id or "default"
        session = memory_store.get_session(session_id)
        retrieved_turns = memory_store.retrieve_similar_turns(session_id, request.user_input)

        if session.current_params and _is_new_proposal_request(request.user_input):
            session.turns.clear()
            session.current_params = None
            retrieved_turns = []

        if not session.current_params:
            extracted = extract_proposal_params(request.user_input)
            is_valid, error_msg = validate_extracted_params(extracted)
            if not is_valid:
                return {
                    "success": False,
                    "message": "I could not create the proposal yet. Please provide the missing details and I will continue.",
                    "error": error_msg,
                }

            extracted = format_extracted_params(extracted)
            artifacts = _generate_proposal_artifacts(extracted)
            pdf_download_url = artifacts["pdf_download_url"]
            graph_error = artifacts.get("graph_error", "")
            if graph_error:
                return {
                    "success": False,
                    "message": "Failed to generate proposal due to validation error.",
                    "error": graph_error,
                }
            session.current_params = {**extracted, "pdf_download_url": pdf_download_url}
            memory_store.add_turn(
                session_id,
                "user",
                request.user_input,
                {
                    "params": extracted,
                    "proposal_sections": [
                        "executive_summary",
                        "scope_of_work",
                        "technical_architecture",
                        "timeline",
                        "budget_breakdown",
                        "deliverables",
                        "team_and_expertise",
                        "terms",
                    ],
                    "timestamp": int(time.time()),
                },
            )
            memory_store.add_turn(
                session_id,
                "assistant",
                "Initial proposal created and stored in conversation memory.",
                {
                    "params": session.current_params,
                    "timestamp": int(time.time()),
                },
            )

            full_md = _build_full_proposal_md(session.current_params)
            return {
                "success": True,
                "message": "Proposal created successfully. I used your timeline, budget range, and deliverables to prepare the PDF.",
                "changed_fields": [
                    f"client_business_name: None -> {session.current_params.get('client_business_name')}"
                ],
                "resolved_params": session.current_params,
                "pdf_download_url": pdf_download_url,
                "updated_sections": {
                    "project_objective": _build_project_objective_section(session.current_params),
                    "scope_of_work": _build_scope_section(session.current_params),
                    "timeline": _build_timeline_section(session.current_params),
                    "budget": _build_budget_section(session.current_params),
                },
                "full_proposal_md": full_md,
                "retrieved_context": {
                    "retrieved_turns": retrieved_turns,
                    "current_params": None,
                },
            }

        updates = extract_update_fields(request.user_input)
        if not updates:
            return {
                "success": False,
                "message": "I could not detect a clear update. Please specify the timeline, budget range, or deliverables you want to change.",
                "error": "Ambiguous update request",
                "retrieved_context": {
                    "retrieved_turns": retrieved_turns,
                    "current_params": session.current_params,
                },
            }

        resolved = {**session.current_params, **updates}
        resolved = format_extracted_params(resolved)
        is_valid, error_msg = validate_extracted_params(resolved)
        if not is_valid:
            return {
                "success": False,
                "message": "The updated proposal details are invalid. Please revise the input and I will try again.",
                "error": error_msg,
                "retrieved_context": {
                    "retrieved_turns": retrieved_turns,
                    "current_params": session.current_params,
                },
            }
        artifacts = _generate_proposal_artifacts(resolved)
        pdf_download_url = artifacts["pdf_download_url"]
        graph_error = artifacts.get("graph_error", "")
        if graph_error:
            return {
                "success": False,
                "message": "Failed to update proposal due to validation error.",
                "error": graph_error,
                "retrieved_context": {
                    "retrieved_turns": retrieved_turns,
                    "current_params": session.current_params,
                },
            }
        resolved = {**resolved, "pdf_download_url": pdf_download_url}

        changed_fields = _interpret_update_changes(session.current_params, resolved)
        if not changed_fields:
            return {
                "success": False,
                "message": "No meaningful changes were detected from the latest input.",
                "error": "No changes detected",
                "retrieved_context": {
                    "retrieved_turns": retrieved_turns,
                    "current_params": session.current_params,
                },
            }

        session.current_params = resolved
        memory_store.add_turn(
            session_id,
            "user",
            request.user_input,
            {
                "params": resolved,
                "proposal_sections": [
                    "executive_summary",
                    "scope_of_work",
                    "technical_architecture",
                    "timeline",
                    "budget_breakdown",
                    "deliverables",
                    "team_and_expertise",
                    "terms",
                ],
                "timestamp": int(time.time()),
            },
        )

        updated_sections: Dict[str, str] = {}
        if any(field.startswith("timeline_days") for field in changed_fields):
            updated_sections["timeline"] = _build_timeline_section(resolved)
            updated_sections["deliverables"] = _build_deliverables_section(resolved)
        if any("budget_inr" in field for field in changed_fields):
            updated_sections["project_objective"] = _build_project_objective_section(resolved)
            updated_sections["scope_of_work"] = _build_scope_section(resolved)
            updated_sections["budget"] = _build_budget_section(resolved)
        if "includes_text: updated deliverables" in changed_fields:
            updated_sections["scope_of_work"] = _build_scope_section(resolved)
            updated_sections["deliverables"] = _build_deliverables_section(resolved)
        if "technology_stack: updated" in changed_fields:
            updated_sections["technology_stack"] = _build_technology_stack_section(resolved)

        full_md = _build_full_proposal_md(resolved)
        return {
            "success": True,
            "message": "Proposal updated successfully. I regenerated the sections affected by your latest changes.",
            "changed_fields": changed_fields,
            "resolved_params": resolved,
            "pdf_download_url": pdf_download_url,
            "updated_sections": updated_sections,
            "full_proposal_md": full_md,
            "retrieved_context": {
                "retrieved_turns": retrieved_turns,
                "current_params": session.current_params,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "message": "An unexpected error occurred while updating the proposal.",
            "error": str(e),
        }


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
    - PDF download URL
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
        graph_error = result.get("error", "")

        if graph_error:
            return ProposalResponse(
                success=False,
                message="Failed to generate proposal.",
                pdf_download_url=None,
                extracted_params=extracted,
                error=graph_error,
            )
        
        # Generate the download URL with payload
        payload = json.dumps(extracted, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        pdf_download_url = f"/proposals/download-pdf?payload={encoded_payload}"
        
        return ProposalResponse(
            success=True,
            message="Proposal generated successfully!",
            pdf_download_url=pdf_download_url,
            extracted_params=extracted,
            error=None
        )
        
    except HTTPException as he:
        return ProposalResponse(
            success=False,
            message="Failed to generate proposal",
            pdf_download_url=None,
            extracted_params=extracted if 'extracted' in locals() else None,
            error=he.detail
        )
    
    except Exception as e:
        error_trace = traceback.format_exc()
        return ProposalResponse(
            success=False,
            message="Failed to generate proposal",
            pdf_download_url=None,
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
