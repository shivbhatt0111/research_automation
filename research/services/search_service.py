"""Multi-source search: Tavily (primary) -> DuckDuckGo (fallback).
Keeps the pipeline independent of Gemini's small grounding quota."""
import json
import logging

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from django.conf import settings

from .llm_providers import LLMError, LLMRouter

logger = logging.getLogger(__name__)


def repair_json_array(text: str) -> list | None:
    """Parses a JSON array, salvaging truncated LLM output by closing it."""
    start = text.find('[')
    if start == -1:
        return None
    text = text[start:]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    last = text.rfind('}')
    while last > 0:
        try:
            return json.loads(text[:last + 1] + ']')
        except json.JSONDecodeError:
            last = text.rfind('}', 0, last)
    return None


class SearchService:
    """Tavily (primary) + DDG (fallback) + LLM structuring. All free."""

    def __init__(self):
        self.router = LLMRouter()
        self.tavily_key = getattr(settings, 'TAVILY_API_KEY', '')
        self._tavily_client = None

    @property
    def tavily(self):
        if self.tavily_key and self._tavily_client is None:
            try:
                from tavily import TavilyClient
                self._tavily_client = TavilyClient(api_key=self.tavily_key)
            except Exception as exc:
                logger.warning('Tavily init failed: %s', exc)
                self._tavily_client = False
        return self._tavily_client or None

    @staticmethod
    def _ddg_results(query: str, max_results: int) -> list[dict]:
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as exc:
            logger.warning('DDG search failed for %r: %s', query, exc)
            return []

    def _tavily_results(self, query: str, max_results: int) -> list[dict]:
        if not self.tavily:
            return []
        try:
            resp = self.tavily.search(query=query, max_results=max_results)
            return [
                {
                    'title': r.get('title', ''),
                    'href': r.get('url', ''),
                    'body': r.get('content', ''),
                }
                for r in resp.get('results', [])
            ]
        except Exception as exc:
            logger.warning('Tavily search failed for %r: %s', query, exc)
            return []

    def _results(self, query: str, max_results: int) -> list[dict]:
        """Tavily first (better quality), DDG fallback (unlimited free)."""
        results = self._tavily_results(query, max_results)
        if results:
            return results
        return self._ddg_results(query, max_results)

    @staticmethod
    def _parse_json(text: str):
        text = text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(text)

    def find_companies(self, industry: str, location: str, count: int,
                       exclude_names: list[str] = None) -> list[dict]:
        exclude_block = ''
        if exclude_names:
            exclude_block = ('DO NOT include these already-tried businesses: '
                             + ', '.join(exclude_names[:20]) + '\n')

        snippets = []
        for query in (
            f'best {industry} in {location} official website',
            f'top {industry} {location} contact details',
        ):
            for r in self._results(query, 10):
                snippets.append(
                    f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
                )
        if not snippets:
            return []

        context = '\n---\n'.join(snippets[:12])
        prompt = f"""You are a business research analyst. From these live web search results, identify up to {count} real {industry} businesses physically located in {location}.

{exclude_block}RULES:
- Only businesses whose result clearly indicates presence in {location}
- Prefer businesses with their own working website over big chains
- Do not invent businesses or websites

Search results:
{context}

Respond ONLY with a JSON array, maximum {count} items, no explanations:
[{{"company_name": "...", "website": "https://...", "description": "one short line", "contact_page": "https://..."}}]"""

        try:
            raw = self.router.generate(prompt)
        except LLMError as exc:
            logger.warning('Search discovery structuring LLM failed: %s', exc)
            return []

        try:
            companies = self._parse_json(raw)
        except json.JSONDecodeError:
            companies = repair_json_array(raw)
            if companies:
                logger.info('Salvaged %d companies from truncated LLM output', len(companies))

        if not companies:
            logger.warning('Search discovery produced no parseable companies')
            return []
        return companies[:count]

    def search_contacts(self, company_name: str, location: str) -> dict:
        snippets = [
            f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
            for r in self._results(f'"{company_name}" {location} phone email address contact', 8)
        ]
        if not snippets:
            return {}

        context = '\n---\n'.join(snippets)
        prompt = f"""From these live web search results about "{company_name}" ({location}), extract its publicly listed contact details.

RULES:
- Only details actually present in the results. Never guess.
- Prefer the {location} branch contact over other cities.
- Empty string if not found.

Respond ONLY with a JSON object, no explanations:
{{"email": "", "phone": "", "address": ""}}

Search results:
{context}"""

        try:
            return self._parse_json(self.router.generate(prompt))
        except (LLMError, json.JSONDecodeError, TypeError) as exc:
            logger.warning('Search contact extraction failed for %s: %s', company_name, exc)
            return {}

    def search_key_persons(self, company_name: str, location: str) -> dict:
        from .prompts import key_persons_search_prompt

        queries = (
            f'"{company_name}" {location} owner founder contact',
            f'"{company_name}" {location} "general manager" OR CEO',
            f'site:linkedin.com/in "{company_name}" {location}',
        )
        snippets, linkedin_urls = [], []
        for query in queries:
            results = self._results(query, 8)
            snippets.extend(
                f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
                for r in results
            )
            for r in results:
                href = (r.get('href') or '').split('?')[0].rstrip('/')
                if 'linkedin.com/in/' in href and href not in linkedin_urls:
                    linkedin_urls.append(href)

        if not snippets and not linkedin_urls:
            return {'persons': [], 'linkedin_urls': []}

        context = '\n---\n'.join(snippets[:12])
        prompt = key_persons_search_prompt(company_name, location, context, linkedin_urls[:8])

        try:
            data = self._parse_json(self.router.generate(prompt))
            return {'persons': data.get('persons', []), 'linkedin_urls': linkedin_urls[:8]}
        except (LLMError, json.JSONDecodeError, TypeError) as exc:
            logger.warning('Key person search failed for %s: %s', company_name, exc)
            return {'persons': [], 'linkedin_urls': linkedin_urls[:8]}