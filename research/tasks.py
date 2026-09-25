import logging
import re

from celery import shared_task, chord
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError
from django.utils import timezone

from .models import ResearchTask, CompanyContact, KeyPerson
from .services.gemini_client import GeminiClientError
from .services.gemini_service import GeminiService, GeminiServiceError
from .services.pincode_service import address_matches_location
from .services.scraper_service import EMAIL_PATTERN, ScraperService
from .services.validators import (
    COMMON_EMAIL_PROVIDERS,
    is_directory_url,
    normalize_company_name,
    normalize_website,
    pick_best_email,
    to_indian_format,
    verify_specific_location,
    website_from_email,
)

logger = logging.getLogger(__name__)

MAX_DISCOVERY_ROUNDS = 6
MAX_COMPANIES_PER_ROUND = 50
BUFFER_RATIO = 0.5
MIN_BUFFER = 6
ATTEMPTED_TTL_SECONDS = 60 * 60 * 3


def _attempted_key(task_id: int) -> str:
    return f'research:attempted:{task_id}'


def _mark_attempted(task_id: int, company: dict) -> None:
    """Records a business that was tried but yielded nothing - it will be
    excluded from future discovery rounds."""
    attempted = cache.get(_attempted_key(task_id), [])
    attempted.append({
        'name': company.get('company_name') or '',
        'domain': normalize_website(company.get('website') or ''),
    })
    cache.set(_attempted_key(task_id), attempted, timeout=ATTEMPTED_TTL_SECONDS)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_company_research(self, task_id: int):
    """Entry pipeline: starts round-based discovery, scraping and selection."""
    task = ResearchTask.objects.get(id=task_id)
    task.status = ResearchTask.Status.IN_PROGRESS
    task.save()

    discover_and_scrape.delay(task_id, 1)


@shared_task(max_retries=2, default_retry_delay=60)
def discover_and_scrape(task_id: int, round_number: int):
    """Discovers only the missing count with a buffer, excluding tried and
    already-collected businesses (global dedup across all tasks)."""
    task = ResearchTask.objects.get(id=task_id)
    contacts = list(task.contacts.all())
    contacts_with_data = sum(1 for c in contacts if c.email or c.phone or c.address)

    if contacts_with_data >= task.top_companies:
        finalize_research.delay(task_id)
        return

    if round_number > MAX_DISCOVERY_ROUNDS:
        finalize_research.delay(task_id)
        return

    needed = task.top_companies - contacts_with_data
    request_count = min(
        needed + max(MIN_BUFFER, int(needed * BUFFER_RATIO)),
        MAX_COMPANIES_PER_ROUND,
    )

    attempted = cache.get(_attempted_key(task_id), [])
    tried_names = set(task.contacts.values_list('normalized_name', flat=True))
    tried_names |= {normalize_company_name(a['name']) for a in attempted if a.get('name')}
    tried_domains = {
        normalize_website(w) for w in task.contacts.values_list('website', flat=True) if w
    }
    tried_domains |= {a['domain'] for a in attempted if a.get('domain')}

    # Global dedup: businesses collected in ANY past run are skipped, so every
    # run spends its full budget on net-new companies (1000-scale mode)
    if getattr(settings, 'SKIP_EXISTING_COMPANIES', True):
        existing = (
            CompanyContact.objects
            .exclude(task_id=task_id)
            .exclude(email='', phone='', address='')
            .values_list('normalized_name', 'website')
        )
        global_count = 0
        for existing_name, existing_website in existing:
            if existing_name:
                tried_names.add(existing_name)
            domain = normalize_website(existing_website)
            if domain:
                tried_domains.add(domain)
            global_count += 1
        if global_count:
            logger.info('[Task %d] Global dedup: %d already-collected businesses excluded', task_id, global_count)

    exclude_names = (
        [c.company_name for c in contacts]
        + [a['name'] for a in attempted if a.get('name')]
    )

    try:
        companies = GeminiService().find_companies(
            task.industry, task.location, request_count,
            exclude_names=exclude_names,
        )
    except (GeminiClientError, GeminiServiceError) as exc:
        # Partial results already collected - finalize with what we have
        # instead of throwing away good data with a FAILED status
        saved_count = sum(1 for c in task.contacts.all() if c.email or c.phone or c.address)
        if saved_count > 0:
            logger.warning(
                '[Task %d] Discovery failed (%s) but %d contacts already saved - finalizing with partial results',
                task_id, exc, saved_count,
            )
            task.error_message = f'Partial results: discovery ended early after {saved_count} contacts. ({str(exc)[:300]})'
            task.save()
            finalize_research.delay(task_id)
            return
        task.status = ResearchTask.Status.FAILED
        task.error_message = str(exc)[:1000]
        task.save()
        logger.error('[Task %d] Discovery failed with no data: %s', task_id, exc)
        return

    unique_companies, seen_names, seen_domains = [], set(), set()
    for company in companies:
        norm = normalize_company_name(company.get('company_name') or '')
        domain = normalize_website(company.get('website') or '')
        if not norm or norm in tried_names or norm in seen_names:
            continue
        if domain and domain in tried_domains:
            logger.info('[Task %d] Same-website duplicate skipped: %s', task_id, company.get('company_name'))
            continue
        seen_names.add(norm)
        if domain:
            seen_domains.add(domain)
        unique_companies.append(company)

    task.total_companies = task.contacts.count() + len(unique_companies)
    task.save()

    logger.info(
        '[Task %d] Round %d: requested %d, got %d new businesses (%d contacts so far)',
        task_id, round_number, request_count, len(unique_companies), contacts_with_data,
    )

    if not unique_companies:
        finalize_research.delay(task_id)
        return

    chord(
        (scrape_company_contact.s(task_id, company) for company in unique_companies)
    )(round_completed.s(task_id, round_number))


