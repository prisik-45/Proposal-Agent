import requests

from src.config import SERPER_API_KEY


def serper_search(query: str, num: int = 5) -> list[str]:
    if not SERPER_API_KEY:
        return ["Serper API key missing, using baseline budget heuristics."]

    response = requests.post(
        "https://google.serper.dev/search",
        headers={
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json",
        },
        json={"q": query, "num": num},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    snippets: list[str] = []
    for item in data.get("organic", []):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")
        if title or snippet:
            snippets.append(f"{title}: {snippet} ({link})")
    return snippets[:num]
