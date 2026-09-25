import re

import dns.resolver

_resolver = dns.resolver.Resolver()
_resolver.timeout = 3
_resolver.lifetime = 3

INDIA_PHONE_REGEX = re.compile(r'(?:\+?91[\s-]?)?[6-9]\d{9}\b')

EMAIL_COUNTRY_KEYWORDS = (
    'brazil', 'usa', 'canada', 'uk', 'europe', 'germany', 'france',
    'japan', 'china', 'australia', 'emea', 'apac', 'latam',
)

# Compliance/system mailboxes - never a business contact
BLOCKED_EMAIL_PREFIXES = (
    'accessibility', 'legal', 'privacy', 'webmaster', 'dpo',
    'abuse', 'noreply', 'no-reply', 'donotreply', 'postmaster',
)

# OTA/GDS booking-system domains - not the hotel's own email
BLOCKED_EMAIL_DOMAINS = (
    'hotelsgds.com', 'hotelonline.co', 'booking.com', 'agoda.com',
    'makemytrip.com', 'goibibo.com', 'expedia.com', 'synxis.com',
    'travelgds.com', 'rezserver.com', 'site minder', 'travelclick.com',
)

# Template/placeholder junk - literally written on some websites
PLACEHOLDER_EMAIL_KEYWORDS = (
    'your-business-name', 'yourname', 'your-email', 'youremail',
    'your-domain', 'example-email', 'email@example', 'name@example',
    'user@example', 'test@test', 'sample@', 'demo@demo',
    'username@domain', 'firstname.lastname', 'john.doe', 'jane.doe',
    'changeme', 'change-me', 'xxx@', '@yoursite', '@mywebsite',
)


def is_placeholder_email(email: str) -> bool:
    """Detects template emails like info@your-business-name.com that
    developers accidentally leave on production websites."""
    email = (email or '').lower()
    if any(keyword in email for keyword in PLACEHOLDER_EMAIL_KEYWORDS):
        return True

    # Suspicious domains that scream template
    domain = email.split('@')[-1]
    if domain.startswith(('your-', 'my-', 'example')) or domain.endswith(('-name.com', 'yourdomain.com')):
        return True

    # Numeric-heavy local part like 123456@domain.com
    local = email.split('@')[0]
    if local.isdigit():
        return True

    return False




# Auto-generated GDS IDs like "-44579-2@"
GDS_ID_PATTERN = re.compile(r'-\d{3,}-?\d*@')

PREFERRED_PREFIXES = (
    'info', 'contact', 'hello', 'sales', 'support',
    'enquiry', 'inquiry', 'office', 'marketing',
    'reservations', 'reservation', 'booking', 'frontoffice', 'front.office', 'fom',
)


def clean_email(raw: str) -> str:
    """Takes the first email when multiple are comma/semicolon separated."""
    raw = (raw or '').strip()
    for sep in (',', ';', ' / '):
        if sep in raw:
            raw = raw.split(sep)[0].strip()
    return raw.lower().strip()


def to_indian_format(phone: str) -> str | None:
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in '6789':
        return f'+91 {digits}'
    return None


def is_relevant_email(email: str) -> bool:
    email = (email or '').lower().strip()
    if '@' not in email:
        return False

    local, _, domain = email.partition('@')
    if not local or not domain:
        return False
    
    
    if is_placeholder_email(email):       
        return False

    # Compliance/system mailboxes (accessibility@, legal@, noreply@ ...)
    for prefix in BLOCKED_EMAIL_PREFIXES:
        if local == prefix or local.startswith(prefix + '.') or local.startswith(prefix + '-'):
            return False

    # OTA/GDS booking-system domains
    if any(bad in domain for bad in BLOCKED_EMAIL_DOMAINS):
        return False

    # Auto-generated GDS IDs
    if GDS_ID_PATTERN.search(email):
        return False

    # Foreign-office keywords
    if any(keyword in local for keyword in EMAIL_COUNTRY_KEYWORDS):
        return False

    return True


def has_mx_record(email: str) -> bool:
    domain = email.split('@')[-1]
    try:
        return bool(_resolver.resolve(domain, 'MX'))
    except Exception:
        return False


def pick_best_email(emails: list[str]) -> str:
    valid = [e for e in emails if is_relevant_email(e) and has_mx_record(e)]

    for email in valid:
        if email.split('@')[0] in PREFERRED_PREFIXES:
            return email

    for email in valid:
        local = email.split('@')[0]
        if any(local.startswith(p) for p in PREFERRED_PREFIXES):
            return email

    return valid[0] if valid else ''


COUNTRY_WORDS = {
    'india', 'indian', 'usa', 'united', 'states', 'uk',
    'kingdom', 'canada', 'australia', 'america',
}

LOCATION_ALIASES = {
    'gurgaon': 'gurugram',
    'bangalore': 'bengaluru',
    'pondicherry': 'puducherry',
    'trivandrum': 'thiruvananthapuram',
    'calcutta': 'kolkata',
    'madras': 'chennai',
    'bombay': 'mumbai',
}


def extract_location_keywords(location: str) -> list[str]:
    tokens = [t.strip().lower() for t in re.split(r'[,\s]+', location) if t.strip()]
    tokens = [t for t in tokens if len(t) > 2 and t not in COUNTRY_WORDS]
    expanded = []
    for token in tokens:
        expanded.append(token)
        if token in LOCATION_ALIASES:
            expanded.append(LOCATION_ALIASES[token])
    return expanded


def verify_location(page_text: str, location: str) -> bool:
    """Keyword-based fallback check. Pincode check is the primary validator."""
    keywords = extract_location_keywords(location)
    if not keywords:
        return True
    text = page_text.lower()
    return any(keyword in text for keyword in keywords)


