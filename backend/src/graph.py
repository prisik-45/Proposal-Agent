import base64
import json
from html import escape, unescape
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from src.config import AGENCY_NAME, AGENCY_SERVICES, GROQ_MODEL, OUTPUT_DIR
from src.pdf_builder import render_pdf
from src.state import ProposalState
from src.tools.drive import upload_pdf_public
from src.tools.groq_client import get_groq_client


FIXED_INTRODUCTION_HTML = """
<h3>1. Introduction</h3>
<p>We at Tarkshy specialize in building modern, immersive, and high-performance websites that not only look premium but also deliver real business value.</p>
<p>Based on your requirement, we understand that you are looking to develop a website that matches your vision in quality and experience, with a strong focus on design, performance, and user engagement.</p>
""".strip()


FIXED_PAYMENT_TERMS_HTML = """
<h3>7. Payment Terms</h3>
<p>Work will begin after confirmation of the initial token amount.</p>
<table style="width:100%; border-collapse:collapse; border:1px solid #bdbdbd;">
    <thead>
        <tr style="background:#000; color:#fff;">
            <th style="text-align:left; padding:8px; border-right:1px solid #bdbdbd;">Amount</th>
            <th style="text-align:left; padding:8px;">Terms</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="padding:8px; border-top:1px solid #bdbdbd; border-right:1px solid #bdbdbd;"><strong>10%</strong></td>
            <td style="padding:8px; border-top:1px solid #bdbdbd;">Upfront - to initiate the project</td>
        </tr>
        <tr>
            <td style="padding:8px; border-top:1px solid #bdbdbd; border-right:1px solid #bdbdbd;"><strong>Milestone 2</strong></td>
            <td style="padding:8px; border-top:1px solid #bdbdbd;">Mid-delivery payment</td>
        </tr>
        <tr>
            <td style="padding:8px; border-top:1px solid #bdbdbd; border-right:1px solid #bdbdbd;"><strong>Milestone 3</strong></td>
            <td style="padding:8px; border-top:1px solid #bdbdbd;">Final delivery payment</td>
        </tr>
    </tbody>
</table>
""".strip()


def _build_timeline_html(total_days: int) -> str:
        base_durations = [7, 14, 10, 7, 12]
        base_total = sum(base_durations)
        scaled = [max(1, round(day * total_days / base_total)) for day in base_durations]

        difference = total_days - sum(scaled)
        scaled[-1] += difference

        phases = [
                ("1. Discovery & Design", "Requirements gathering, conversation flow, UX mock-ups"),
                ("2. AI Development", "Model training, intent mapping, recommendation engine"),
                ("3. Integration & Payments", "Backend API links, payment gateway setup, social media connectors"),
                ("4. Testing & Pilot", "Functional & security testing, live pilot"),
                ("5. Deployment & Support", "Production launch, monitoring, post-launch support"),
        ]

        rows = []
        for (phase, activities), duration in zip(phases, scaled):
                rows.append(
                        f"<tr><td>{escape(phase)}</td><td>{escape(activities)}</td><td class='col-duration'>{duration}</td></tr>"
                )

        return f"""
<p>The project will be delivered in a structured {total_days}-day schedule, ensuring timely completion and clear milestone control.</p>
<table class="proposal-table">
    <thead>
        <tr>
            <th class="col-phase">Phase</th>
            <th class="col-activities">Key Activities</th>
            <th class="col-duration">Duration (Days)</th>
        </tr>
    </thead>
    <tbody>
        {''.join(rows)}
    </tbody>
</table>
""".strip()


FIXED_DESIGN_QUALITY_HTML = """
<h3>8. Design &amp; Quality Commitment</h3>
<ul>
    <li>We will craft a unique design tailored specifically to your brand identity and goals</li>
    <li>Our focus is on delivering premium quality that stands out - not just meets expectations</li>
    <li>The final product will be built to outperform industry benchmarks in design and performance</li>
    <li>Every element will be custom-crafted to reflect your brand's values and vision</li>
</ul>
""".strip()


