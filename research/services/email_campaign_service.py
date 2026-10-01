"""Email campaign service: company analysis, AI draft generation,
and SMTP sending with daily quota protection."""
import logging

import requests
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .llm_providers import LLMError, LLMRouter
from .prompts import outreach_email_prompt

logger = logging.getLogger(__name__)


class EmailCampaignServiceError(Exception):
    pass


class EmailCampaignService:

    def __init__(self):
        self.router = LLMRouter()

    # ---------- Website content ----------

    def fetch_website_text(self, website_url: str) -> str:
        """Crawls the company website (JS rendering first, plain fetch as
        fallback). Returns readable text for AI analysis."""
        if not website_url:
            return ''

        try:
            from .crawler_service import CrawlerService
            crawled = CrawlerService().crawl_company_pages(website_url)
            if crawled.get('text'):
                return crawled['text'][:4000]
        except Exception as exc:
            logger.info('Crawl4AI failed for %s: %s', website_url, exc)

        # Plain fetch fallback
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(website_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'lxml')
                return soup.get_text(separator=' ', strip=True)[:4000]
        except Exception as exc:
            logger.info('Plain fetch failed for %s: %s', website_url, exc)

        return ''

    # ---------- AI draft ----------

    def generate_draft(self, company_name: str, industry: str,
                       location: str, website_url: str) -> dict | None:
        """Analyzes the company website and generates a personalized
        outreach email draft. Returns None when generation fails."""
        website_text = self.fetch_website_text(website_url)
        sender_info = {
            'company_name': settings.SENDER_COMPANY_NAME,
            'website': settings.SENDER_WEBSITE,
        }
        prompt = outreach_email_prompt(
            company_name, industry, location, website_text, sender_info
        )

        try:
            raw = self.router.generate(prompt)
        except LLMError as exc:
            logger.warning('Email draft generation failed for %s: %s', company_name, exc)
            return None

        import json
        try:
            text = raw.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning('Email draft JSON invalid for %s', company_name)
            return None

        subject = (data.get('subject') or '').strip()
        body = (data.get('body') or '').strip()
        if not subject or not body:
            logger.warning('Email draft incomplete for %s', company_name)
            return None

        return {'analysis': data.get('analysis', ''), 'subject': subject, 'body': body}

    # ---------- Signature ----------

    @staticmethod
    def _signature() -> str:
        return (
            f"\n\nBest regards,\n"
            f"{settings.SENDER_COMPANY_NAME} Team\n"
            f"Web: {settings.SENDER_WEBSITE}\n"
            f"Email: {settings.SENDER_EMAIL}\n"
            f"Phone: {settings.SENDER_PHONE}"
        )

    def build_final_body(self, draft_body: str, intended_recipient: str) -> str:
        """Appends the sender signature. In test mode, adds a notice line
        showing the real intended recipient."""
        body = draft_body.strip()
        if settings.SEND_MODE == 'test':
            body = (
                f"--- TEST EMAIL - Intended recipient: {intended_recipient} ---\n\n"
                + body
            )
        return body + self._signature()

    # ---------- Quota ----------

    @staticmethod
    def sent_today_count() -> int:
        from research.models import CompanyContact
        return CompanyContact.objects.filter(
            is_mail_sent=True,
            mail_sent_at__date=timezone.localdate(),
        ).count()

    @classmethod
    def remaining_quota(cls) -> int:
        return max(0, settings.EMAIL_DAILY_LIMIT - cls.sent_today_count())

    # ---------- Sending ----------

    def send_email(self, recipient: str, subject: str, body: str) -> None:
        """Sends one email via SMTP. Raises on failure."""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient],
        )
        email.send(fail_silently=False)