NAME_NOISE_WORDS = {'pvt', 'private', 'limited', 'ltd', 'llp', 'llc', 'inc', 'corp', 'india'}


def normalize_company_name(name: str) -> str:
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', name.lower())
    tokens = [t for t in cleaned.split() if t not in NAME_NOISE_WORDS]
    return ''.join(tokens)


ADDRESS_JUNK_KEYWORDS = (
    'rates may apply', 'reply help', 'opt out', 'unsubscribe',
    'cookie', 'privacy policy', 'terms of', 'disclaimer', 'epfo',
    'registration details', 'google maps', 'all rights reserved',
    'copyright', 'newsletter', 'subscribe', 'login', 'sign up',
    'skip to content', 'contact us,', 'head office address',
    '@gmail.com', '@.com', 'email:', 
)

def clean_address(address: str) -> str | None:
    """Validates a raw string as a usable Indian postal address.

    Location matching is NOT done here - pincode verification
    (pincode_service.address_matches_location) handles that.
    """
    text = re.sub(r'\s+', ' ', address).strip(' ,|-')
    if not (30 <= len(text) <= 300):
        return None

    low = text.lower()
    if any(junk in low for junk in ADDRESS_JUNK_KEYWORDS):
        return None

    if not re.search(r'\b[1-9]\d{5}\b', text):
        return None

    return text


def normalize_website(url: str) -> str:
    domain = (url or '').replace('https://', '').replace('http://', '').replace('www.', '')
    return domain.split('/')[0].split('?')[0].lower()



# ---------- Key Person data validation ----------

PERSON_EMAIL_ROLE_PREFIXES = (
    'ceo', 'cto', 'cfo', 'director', 'admin', 'chairman',
    'president', 'founder', 'owner', 'hr', 'secretary', 'gm',
)


def linkedin_matches_name(name: str, linkedin_url: str) -> bool:
    """A LinkedIn URL belongs to a person ONLY when their name tokens
    appear in the profile slug. 'Manoj Jain' can never own '/in/pragati-patra'."""
    if not name or not linkedin_url or 'linkedin.com/in/' not in linkedin_url:
        return False

    slug = linkedin_url.rstrip('/').split('/in/')[-1]
    slug = re.sub(r'[^a-z-]', '', slug.lower())
    slug_tokens = {t for t in slug.split('-') if len(t) >= 3}
    if not slug_tokens:
        return False

    name_tokens = [
        t for t in re.sub(r'[^a-z\s]', '', name.lower()).split()
        if len(t) >= 3
    ]
    if not name_tokens:
        return False

    matches = sum(1 for t in name_tokens if any(t in st for st in slug_tokens))
    return matches >= 2 or (matches == 1 and len(name_tokens) == 1)


def person_email_matches_name(name: str, email: str) -> bool:
    """A person's email must contain their name token or a role prefix.
    Random company emails belong on the company record, not the person."""
    if not name or not email or '@' not in email:
        return False

    local = email.split('@')[0].lower()

    if any(role in local for role in PERSON_EMAIL_ROLE_PREFIXES):
        return True

    name_tokens = [
        t for t in re.sub(r'[^a-z\s]', '', name.lower()).split()
        if len(t) >= 3
    ]
    if not name_tokens:
        return True

    matches = sum(1 for t in name_tokens if t in local)
    return matches >= 2 or (matches == 1 and len(name_tokens) == 1)


# Business directories - these are listings, NOT official websites
DIRECTORY_DOMAINS = (
    'cataloxy.in', 'justdial.com', 'indiamart.com', 'tradeindia.com',
    'sulekha.com', 'yellowpages', 'glassdoor', 'indeed.com',
    'zaggor.com', 'compactleader.com', 'bizzlane.com',
    'idbf.in',                          # industrial directory portal
    'environmentclearance.nic.in',      # govt PDF portal
    'nic.in', 'gov.in',                 # sarkari portals - not company sites
    'mca.gov.in', 'zauba.com', 'tofler.in', 'falconebiz.com',
    'indianfilings.com', 'companycheck',
)

COMMON_EMAIL_PROVIDERS = (
    'gmail.com', 'yahoo.com', 'yahoo.co.in', 'hotmail.com', 'outlook.com',
    'rediffmail.com', 'live.com', 'icloud.com', 'protonmail.com',
)


def is_directory_url(url: str) -> bool:
    domain = normalize_website(url)
    return any(d in domain for d in DIRECTORY_DOMAINS)


def website_from_email(email: str) -> str:
    """Backfills official website from a non-provider email domain."""
    if not email or '@' not in email:
        return ''
    domain = email.split('@')[-1].lower()
    if domain in COMMON_EMAIL_PROVIDERS or is_placeholder_email(email):
        return ''
    return f'https://{domain}'
    
def verify_specific_location(address: str, location: str) -> bool | None:
    """Area-level verification: 'pithampur' address mein hona chahiye.
    Returns True/False/None (None = cannot verify)."""
    if not address or not location:
        return None

    addr_low = address.lower()
    keywords = extract_location_keywords(location)

    # Area keywords (pithampur, sanwer, vijay nagar etc.) - NOT generic city
    area_keywords = [k for k in keywords if k not in ('indore', 'road', 'industrial', 'area', 'india')]

    if not area_keywords:
        return None  # No specific area mentioned - city-level check

    # Agar area keyword address mein hai → verified
    for kw in area_keywords:
        if kw in addr_low:
            return True

    # Area keyword NAHI mila - lekin pincode toh check hi kar lo
    # (address mein sirf 'Indore' likha ho toh bhi FAIL - kyunki area specific mangi thi)
    return False