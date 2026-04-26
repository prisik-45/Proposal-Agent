from typing import Optional, TypedDict


class ProposalInput(TypedDict, total=False):
    client_business_name: str
    client_requirements: str
    timeline_days: int
    price_min: str
    price_max: str
    includes_text: str
    technology_stack_text: str
    # Optional word limits for sections
    scope_of_work_max_words: int
    project_objective_max_words: int
    technology_stack_max_words: int
    additional_notes_max_words: int


class ProposalState(TypedDict, total=False):
    input: ProposalInput
    computed_budget_inr: str
    budget_guidance: str
    section_text: str
    html_content: str
    output_pdf_path: str
    pdf_bytes: bytes
    pdf_data_url: str
    error: Optional[str]