FIXED_DEMO_WORK_HTML = """
<h3>9. Demo Work</h3>
<p>We have developed demo projects showcasing our design and development capabilities. The demos below reflect our approach to clean UI, smooth experience, and premium feel.</p>
<p><strong>Portfolio:</strong> <a href="https://www.takshy.com/">https://www.takshy.com/</a></p>
<p><strong>Demo Project 1:</strong> <a href="https://the-royal-palace-mauve.vercel.app/">https://the-royal-palace-mauve.vercel.app/</a></p>
<p><strong>Demo Project 2:</strong> <a href="https://zeore-new.vercel.app/">https://zeore-new.vercel.app/</a></p>
""".strip()


FIXED_REVISIONS_SUPPORT_HTML = """
<h3>10. Revisions &amp; Support</h3>
<ul>
    <li>Up to 2-3 revision rounds included</li>
    <li>Additional revisions available at extra cost</li>
    <li>3 months free maintenance support after de</li>
</ul>
""".strip()


FIXED_NEXT_STEPS_HTML = """
<h3>12. Next Steps</h3>
<p>To move forward with this project, here's how we proceed:</p>
<ul>
    <li>Review this proposal and share any questions or adjustments</li>
    <li>Confirm the scope and finalize the feature list</li>
    <li>Initial token payment (10%) to officially kick off the project</li>
    <li>Project kickoff meeting to align on design direction, timelines, and milestones</li>
    <li>Kindly provide product details, business information, and required content so we can initiate the design and development process smoothly.</li>
</ul>
""".strip()


def _render_structured_html(section_data: dict) -> str:
    parts: list[str] = []

    for paragraph in section_data.get("paragraphs", []):
        parts.append(f"<p>{escape(str(paragraph))}</p>")

    bullets = section_data.get("bullets", [])
    if bullets:
        bullet_items = "".join(f"<li>{escape(str(item))}</li>" for item in bullets)
        parts.append(f"<ul>{bullet_items}</ul>")

    return "\n".join(parts).strip() or "<p></p>"


def _build_pricing_html(price_min: str, price_max: str, includes_text: str) -> str:
    """
    Generate pricing section with user-provided pricing information.
    Price must be provided explicitly by the user when generating proposals.
    Styling is defined in proposal.html.j2 template.
    """
    html = f"""
<div class="pricing-container">
    <h4 class="pricing-title">TOTAL PROJECT COST</h4>
    <p class="pricing-amount">₹{price_min} — ₹{price_max}</p>
    <p class="pricing-includes">Includes {includes_text}</p>
</div>

<p class="pricing-note"><strong>Note:</strong> The final cost may vary depending on additional features, integrations (cart systems, advanced animations, admin panels), or custom requirements beyond the initial scope.</p>

<div class="value-assurance">
    <p><strong>Value Assurance:</strong> If we are unable to deliver the promised quality and experience, a full refund will be provided.</p>
</div>
""".strip()
    
    return html


def _parse_budget_value(value: str) -> int:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits or "0")


def _format_budget_range(price_min: str, price_max: str) -> str:
    return f"INR {_parse_budget_value(price_min):,} to INR {_parse_budget_value(price_max):,}"


def _budget_guidance(price_min: str, price_max: str) -> str:
    min_value = _parse_budget_value(price_min)
    max_value = _parse_budget_value(price_max)
    midpoint = (min_value + max_value) / 2

    if midpoint <= 50_000:
        return (
            "Lean budget. Prioritize the core business objective, essential pages or workflows, "
            "standard UI components, basic integrations, testing, and launch readiness. "
            "Avoid promising advanced automation, complex admin panels, heavy custom animation, "
            "or large multi-module builds unless the user included them explicitly."
        )
    if midpoint <= 150_000:
        return (
            "Balanced budget. Include a polished core solution, responsive UI, practical integrations, "
            "content structure, testing, deployment support, and reasonable refinement. "
            "Keep advanced features scoped clearly as optional or phased when they exceed the budget."
        )
    return (
        "Premium budget. Include a more comprehensive scope with custom UX, stronger automation, "
        "richer integrations, performance optimization, analytics, admin or workflow tooling where relevant, "
        "and more complete post-launch support."
    )


