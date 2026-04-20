import json
from html import escape, unescape
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from src.config import AGENCY_NAME, AGENCY_SERVICES, GROQ_MODEL, OUTPUT_DIR
from src.pdf_builder import render_pdf
from src.state import ProposalState
from src.tools.drive import upload_pdf_public
from src.tools.groq_client import get_groq_client
from src.tools.research import serper_search


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
<p>AI Automation Demo: <a href="https://the-royal-palace-mauve.vercel.app/">https://the-royal-palace-mauve.vercel.app/</a><br/>
Web Development Demo: <a href="https://the-royal-palace-mauve.vercel.app/">https://the-royal-palace-mauve.vercel.app/</a><br/>
Social Media Management Demo: <a href="https://the-royal-palace-mauve.vercel.app/">https://the-royal-palace-mauve.vercel.app/</a></p>
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
    research_text: str,
) -> str:
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
- Pricing section must mention INR values.

Context:
- Agency: {agency_name}
- Agency services: {', '.join(agency_services)}
- Client business: {client_business}
- Client requirements: {client_requirements}
- Timeline: {timeline_days} days
- Budget anchor: {budget_inr}
- Market research:
{research_text}
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


def _compute_budget(requirements: str, research_points: list[str]) -> str:
    req = requirements.lower()
    base = 80000
    if "website" in req or "web" in req:
        base += 70000
    if "ai" in req or "agent" in req:
        base += 120000
    if "social" in req:
        base += 45000

    multiplier = 1.0
    text = " ".join(research_points).lower()
    if "enterprise" in text or "premium" in text:
        multiplier = 1.2

    final_value = int(base * multiplier)
    return f"INR {final_value:,}"


def intake_node(state: ProposalState) -> ProposalState:
    return state


def research_node(state: ProposalState) -> ProposalState:
    business = state["input"]["client_business_name"]
    requirements = state["input"]["client_requirements"]
    query = f"India pricing benchmark for {business} {requirements} web development ai automation social media management"
    points = serper_search(query=query, num=5)
    state["market_research"] = points
    state["computed_budget_inr"] = _compute_budget(requirements, points)
    return state


def draft_node(state: ProposalState) -> ProposalState:
    client = get_groq_client()
    data = state["input"]
    research_text = "\n".join(f"- {x}" for x in state.get("market_research", []))

    dynamic_2 = _generate_dynamic_section(
        client=client,
        section_number=2,
        section_title="Project Objective",
        agency_name=AGENCY_NAME,
        agency_services=AGENCY_SERVICES,
        client_business=data["client_business_name"],
        client_requirements=data["client_requirements"],
        timeline_days=data["timeline_days"],
        budget_inr=state["computed_budget_inr"],
        research_text=research_text,
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
        budget_inr=state["computed_budget_inr"],
        research_text=research_text,
    )
    dynamic_4 = _generate_dynamic_section(
        client=client,
        section_number=4,
        section_title="Technology Stack",
        agency_name=AGENCY_NAME,
        agency_services=AGENCY_SERVICES,
        client_business=data["client_business_name"],
        client_requirements=data["client_requirements"],
        timeline_days=data["timeline_days"],
        budget_inr=state["computed_budget_inr"],
        research_text=research_text,
    )
    dynamic_5 = _build_timeline_html(data["timeline_days"])
    dynamic_6 = _generate_dynamic_section(
        client=client,
        section_number=6,
        section_title="Pricing",
        agency_name=AGENCY_NAME,
        agency_services=AGENCY_SERVICES,
        client_business=data["client_business_name"],
        client_requirements=data["client_requirements"],
        timeline_days=data["timeline_days"],
        budget_inr=state["computed_budget_inr"],
        research_text=research_text,
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
        budget_inr=state["computed_budget_inr"],
        research_text=research_text,
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
    return state


def drive_node(state: ProposalState) -> ProposalState:
    file_id, link = upload_pdf_public(state["output_pdf_path"])
    state["drive_file_id"] = file_id
    state["drive_public_link"] = link
    return state


def should_continue(state: ProposalState) -> str:
    if state.get("error"):
        return "end"
    return "ok"


def build_graph():
    graph = StateGraph(ProposalState)
    graph.add_node("intake", intake_node)
    graph.add_node("research", research_node)
    graph.add_node("draft", draft_node)
    graph.add_node("validate", validate_node)
    graph.add_node("pdf", pdf_node)
    graph.add_node("drive", drive_node)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "research")
    graph.add_edge("research", "draft")
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