@shared_task
def round_completed(_: list, task_id: int, round_number: int) -> None:
    """After every round, check the pool and decide next round or finalize."""
    discover_and_scrape.delay(task_id, round_number + 1)


@shared_task(rate_limit='20/m', max_retries=1, default_retry_delay=30)
def scrape_company_contact(task_id: int, company: dict) -> None:
    """Chord-safe wrapper: a single business failure never breaks the round."""
    try:
        _process_company(task_id, company)
    except Exception as exc:
        logger.exception(
            '[Task %d] Unexpected error for %s', task_id, company.get('company_name')
        )
        _mark_attempted(task_id, company)


def _crawl_company(task_id: int, name: str, company: dict) -> tuple[str, list[str]]:
    """Crawl4AI first (JS rendering, deep pages). Returns (text, linkedin_urls)."""
    crawler_text, crawler_linkedin = '', []
    website = company.get('website') or ''
    if not website:
        return crawler_text, crawler_linkedin

    try:
        from .services.crawler_service import CrawlerService
        crawled = CrawlerService().crawl_company_pages(website)
        crawler_text = crawled['text']
        crawler_linkedin = crawled['linkedin_urls']
        if crawler_text:
            logger.info('[Task %d] Crawl4AI got %d chars for %s', task_id, len(crawler_text), name)
    except Exception as exc:
        logger.info('[Task %d] Crawl4AI unavailable for %s: %s', task_id, name, exc)
    return crawler_text, crawler_linkedin


def _regex_extract_from_text(text: str) -> tuple[list[str], list[str]]:
    """Free instant email/phone extraction from any text block."""
    emails = list(set(EMAIL_PATTERN.findall(text)))
    phones = [
        to_indian_format(match.group(0))
        for match in re.finditer(r'(?:\+?91[\s-]?)?[6-9]\d{9}\b', text)
    ]
    return emails, [p for p in phones if p]


