"""Best-effort launch enrichment: Wikipedia summary + optional Groq rewrite.

Both third-party libraries are imported lazily so ``events``/``engine`` still
import and work when they aren't installed. Failures never leak into event
content: on any error the enrichment is skipped and the caller's own
description is kept.
"""

from __future__ import annotations

from collections import OrderedDict

from core.config import GROQ_API_KEY, GROQ_MODEL

_WIKI = None
_GROQ_CLIENT = None
if GROQ_API_KEY:
    try:  # pragma: no cover - environment dependent
        from groq import Groq
        _GROQ_CLIENT = Groq(api_key=GROQ_API_KEY)
    except Exception:  # noqa: BLE001 - never let a bad key break imports
        _GROQ_CLIENT = None

# Bounded per-mission summary cache so nightly web/bot polling doesn't hammer
# Wikipedia / Groq, and the process doesn't grow without bound.
_MAX_CACHE = 200


class EventEnricher:
    def __init__(self):
        self._summaries: "OrderedDict[str, str]" = OrderedDict()

    def _wiki(self):
        global _WIKI
        if _WIKI is None:
            import wikipedia
            wikipedia.set_lang("en")
            _WIKI = wikipedia
        return _WIKI

    def get_wiki_summary(self, name: str) -> str:
        if self._summaries.get(name) is not None:
            self._summaries.move_to_end(name)
            return self._summaries[name]
        try:
            results = self._wiki().search(name)
            if not results:
                return ""
            try:
                page = self._wiki().page(results[0])
            except _Disambiguation as de:
                if not de.options:
                    return ""
                page = self._wiki().page(de.options[0])
            if not page:
                return ""
            summary = page.summary[:200].rstrip(".") + "..." \
                if len(page.summary) > 200 else page.summary
            self._summaries[name] = summary
            self._summaries.move_to_end(name)
            if len(self._summaries) > _MAX_CACHE:
                self._summaries.popitem(last=False)
            return summary
        except Exception:  # noqa: BLE001 - enrichment is best-effort
            return ""

    def get_ai_summary(self, query: str) -> str:
        if _GROQ_CLIENT is None:
            return ""
        try:
            response = _GROQ_CLIENT.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": query}],
            )
            return str(response.choices[0].message.content).strip()
        except Exception:  # noqa: BLE001 - enrichment is best-effort
            return ""


try:  # pragma: no cover - import guard for legacy module path
    from wikipedia.exceptions import DisambiguationError as _Disambiguation
except ImportError:
    class _Disambiguation(Exception):
        options: tuple[str, ...] = ()