def _technology_rows_from_override(technology_text: str) -> list[tuple[str, str]]:
    text = technology_text.strip()
    lower = text.lower()
    rows: list[tuple[str, str]] = []

    layer_keywords = [
        ("Frontend", ["next", "react", "vue", "angular", "frontend"]),
        ("Styling", ["tailwind", "css", "bootstrap", "styled"]),
        ("Backend", ["node", "express", "fastapi", "django", "flask", "backend"]),
        ("Database", ["postgres", "mysql", "mongodb", "mongo", "supabase", "database", "db"]),
        ("AI / LLM", ["openai", "groq", "langchain", "langgraph", "llm", "ai"]),
        ("Automation", ["zapier", "make", "n8n", "webhook", "automation"]),
        ("Hosting", ["vercel", "aws", "azure", "gcp", "vps", "hosting", "cloud"]),
    ]

    parts = [part.strip(" .") for part in text.replace(" and ", ", ").split(",") if part.strip(" .")]
    used_parts: set[str] = set()
    for layer, keywords in layer_keywords:
        matches = [part for part in parts if any(keyword in part.lower() for keyword in keywords)]
        if matches:
            rows.append((layer, " / ".join(matches)))
            used_parts.update(matches)

    remaining = [part for part in parts if part not in used_parts]
    if remaining:
        rows.append(("Additional Tools", " / ".join(remaining)))

    return rows or [("Requested Stack", text)]


def _default_technology_rows(client_requirements: str) -> list[tuple[str, str]]:
    req = client_requirements.lower()

    if "website" in req or "web" in req or "ecommerce" in req or "e-commerce" in req:
        return [
            ("Frontend", "Next.js / React - or other frameworks as per project requirements"),
            ("Styling", "Tailwind CSS / CSS Modules / Styled Components"),
            ("Backend", "Node.js, Express.js (if required)"),
            ("Database", "PostgreSQL (Supabase) / VPS-hosted DB - as per client requirements"),
            ("Hosting", "Vercel / VPS"),
        ]

    if "ai" in req or "automation" in req or "agent" in req or "chatbot" in req:
        return [
            ("AI / LLM", "OpenAI / Groq / Anthropic - selected as per use case and budget"),
            ("Orchestration", "LangChain / LangGraph for workflow and agent logic"),
            ("Backend", "FastAPI / Node.js for APIs, business logic, and integrations"),
            ("Database", "PostgreSQL / Supabase, with vector database if retrieval is required"),
            ("Integrations", "REST APIs, webhooks, CRM, WhatsApp, email, or third-party tools as required"),
            ("Hosting", "VPS / cloud deployment with secure environment configuration"),
        ]

    if "social" in req or "media" in req:
        return [
            ("Planning", "Notion / Google Workspace for calendar, approvals, and content planning"),
            ("Design", "Figma / Canva / Adobe tools based on campaign requirements"),
            ("Publishing", "Meta Business Suite / LinkedIn tools / scheduling platforms as required"),
            ("Analytics", "Platform analytics, Google Analytics, and campaign reporting dashboards"),
            ("Automation", "Zapier / Make / native platform automation where useful"),
        ]

    return [
        ("Core Stack", "Modern, scalable tools selected according to final project requirements"),
        ("Backend", "FastAPI / Node.js where APIs or integrations are required"),
        ("Database", "PostgreSQL / Supabase if structured data storage is required"),
        ("Hosting", "VPS / cloud hosting according to deployment needs"),
    ]


