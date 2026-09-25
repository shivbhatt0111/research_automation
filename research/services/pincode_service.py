"""Pincode-based location verification via India Post public API."""
import logging
import re
import time

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

PINCODE_PATTERN = re.compile(r'\b([1-9]\d{5})\b')
API_URLS = [
    'https://api.postalpincode.in/pincode/{}',
    'http://api.postalpincode.in/pincode/{}',
]
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json',
}
CACHE_TTL = 60 * 60 * 24 * 7
REQUEST_TIMEOUT = 6
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1


def _fetch_offices(url: str, pincode: str) -> list[dict] | None:
    try:
        resp = requests.get(
            url.format(pincode), headers=HEADERS, timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        return data[0].get('PostOffice') or []
    except Exception as exc:
        logger.warning('Pincode API failed (%s, %s): %s', url.split('/')[2], pincode, exc)
        return None


def _fetch_pincode_info(pincode: str) -> list[dict] | None:
    """Returns offices list, empty list (pincode unknown), or None (API unavailable)."""
    cached = cache.get(f'pincode:{pincode}')
    if cached is not None:
        return cached

    for attempt in range(MAX_RETRIES):
        for url in API_URLS:
            offices = _fetch_offices(url, pincode)
            if offices is not None:
                if offices:
                    cache.set(f'pincode:{pincode}', offices, CACHE_TTL)
                return offices
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_SECONDS)

    return None


def pincode_matches_location(pincode: str, location: str) -> bool | None:
    """True = district matches location, False = confirmed different district,
    None = API unavailable, cannot verify."""
    from .validators import extract_location_keywords

    offices = _fetch_pincode_info(pincode)
    if offices is None:
        logger.warning('Pincode API unavailable for %s - cannot verify location', pincode)
        return None

    if not offices:
        return False

    tokens = extract_location_keywords(location)
    if not tokens:
        return True

    for office in offices:
        district = (office.get('District') or '').lower()
        if any(token in district for token in tokens):
            return True
    return False


def address_matches_location(address: str, location: str) -> bool | None:
    """True = verified in location, False = confirmed wrong city, None = cannot verify."""
    if not address or not location:
        return None

    match = PINCODE_PATTERN.search(address)
    if not match:
        return None

    return pincode_matches_location(match.group(1), location)