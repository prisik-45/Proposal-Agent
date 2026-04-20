from typing import List, Optional, TypedDict


class ProposalInput(TypedDict):
    client_business_name: str
    client_requirements: str
    timeline_days: int


class ProposalState(TypedDict, total=False):
    input: ProposalInput
    market_research: List[str]
    computed_budget_inr: str
    section_text: str
    html_content: str
    output_pdf_path: str
    drive_file_id: str
    drive_public_link: str
    error: Optional[str]
