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
        self._tavily_client = None
        self._tavily_index = -1

    @property
    def tavily(self):
        keys = [k for k in getattr(settings, 'TAVILY_API_KEYS', []) if k]
        if not keys:
            return None
        if self._tavily_client is None:
            try:
                from tavily import TavilyClient
                # Round-robin: har SearchService instance alag key se start
                self._tavily_index = (self._tavily_index + 1) % len(keys)
                self._tavily_client = TavilyClient(api_key=keys[self._tavily_index])
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
                       exclude_names: list[str] = None, variation: int = 0) -> list[dict]:
        exclude_block = ''
        if exclude_names:
            exclude_block = ('DO NOT include these already-tried businesses: '
                             + ', '.join(exclude_names[:20]) + '\n')

        # Clean industry string for better search engine matching
        clean_industry = industry.replace("with official website", "").replace("companies", "").strip()
        
        # Aggressive negative filters to block directories at the search engine level
        negative_filters = "-indiamart -tradeindia -justdial -textileinfomedia -sulekha -exportersindia -zauba -tofler -directory -list"

        query_sets = [
            # Query 1: Direct official site focus
            (f'"{clean_industry}" "{location}" "contact us" email phone {negative_filters}',
             f'"{clean_industry}" manufacturers "{location}" official website .com OR .in {negative_filters}'),
            
            # Query 2: Domain-specific search
            (f'site:.in OR site:.com "{clean_industry}" "{location}" contact',
             f'"{clean_industry}" factory "{location}" email address {negative_filters}'),
        ]
        selected_queries = query_sets[variation % len(query_sets)]

        snippets = []
        for query in selected_queries:
            for r in self._results(query, 10):
                snippets.append(
                    f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
                )
        if not snippets:
            return []

        context = '\n---\n'.join(snippets[:12])
        
        prompt = f"""You are a strict business research analyst. From these live web search results, identify up to {count} real {clean_industry} businesses physically located in {location}.

{exclude_block}
CRITICAL RULES:
1. FORBIDDEN SOURCES: IGNORE ANY RESULT FROM directories or aggregators. 
2. WEBSITE: Must be the company's OWN official domain (e.g., companyname.com or companyname.in). If the result is a directory listing, DO NOT extract it. Return empty string "" for website if no official site is clearly found.
3. LOCATION: Must be physically in {location}.
4. Do not invent or guess data.

Search results:
{context}

Respond ONLY with a JSON array, maximum {count} items:
[{{"company_name": "...", "website": "https://...", "description": "...", "contact_page": "https://..."}}]"""

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



    def search_contacts(self, company_name: str, location: str,
                        official_domain: str = '') -> dict:
        # STRICT OFFICIAL-ONLY: scope queries to the official domain
        if official_domain:
            queries = (
                f'"{company_name}" contact site:{official_domain}',
                f'site:{official_domain} phone email address',
            )
        else:
            queries = (f'"{company_name}" {location} phone email address contact',)

        snippets = [
            f"{r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}"
            for q in queries
            for r in self._results(q, 8)
        ]
        if not snippets:
            return {}

        context = '\n---\n'.join(snippets)
        from .prompts import contact_search_prompt
        prompt = contact_search_prompt(company_name, location, official_domain)

        # Note: prompt already contains the full rules; context added below it
        prompt = prompt.replace(
            'Respond ONLY with a JSON object, no explanations:',
            f'Search results:\n{context}\n\nRespond ONLY with a JSON object, no explanations:'
        ) if 'Search results:' not in prompt else prompt

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