def _process_company(task_id: int, company: dict) -> None:
    task = ResearchTask.objects.get(id=task_id)
    name = company.get('company_name') or 'Unknown'
    norm = normalize_company_name(name)

    # Garbage name filter: "Tiles Private Limited" type entries where the AI
    # only returned suffix words with no real company name
    meaningful_words = [w for w in norm if len(w) >= 3]
    if len(meaningful_words) < 2 or len(name.strip()) < 5:
        logger.info('[Task %d] Garbage/incomplete company name skipped: %r', task_id, name)
        _mark_attempted(task_id, company)
        return

    # Directory URLs (cataloxy/justdial/indiamart/govt portals etc.) are
    # listings, not official websites - clean them before any scraping
    if is_directory_url(company.get('website') or ''):
        logger.info(
            '[Task %d] Directory URL as website cleaned: %s',
            task_id, company.get('website'),
        )
        company['website'] = ''

    # Reuse data from ANY past task, but ONLY when the previous record's
    # address matches this task's area (Sanwer data never leaks into a
    # Pithampur task). Fully dynamic - works for any location strings.
    previous = (
        CompanyContact.objects
        .filter(normalized_name=norm)
        .exclude(task_id=task_id)
        .exclude(email='', phone='', address='')
        .prefetch_related('key_persons')
        .first()
    )

    if previous and task.location:
        prev_loc = verify_specific_location(previous.address, task.location)
        if prev_loc is False:
            logger.info(
                '[Task %d] Previous data area mismatch for %s (this task: %s, prev addr: %s) - fresh scrape',
                task_id, previous.company_name, task.location, (previous.address or '')[:80],
            )
            previous = None

    if previous:
        contact, _ = CompanyContact.objects.get_or_create(
            task_id=task_id,
            normalized_name=norm,
            defaults={
                'company_name': previous.company_name,
                'website': previous.website,
                'email': previous.email,
                'phone': previous.phone,
                'address': previous.address,
                'source_url': previous.source_url,
                'confidence': previous.confidence,
                'is_verified': previous.is_verified,
            },
        )
        for person in previous.key_persons.all():
            KeyPerson.objects.get_or_create(
                company=contact,
                name=person.name,
                defaults={
                    'designation': person.designation,
                    'email': person.email,
                    'phone': person.phone,
                    'linkedin_url': person.linkedin_url,
                },
            )
        _enrich_contact(contact, task.location)
        logger.info('[Task %d] Reused existing data for %s', task_id, previous.company_name)
        return

    # Layer 1: Crawl4AI first (JS rendering, contact+team pages in one pass)
    crawler_text, crawler_linkedin = _crawl_company(task_id, name, company)

    # Layer 2: Plain scraper (always runs - catches what crawler missed)
    scraper = ScraperService()
    scraped = scraper.scrape_company(company, location=task.location)
    team_urls = scraped.pop('team_urls', [])
    homepage_linkedin = list(dict.fromkeys(scraped.pop('linkedin_urls', []) + crawler_linkedin))
    page_text = crawler_text + '\n' + scraped.pop('page_text', '')

    # Layer 1.5: Quick regex on crawler text (free, instant - before any AI)
    if crawler_text and (not scraped['email'] or not scraped['phone']):
        crawler_emails, crawler_phones = _regex_extract_from_text(crawler_text)
        if crawler_emails and not scraped['email']:
            scraped['email'] = pick_best_email(crawler_emails)
        if crawler_phones and not scraped['phone']:
            scraped['phone'] = crawler_phones[0]

    # Crawler-only success ka source mark karo
    if crawler_text and not scraped['source_url'] and (scraped['email'] or scraped['phone']):
        scraped['source_url'] = company.get('website') or ''
        scraped['confidence'] = 'HIGH'

    # Layer 3: AI page extraction (Groq/Gemini router)
    needs_ai = not scraped['email'] or not scraped['address']
    if needs_ai and (page_text or not company.get('website')):
        ai_contacts = GeminiService().extract_contacts(name, page_text, location=task.location)
        if ai_contacts.get('email'):
            scraped['email'] = ai_contacts['email']
        scraped['phone'] = scraped['phone'] or ai_contacts.get('phone', '')
        scraped['address'] = scraped['address'] or ai_contacts.get('address', '')

    # Layer 4: Search rescue (Tavily/DDG/Gemini) - blocked/dead/no-website businesses
    if task.location and (not scraped['email'] or not scraped['phone'] or not scraped['address']):
        searched = GeminiService().search_contacts(name, task.location)
        if searched:
            scraped['email'] = scraped['email'] or searched.get('email', '')
            scraped['phone'] = scraped['phone'] or searched.get('phone', '')
            scraped['address'] = scraped['address'] or searched.get('address', '')

    if not scraped['email'] and not scraped['phone'] and not scraped['address']:
        logger.info('[Task %d] No usable data for %s, skipping save', task_id, name)
        _mark_attempted(task_id, company)
        return

    # Pincode-based wrong-city discard - hard reject on confirmed mismatch
    if scraped['address'] and task.location:
        check = scraped.get('address_check')
        if check is None:
            check = address_matches_location(scraped['address'], task.location)
        if check is False:
            logger.info(
                '[Task %d] Wrong-city business discarded: %s (address: %s)',
                task_id, name, scraped['address'][:120],
            )
            _mark_attempted(task_id, company)
            return

    # Area-level location check - dynamic for any location format
    # (pithampur / sanwer road / vijay nagar / koi bhi area keyword jo
    #  location string se extract hua, address mein hona chahiye)
    if scraped['address'] and task.location:
        area_check = verify_specific_location(scraped['address'], task.location)
        if area_check is False:
            logger.info(
                '[Task %d] Area-mismatch business discarded: %s (address: %s)',
                task_id, name, scraped['address'][:100],
            )
            _mark_attempted(task_id, company)
            return

    # Website backfill from email domain (Annova case: info@annovasolutions.com
    # with empty website -> https://annovasolutions.com)
    if not company.get('website') and scraped['email']:
        backfill = website_from_email(scraped['email'])
        if backfill:
            company['website'] = backfill
            if not scraped['source_url']:
                scraped['source_url'] = backfill
            logger.info('[Task %d] Website backfilled from email: %s', task_id, backfill)

    # Email-domain consistency: an email from an unrelated domain likely
    # belongs to a different company (Infoway India / DreamCyber Infoway case)
    email_domain = scraped['email'].split('@')[-1] if scraped['email'] else ''
    website_domain = normalize_website(company.get('website') or '')
    if (email_domain and website_domain
            and email_domain not in COMMON_EMAIL_PROVIDERS
            and email_domain not in website_domain
            and website_domain not in email_domain):
        logger.info(
            '[Task %d] Email domain mismatch for %s: %s vs %s - clearing email',
            task_id, name, scraped['email'], website_domain,
        )
        scraped['email'] = ''

    contact, _ = CompanyContact.objects.update_or_create(
        task_id=task_id,
        normalized_name=norm,
        defaults={
            'company_name': name,
            'website': company.get('website') or '',
            'email': scraped['email'],
            'phone': scraped['phone'],
            'address': scraped['address'],
            'source_url': scraped['source_url'],
            'confidence': scraped['confidence'],
            'is_verified': scraped['is_verified'],
        },
    )

    _extract_key_persons(task_id, contact, scraper, company, team_urls,
                         homepage_linkedin, page_text, task.location)


