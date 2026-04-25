from datetime import date
import os
import platform
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Ensure GTK runtime is discoverable for WeasyPrint on Windows.
if platform.system() == "Windows":
    gtk_candidates = [
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
    ]
    for gtk_bin in gtk_candidates:
        if Path(gtk_bin).exists() and gtk_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = gtk_bin + os.pathsep + os.environ.get("PATH", "")

from weasyprint import HTML

from src.config import AGENCY_NAME, AGENCY_LOGO_PATH, AGENCY_SERVICES, AGENCY_DEMO_LINK


def _proposal_service_from_requirements(requirements: str) -> str:
    req = requirements.lower()
    services: list[str] = []

    if "website" in req or "web" in req:
        services.append("Website Development")
    if "ai" in req or "automation" in req or "agent" in req:
        services.append("AI Automation")
    if "social" in req or "media" in req:
        services.append("Social Media Management")

    if not services:
        return "Digital Services"
    if len(services) == 1:
        return services[0]
    if len(services) == 2:
        return f"{services[0]} + {services[1]}"
    return "Integrated Digital Services"


def render_pdf(
    client_business_name: str,
    client_requirements: str,
    body_html: str,
    output_file: Path,
) -> str:
    template_env = Environment(loader=FileSystemLoader("src/templates"))
    template = template_env.get_template("proposal.html.j2")

    service_title = _proposal_service_from_requirements(client_requirements)

    html_content = template.render(
        agency_name=AGENCY_NAME,
        agency_name_upper=AGENCY_NAME.upper(),
        logo_path=AGENCY_LOGO_PATH,
        client_business_name=client_business_name,
        proposal_title_header=f"{service_title} Proposal",
        proposal_title_display=f"{service_title}<br/>Proposal",
        current_date=date.today().strftime("%d-%m-%Y"),
        agency_services=", ".join(AGENCY_SERVICES),
        demo_link=AGENCY_DEMO_LINK,
        body_html=body_html,
    )

    HTML(string=html_content, base_url=str(Path.cwd())).write_pdf(str(output_file))
    return str(output_file)
