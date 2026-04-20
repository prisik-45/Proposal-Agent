from groq import Groq

from src.config import GROQ_API_KEY


def get_groq_client() -> Groq:
    if GROQ_API_KEY:
        return Groq(api_key=GROQ_API_KEY)
    return Groq()
