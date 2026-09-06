from groq import Groq
import wikipedia
from core.config import GROQ_API_KEY, GROQ_MODEL


class EventEnricher:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        wikipedia.set_lang("en")

    def get_wiki_summary(self, name: str) -> str:
        try:
            results = wikipedia.search(name)
            if not results:
                return "No summary available."
            try:
                page = wikipedia.page(results[0])
            except wikipedia.DisambiguationError as de:
                if not de.options:
                    return "No summary available."
                page = wikipedia.page(de.options[0])
            if not page:
                return "No summary available."
            return page.summary[:200] + "..." if len(page.summary) > 200 else page.summary
        except Exception as e:
            return f"Error fetching summary: {e}"

    def get_ai_summary(self, query: str) -> str:
        if self.client is None:
            return ""
        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": query}]
            )
            return str(response.choices[0].message.content)
        except Exception as e:
            return f"Error fetching Groq response: {e}"
