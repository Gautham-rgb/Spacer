from groq import Groq
import wikipedia
from typing import Optional
from .config import GROQ_API_KEY

class EventEnricher:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        wikipedia.set_lang("en")

    def get_wiki_summary(self, name: str) -> str:
        try:
            results = wikipedia.search(name)
            if results:
                page = wikipedia.page(results[0])
                return page.summary[:200] + "..." if len(page.summary) > 200 else page.summary
            return "No summary available."
        except Exception as e:
            return f"Error fetching summary: {e}"

    def get_ai_summary(self, query: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": query}]
            )
            return str(response.choices[0].message.content)
        except Exception as e:
            return f"Error fetching Groq response: {e}"
