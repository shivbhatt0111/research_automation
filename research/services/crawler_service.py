"""Crawl4AI-powered deep crawling with JS rendering.
Falls back gracefully when unavailable - scraper_service remains the base."""
import asyncio
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

CONTACT_PATHS = ['/contact', '/contact-us', '/about', '/about-us']
TEAM_PATHS = ['/team', '/our-team', '/leadership', '/management']


class CrawlerService:
    """Async JS-rendered crawling. One instance handles a full company."""

    def __init__(self):
        self.enabled = getattr(settings, 'CRAWL4AI_ENABLED', True)
        self.timeout_ms = getattr(settings, 'CRAWL4AI_TIMEOUT_MS', 25000)

    def _run(self, coro):
        """Runs async code safely from Celery worker threads."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(asyncio.run, coro).result(timeout=120)
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def _crawl_many(self, urls: list[str]) -> list[dict]:
        """Crawls multiple URLs with JS rendering. Returns [{url, html, text}]."""
        if not self.enabled:
            return []

        async def _crawl():
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

            browser_cfg = BrowserConfig(headless=True, browser_type='chromium')
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=self.timeout_ms,
                wait_for='body',
            )

            results = []
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                for url in urls[:4]:
                    try:
                        result = await crawler.arun(url=url, config=run_cfg)
                        if result.success and result.html:
                            results.append({
                                'url': url,
                                'html': result.html,
                                'text': (result.markdown or '')[:8000],
                            })
                    except Exception as exc:
                        logger.info('Crawl4AI failed for %s: %s', url, exc)
            return results

        try:
            return self._run(_crawl())
        except Exception as exc:
            logger.warning('Crawl4AI batch failed: %s', exc)
            return []

    def crawl_company_pages(self, website: str) -> dict:
        """Crawls homepage + contact + team pages with JS rendering.
        Returns combined text, LinkedIn URLs, and per-page results."""
        if not website:
            return {'text': '', 'linkedin_urls': [], 'pages': []}

        base = website.rstrip('/')
        urls = [base] + [f'{base}{p}' for p in CONTACT_PATHS + TEAM_PATHS]

        pages = self._crawl_many(urls)
        if not pages:
            return {'text': '', 'linkedin_urls': [], 'pages': []}

        all_text = '\n\n'.join(p['text'] for p in pages)
        linkedin_urls = []
        for p in pages:
            html = p['html']
            if not html or 'linkedin.com' not in html:
                continue
            import re
            for match in re.findall(r'https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_%-]+', html):
                clean = match.split('?')[0].rstrip('/')
                if clean not in linkedin_urls:
                    linkedin_urls.append(clean)

        return {
            'text': all_text[:15000],
            'linkedin_urls': linkedin_urls[:10],
            'pages': pages,
        }