def _extract_key_persons(task_id: int, contact: CompanyContact, scraper: ScraperService,
                         company: dict, team_urls: list[str], homepage_linkedin: list[str],
                         page_text: str, location: str) -> None:
    """Team pages first (with LinkedIn URL matching), public web search as fallback."""
    team_data = scraper.fetch_team_data(company, team_urls)
    team_text = team_data['text'] or page_text
    linkedin_urls = list(dict.fromkeys(team_data['linkedin_urls'] + homepage_linkedin))[:10]

    persons = (
        GeminiService().extract_key_persons(
            contact.company_name, team_text, linkedin_urls=linkedin_urls
        )
        if team_text else []
    )

    if not persons:
        persons = GeminiService().search_key_persons(contact.company_name, location)
        source = 'web search'
    else:
        source = 'website'

    KeyPerson.objects.filter(company=contact).delete()
    for person in persons:
        KeyPerson.objects.create(company=contact, **person)
    if persons:
        logger.info(
            '[Task %d] Saved %d key persons for %s (via %s, %d linkedin urls)',
            task_id, len(persons), contact.company_name, source, len(linkedin_urls),
        )


def _enrich_contact(contact: CompanyContact, location: str) -> None:
    """Fills missing address/email of a reused contact via search. Also
    validates that enriched address belongs to this task's area."""
    if not location or (contact.address and contact.email):
        return

    searched = GeminiService().search_contacts(contact.company_name, location)
    if not searched:
        return

    updates = {}
    if not contact.address and searched.get('address'):
        if address_matches_location(searched['address'], location) is not False:
            updates['address'] = searched['address']
    if not contact.email and searched.get('email'):
        updates['email'] = searched['email']

    if updates:
        CompanyContact.objects.filter(id=contact.id).update(**updates)
        logger.info('Enriched contact %d with searched data', contact.id)


def _quality_score(contact: CompanyContact) -> int:
    """Higher score = more trustworthy and useful contact."""
    return (
        (100 if contact.is_verified else 0)
        + (20 if contact.email else 0)
        + (10 if contact.phone else 0)
        + (5 if contact.address else 0)
    )


@shared_task
def finalize_research(task_id: int) -> None:
    """Selects the best contacts and marks the task complete. Data stays in DB."""
    task = ResearchTask.objects.get(id=task_id)
    all_contacts = list(task.contacts.all())

    eligible = [c for c in all_contacts if c.email or c.phone or c.address]
    ranked = sorted(eligible, key=_quality_score, reverse=True)
    selected = ranked[:task.top_companies]
    selected_ids = {c.id for c in selected}

    CompanyContact.objects.filter(task=task).update(is_selected=False)
    CompanyContact.objects.filter(id__in=selected_ids).update(is_selected=True)

    task.emails_found = sum(1 for c in selected if c.email)
    task.phones_found = sum(1 for c in selected if c.phone)
    task.status = ResearchTask.Status.COMPLETED
    task.completed_at = timezone.now()
    task.save()

    logger.info(
        '[Task %d] Finalized: %d eligible out of %d pool, selected %d (requested %d)',
        task_id, len(eligible), len(all_contacts), len(selected), task.top_companies,
    )