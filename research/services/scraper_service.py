import logging
import re

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from .pincode_service import address_matches_location
from .validators import (
    INDIA_PHONE_REGEX,
    clean_address,
    extract_location_keywords,
    pick_best_email,
    to_indian_format,
    verify_location,
)

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

CONTACT_PATHS = ['/contact', '/contact-us', '/about', '/about-us', '/connect']
TEAM_PATHS = ['/team', '/our-team', '/leadership', '/management', '/about/team']
TEAM_LINK_KEYWORDS = ('team', 'leadership', 'management', 'people', 'founder', 'about-us', 'about/')
ASSET_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.js', '.css', '.svg')
BLOCKED_EMAIL_DOMAINS = ('example.com', 'sentry.io', 'wixpress.com', 'godaddy.com')


class ScraperService:
    """Extracts India-specific contact details from company websites."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(settings.SCRAPER_HEADERS)
        self.timeout = settings.SCRAPER_REQUEST_TIMEOUT
        self.max_pages = settings.SCRAPER_MAX_PAGES_PER_COMPANY

    def _fetch(self, url: str) -> BeautifulSoup | None:
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'lxml')
            logger.info('Non-200 (%d) from %s', response.status_code, url)
        except requests.RequestException as exc:
            logger.warning('Fetch failed for %s: %s', url, exc)
        return None

    @staticmethod
    def _clean_emails(emails: list[str]) -> list[str]:
        cleaned = set()
        for email in emails:
            email = email.lower().strip().strip('.')
            domain = email.split('@')[-1]
            if any(blocked in domain for blocked in BLOCKED_EMAIL_DOMAINS):
                continue
            if email.endswith(ASSET_EXTENSIONS) or len(email) > 100:
                continue
            cleaned.add(email)
        return list(cleaned)

    @staticmethod
    def _looks_like_india(text: str) -> bool:
        return bool(re.search(r'\b\d{6}\b', text) or 'india' in text.lower())

    def _candidate_urls(self, company: dict) -> list[str]:
        website = (company.get('website') or '').rstrip('/')
        if not website:
            return []
        urls = [website]
        if company.get('contact_page'):
            urls.append(company['contact_page'])
        urls.extend(f'{website}{path}' for path in CONTACT_PATHS)
        return urls[:self.max_pages]



    def fetch_team_data(self, company: dict, discovered_urls: list[str] = None) -> dict:
        """Fetches team pages. Returns text plus LinkedIn profile URLs found there."""
        website = (company.get('website') or '').rstrip('/')
        if not website:
            return {'text': '', 'linkedin_urls': []}

        urls = list(discovered_urls or [])
        urls.extend(f'{website}{p}' for p in TEAM_PATHS)
        urls = list(dict.fromkeys(urls))[:3]

        texts, linkedin_urls = [], []
        for url in urls:
            soup = self._fetch(url)
            if not soup:
                continue
            texts.append(soup.get_text(separator='\n', strip=True))
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'linkedin.com/in/' in href:
                    clean = href.split('?')[0].rstrip('/')
                    if clean not in linkedin_urls and len(linkedin_urls) < 10:
                        linkedin_urls.append(clean)

        return {'text': '\n'.join(texts)[:6000], 'linkedin_urls': linkedin_urls}




    @staticmethod
    def _extract_address(page_text: str, location: str) -> str:
        """Extracts address from lines. Pincode line anchors the block - up to
        2 preceding lines are joined (handles multi-line postal addresses)."""
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        candidates = []

        for i, line in enumerate(lines):
            if not re.search(r'\b[1-9]\d{5}\b', line):
                continue

            block = ', '.join(lines[max(0, i - 2):i + 1])
            if 30 <= len(block) <= 300:
                cleaned = clean_address(block)
                if cleaned:
                    candidates.append(cleaned)
                    continue

            if 30 <= len(line) <= 250:
                cleaned = clean_address(line)
                if cleaned:
                    candidates.append(cleaned)

        if not candidates:
            return ''

        keywords = extract_location_keywords(location) if location else []
        if keywords:
            for candidate in candidates:
                if any(k in candidate.lower() for k in keywords):
                    return candidate

        return min(candidates, key=len)

    def scrape_company(self, company: dict, location: str = '') -> dict:
        website_root = (company.get('website') or '').rstrip('/')
        result = {
            'email': '', 'phone': '', 'address': '',
            'source_url': '', 'confidence': 'LOW',
            'page_text': '', 'is_verified': False,
            'team_urls': [], 'address_check': None,
            'linkedin_urls': [],
        }
        all_text = ''

        for url in self._candidate_urls(company):
            soup = self._fetch(url)
            if soup is None:
                continue

            text = soup.get_text(separator=' ', strip=True)
            text_with_lines = soup.get_text(separator='\n', strip=True)
            all_text += text + '\n'

            emails, phones = [], []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().startswith('mailto:'):
                    emails.append(href.split('mailto:')[1].split('?')[0])
                elif href.lower().startswith('tel:'):
                    tel_number = href.split('tel:', 1)[1].strip() if len(href) > 4 else ''
                    phone = to_indian_format(tel_number) if tel_number else None
                    if phone:
                        phones.append(phone)
                elif 'linkedin.com/in/' in href:
                    clean = href.split('?')[0].rstrip('/')
                    if clean not in result['linkedin_urls'] and len(result['linkedin_urls']) < 10:
                        result['linkedin_urls'].append(clean)

            emails.extend(EMAIL_PATTERN.findall(text))
            phones.extend(
                to_indian_format(match.group(0))
                for match in INDIA_PHONE_REGEX.finditer(text)
            )
            phones = [p for p in phones if p]
            emails = self._clean_emails(emails)

            if not result.get('team_urls'):
                team_urls = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    label = link.get_text(strip=True).lower()
                    if any(k in href.lower() or k in label for k in TEAM_LINK_KEYWORDS):
                        if href.startswith('/'):
                            team_urls.append(website_root + href.split('#')[0])
                        elif href.startswith('http'):
                            team_urls.append(href.split('#')[0])
                result['team_urls'] = list(dict.fromkeys(team_urls))[:4]

            if not result['address']:
                address_tag = soup.find('address')
                if address_tag:
                    address_tag_text = address_tag.get_text(strip=True)[:500]
                    if self._looks_like_india(address_tag_text):
                        cleaned = clean_address(address_tag_text)
                        if cleaned:
                            result['address'] = cleaned

            if not result['address']:
                result['address'] = self._extract_address(text_with_lines, location)

            if emails or phones:
                result.update({
                    'email': pick_best_email(emails),
                    'phone': phones[0] if phones else '',
                    'source_url': url,
                    'confidence': 'HIGH' if emails else 'MEDIUM',
                })
                break

        result['page_text'] = all_text[:8000]

        if result['address'] and location:
            result['address_check'] = address_matches_location(result['address'], location)

        if result['address_check'] is not None:
            result['is_verified'] = result['address_check']
        elif location:
            result['is_verified'] = verify_location(all_text, location)
        else:
            result['is_verified'] = bool(all_text)

        return result