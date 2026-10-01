import json
import logging

from django.conf import settings

from .gemini_client import GeminiClient, GeminiClientError
from .llm_providers import LLMError, LLMRouter
from .crawler_service import CrawlerService
from .prompts import (
    company_discovery_prompt,
    contact_extraction_prompt,
    contact_search_prompt,
    key_persons_prompt,
    linkedin_profile_extraction_prompt,
)
from .search_service import SearchService
from .validators import (
    clean_address,
    clean_email,
    email_matches_official_domain,
    has_mx_record,
    is_relevant_email,
    linkedin_matches_name,
    person_email_matches_name,
    to_indian_format,
)

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    pass


class GeminiService:
    """Research operations. Gemini grounding for search when available,
    DDG + Groq as the always-free backbone."""

    def __init__(self):
        self.client = GeminiClient()
        self.router = LLMRouter()
        self.search = SearchService()

    @staticmethod
    def _parse_json(text: str):
        text = text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(text)


    def find_companies(self, industry: str, location: str, count: int,
                       exclude_names: list[str] = None, variation: int = 0) -> list[dict]:
        prompt = company_discovery_prompt(industry, location, count, exclude_names)

        try:
            # Discovery MUST be search-based - never accept model memory
            companies = self._parse_json(
                self.client.generate(prompt, use_search=True, require_search=True)
            )
            logger.info('Discovery via Gemini grounding succeeded')
            return companies[:count]
        except (GeminiClientError, json.JSONDecodeError, TypeError) as exc:
            logger.warning('Gemini discovery failed (%s), falling back to DDG search', exc)
        companies = self.search.find_companies(
            industry, location, count, exclude_names, variation=variation
        )
        if not companies:
            raise GeminiServiceError('Both Gemini grounding and DDG discovery failed')
        logger.info('Discovery via DDG search succeeded: %d companies', len(companies))
        return companies

    def extract_contacts(self, company_name: str, page_text: str, location: str = '') -> dict:
        prompt = contact_extraction_prompt(company_name, location or 'India', page_text)

        try:
            data = self._parse_json(self.router.generate(prompt))
        except (GeminiClientError, LLMError, json.JSONDecodeError, TypeError):
            logger.warning('AI contact extraction failed for %s', company_name)
            return {'email': '', 'phone': '', 'address': ''}

        email = clean_email(data.get('email', ''))
        if email and (not is_relevant_email(email) or not has_mx_record(email)):
            email = ''

        phone = to_indian_format(data.get('phone', '')) or ''
        address = clean_address(data.get('address', '')) or ''

        return {'email': email, 'phone': phone, 'address': address}

    def search_contacts(self, company_name: str, location: str,
                        official_domain: str = '') -> dict:
        """Contact rescue - STRICT OFFICIAL-ONLY. Rescued email must match
        the official domain; third-party sources are rejected."""
        data = self.search.search_contacts(company_name, location, official_domain) or {}

        if not any(data.values()) and getattr(settings, 'STRICT_OFFICIAL_ONLY', True) is False:
            # Loose mode only: Gemini grounding fallback allowed
            prompt = contact_search_prompt(company_name, location)
            try:
                data = self._parse_json(
                    self.client.generate(prompt, use_search=True, require_search=True)
                )
            except (GeminiClientError, json.JSONDecodeError, TypeError) as exc:
                logger.warning('Gemini contact search failed for %s: %s', company_name, exc)
                return {}

        email = clean_email(data.get('email', ''))
        if email and (not is_relevant_email(email) or not has_mx_record(email)):
            email = ''
        # STRICT: rescued email must belong to the official domain
        if email and official_domain and not email_matches_official_domain(email, official_domain):
            logger.info('Rescued email rejected (domain mismatch): %s', email)
            email = ''

        phone = to_indian_format(data.get('phone', '')) or ''
        address = clean_address(data.get('address', '')) or ''

        return {'email': email, 'phone': phone, 'address': address}







    def extract_key_persons(self, company_name: str, page_text: str,
                            linkedin_urls: list[str] = None) -> list[dict]:
        prompt = key_persons_prompt(company_name, page_text, linkedin_urls)

        try:
            data = self._parse_json(self.router.generate(prompt))
            persons = data.get('persons', [])
        except (GeminiClientError, LLMError, json.JSONDecodeError, TypeError):
            logger.warning('Key person extraction failed for %s', company_name)
            return []

        validated, seen = [], set()
        for person in persons[:5]:
            name = (person.get('name') or '').strip()
            if not name or len(name) < 3 or len(name) > 100:
                continue
            if name.lower() in seen:
                continue
            seen.add(name.lower())

            email = clean_email(person.get('email', ''))
            if email and (not is_relevant_email(email) or not has_mx_record(email)):
                email = ''
            if email and not person_email_matches_name(name, email):
                email = ''

            phone = to_indian_format(person.get('phone', '')) or ''

            linkedin = (person.get('linkedin_url') or '').split('?')[0].rstrip('/')
            if linkedin and not linkedin_matches_name(name, linkedin):
                linkedin = ''

            validated.append({
                'name': name,
                'designation': (person.get('designation') or '').strip()[:255],
                'email': email,
                'phone': phone,
                'linkedin_url': linkedin,
            })

        # Single person + single URL: assign ONLY after name validation
        if linkedin_urls and len(linkedin_urls) == 1 and len(validated) == 1:
            if not validated[0]['linkedin_url'] and linkedin_matches_name(
                    validated[0]['name'], linkedin_urls[0]):
                validated[0]['linkedin_url'] = linkedin_urls[0]

        return validated


    def search_key_persons(self, company_name: str, location: str) -> list[dict]:
        """Key persons from public web (directories, news, LinkedIn) when the
        website has no team info. Strict name validation on every field."""
        search_data = self.search.search_key_persons(company_name, location)
        raw_persons = search_data.get('persons', [])
        linkedin_urls = search_data.get('linkedin_urls', [])

        if not raw_persons:
            return []

        validated, seen = [], set()
        for person in raw_persons[:3]:
            name = (person.get('name') or '').strip()
            if not name or len(name) < 3 or len(name) > 100:
                continue
            if name.lower() in seen:
                continue
            seen.add(name.lower())

            email = clean_email(person.get('email', ''))
            if email and (not is_relevant_email(email) or not has_mx_record(email)):
                email = ''
            if email and not person_email_matches_name(name, email):
                email = ''

            phone = to_indian_format(person.get('phone', '')) or ''

            linkedin = (person.get('linkedin_url') or '').split('?')[0].rstrip('/')
            if linkedin and not linkedin_matches_name(name, linkedin):
                linkedin = ''

            validated.append({
                'name': name,
                'designation': (person.get('designation') or '').strip()[:255],
                'email': email,
                'phone': phone,
                'linkedin_url': linkedin,
            })

        # Auto-match only when name validation passes
        if linkedin_urls and len(validated) == 1:
            if not validated[0]['linkedin_url'] and linkedin_matches_name(
                    validated[0]['name'], linkedin_urls[0]):
                validated[0]['linkedin_url'] = linkedin_urls[0]

        return validated



    def extract_person_contacts_from_linkedin(self, person_name: str,
                                              linkedin_url: str) -> dict:
        """Opens a key person's LinkedIn profile (public content) and extracts
        email/phone IF the person published them there. Strict name match."""
        if not linkedin_url or 'linkedin.com/in/' not in linkedin_url:
            return {}

        try:
            page_text = CrawlerService().crawl_single_url(linkedin_url)
        except Exception as exc:
            logger.warning('LinkedIn crawl failed for %s: %s', person_name, exc)
            return {}

        if not page_text:
            return {}

        from .prompts import linkedin_profile_extraction_prompt
        prompt = linkedin_profile_extraction_prompt(person_name, page_text)

        try:
            data = self._parse_json(self.router.generate(prompt))
        except (GeminiClientError, LLMError, json.JSONDecodeError, TypeError):
            logger.warning('LinkedIn profile extraction failed for %s', person_name)
            return {}

        # Name match verify - AI ka is_match + hamara apna check
        if not data.get('is_match'):
            logger.info('LinkedIn profile name mismatch for %s, skipping', person_name)
            return {}

        email = clean_email(data.get('email', ''))
        if email and (not is_relevant_email(email) or not has_mx_record(email)):
            email = ''

        phone = to_indian_format(data.get('phone', '')) or ''

        return {'email': email, 'phone': phone}