def _build_technology_stack_html(client_requirements: str, technology_text: str | None = None) -> str:
    rows = (
        _technology_rows_from_override(technology_text)
        if technology_text
        else _default_technology_rows(client_requirements)
    )
    table_rows = "".join(
        f"<tr><td>{escape(layer)}</td><td>{escape(technology)}</td></tr>"
        for layer, technology in rows
    )

    return f"""
<p>We will be using modern and scalable technologies ensuring fast loading speed, performance, and scalability for future upgrades.</p>
<table class="proposal-table">
    <thead>
        <tr>
            <th class="col-phase">Layer</th>
            <th>Technology</th>
        </tr>
    </thead>
    <tbody>
        {table_rows}
    </tbody>
</table>
""".strip()


def _generate_dynamic_section(
    client,
    section_number: int,
    section_title: str,
    agency_name: str,
    agency_services: list[str],
    client_business: str,
    client_requirements: str,
    timeline_days: int,
    budget_inr: str,
    budget_guidance: str,
    max_words: int = None,
) -> str:
    word_limit_text = f"IMPORTANT: Keep content to maximum {max_words} words total." if max_words else ""
    
    prompt = f"""
Generate content for section {section_number}. {section_title}.
Return STRICT JSON only in this shape:
{{
  "paragraphs": ["..."],
  "bullets": ["..."]
}}

Rules:
- Do not include heading text.
- Do not include HTML.
- Keep 1-2 paragraphs and 3-6 bullet points max.
- Write section 2 and section 3 according to the provided budget range.
- Match ambition, deliverables, and complexity to the budget guidance.
- Do not overpromise features that do not fit the budget.
- Use a professional, conversational tone.
- Do not use emojis.
- Do not use markdown bold or italic markers.
{word_limit_text}

Context:
- Agency: {agency_name}
- Agency services: {', '.join(agency_services)}
- Client business: {client_business}
- Client requirements: {client_requirements}
- Timeline: {timeline_days} days
- User provided budget range: {budget_inr}
- Budget guidance: {budget_guidance}
""".strip()

    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_completion_tokens=900,
        top_p=1,
        stream=False,
    )
    raw = (completion.choices[0].message.content or "").strip()

    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON is not an object")
    except Exception:
        data = {"paragraphs": [raw], "bullets": []}

    return _render_structured_html(data)


def intake_node(state: ProposalState) -> ProposalState:
    data = state["input"]
    state["computed_budget_inr"] = _format_budget_range(
        data.get("price_min", "0"),
        data.get("price_max", "0"),
    )
    state["budget_guidance"] = _budget_guidance(
        data.get("price_min", "0"),
        data.get("price_max", "0"),
    )
    return state


def draft_node(state: ProposalState) -> ProposalState:
    client = get_groq_client()
    data = state["input"]
    budget_inr = state["computed_budget_inr"]
    budget_guidance = state["budget_guidance"]

    dynamic_2 = _generate_dynamic_section(
        client=client,
        section_number=2,
        section_title="Project Objective",
        agency_name=AGENCY_NAME,
        agency_services=AGENCY_SERVICES,
        client_business=data["client_business_name"],
        client_requirements=data["client_requirements"],
        timeline_days=data["timeline_days"],
        budget_inr=budget_inr,
        budget_guidance=budget_guidance,
        max_words=data.get("project_objective_max_words"),
    )
    dynamic_3 = _generate_dynamic_section(
        client=client,
        section_number=3,
        section_title="Scope of Work",
        agency_name=AGENCY_NAME,
        agency_services=AGENCY_SERVICES,
        client_business=data["client_business_name"],
        client_requirements=data["client_requirements"],
        timeline_days=data["timeline_days"],
        budget_inr=budget_inr,
        budget_guidance=budget_guidance,
        max_words=data.get("scope_of_work_max_words"),
    )
    dynamic_4 = _build_technology_stack_html(
        client_requirements=data["client_requirements"],
        technology_text=data.get("technology_stack_text"),
    )
    dynamic_5 = _build_timeline_html(data["timeline_days"])
    dynamic_6 = _build_pricing_html(
        price_min=data.get("price_min", "25,000"),
        price_max=data.get("price_max", "40,000"),
        includes_text=data.get("includes_text", "Full development • Domain setup • Basic SEO • 3 months maintenance"),
    )
    dynamic_11 = _generate_dynamic_section(
        client=client,
        section_number=11,
        section_title="Additional Notes",
        agency_name=AGENCY_NAME,
        agency_services=AGENCY_SERVICES,
        client_business=data["client_business_name"],
        client_requirements=data["client_requirements"],
        timeline_days=data["timeline_days"],
        budget_inr=budget_inr,
        budget_guidance=budget_guidance,
        max_words=data.get("additional_notes_max_words"),
    )

    state["section_text"] = "\n\n".join(
        [
            FIXED_INTRODUCTION_HTML,
            f"<h3>2. Project Objective</h3>\n{dynamic_2}",
            f"<h3>3. Scope of Work</h3>\n{dynamic_3}",
            f"<h3>4. Technology Stack</h3>\n{dynamic_4}",
            f"<h3>5. Timeline</h3>\n{dynamic_5}",
            f"<h3>6. Pricing</h3>\n{dynamic_6}",
            FIXED_PAYMENT_TERMS_HTML,
            FIXED_DESIGN_QUALITY_HTML,
            FIXED_DEMO_WORK_HTML,
            FIXED_REVISIONS_SUPPORT_HTML,
            f"<h3>11. Additional Notes</h3>\n{dynamic_11}",
            FIXED_NEXT_STEPS_HTML,
        ]
    )
    return state


def validate_node(state: ProposalState) -> ProposalState:
    text = (state.get("section_text") or "")
    lowered = unescape(text).lower()
    required = [
        "introduction",
        "project objective",
        "scope of work",
        "technology stack",
        "timeline",
        "pricing",
        "payment terms",
        "design & quality commitment",
        "demo work",
        "revisions & support",
        "additional notes",
        "next steps",
    ]
    missing = [x for x in required if x not in lowered]

    if missing:
        state["error"] = f"Missing sections: {', '.join(missing)}"
    else:
        state.pop("error", None)
    return state


def pdf_node(state: ProposalState) -> ProposalState:
    data = state["input"]
    file_name = f"Tarkshy_Proposal_{data['client_business_name'].replace(' ', '')}.pdf"
    output_path = OUTPUT_DIR / file_name
    path = render_pdf(
        client_business_name=data["client_business_name"],
        client_requirements=data["client_requirements"],
        body_html=state.get("section_text", ""),
        output_file=Path(output_path),
    )
    state["output_pdf_path"] = path
    try:
        pdf_bytes = Path(path).read_bytes()
        state["pdf_data_url"] = "data:application/pdf;base64," + base64.b64encode(pdf_bytes).decode("utf-8")
    except Exception:
        state["pdf_data_url"] = ""
    return state


def drive_node(state: ProposalState) -> ProposalState:
    try:
        file_id, link = upload_pdf_public(state["output_pdf_path"])
        state["drive_file_id"] = file_id
        state["drive_public_link"] = link
    except Exception as exc:
        # On Vercel/serverless, browser-based OAuth re-auth is unavailable.
        # Treat upload as optional so proposal generation can still succeed.
        state["drive_file_id"] = ""
        state["drive_public_link"] = ""
        state["drive_upload_error"] = str(exc)
    return state


def should_continue(state: ProposalState) -> str:
    if state.get("error"):
        return "end"
    return "ok"


def build_graph():
    graph = StateGraph(ProposalState)
    graph.add_node("intake", intake_node)
    graph.add_node("draft", draft_node)
    graph.add_node("validate", validate_node)
    graph.add_node("pdf", pdf_node)
    graph.add_node("drive", drive_node)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "draft")
    graph.add_edge("draft", "validate")
    graph.add_conditional_edges(
        "validate",
        should_continue,
        {
            "ok": "pdf",
            "end": END,
        },
    )
    graph.add_edge("pdf", "drive")
    graph.add_edge("drive", END)

    return graph.compile()
