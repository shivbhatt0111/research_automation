"""Celery tasks for email campaigns: draft generation and scheduled sending."""
import logging
import time
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import CompanyContact, EmailCampaign
from .services.email_campaign_service import EmailCampaignService

logger = logging.getLogger(__name__)


def _scheduled_send_date(now) -> object:
    """If today's send time has passed, schedule for tomorrow. Otherwise today."""
    send_h, send_m = map(int, settings.EMAIL_SEND_TIME.split(':'))
    today_slot = now.replace(hour=send_h, minute=send_m, second=0, microsecond=0)
    if now < today_slot:
        return now.date()
    return (now + timedelta(days=1)).date()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_email_campaign(self, campaign_id: int):
    """Selects eligible companies, generates AI drafts for each, and marks
    the campaign as scheduled for the next send window."""
    campaign = EmailCampaign.objects.get(id=campaign_id)
    campaign.status = EmailCampaign.Status.DRAFTING
    campaign.save()

    service = EmailCampaignService()
    start_time = timezone.now()

    try:
        base_qs = CompanyContact.objects.filter(
            email__gt='',
            is_mail_sent=False,
        ).filter(
            Q(task__industry__icontains=campaign.industry)
            | Q(address__icontains=campaign.industry)
        ).filter(
            Q(task__location__icontains=campaign.location)
            | Q(address__icontains=campaign.location)
        ).order_by('id')

        available = base_qs.count()
        if available == 0:
            campaign.status = EmailCampaign.Status.FAILED
            campaign.error_message = 'No eligible companies found for these filters (companies must have an email and not be contacted before).'
            campaign.completed_at = timezone.now()
            campaign.duration_seconds = int((timezone.now() - start_time).total_seconds())
            campaign.save()
            logger.warning('[Campaign %d] No eligible companies', campaign_id)
            return

        selected_count = min(campaign.requested_count, available)
        companies = base_qs[:selected_count]

        drafted = 0
        for contact in companies:
            try:
                draft = service.generate_draft(
                    contact.company_name, campaign.industry,
                    campaign.location, contact.website,
                )
                if draft:
                    contact.email_draft_subject = draft['subject']
                    contact.email_draft_body = draft['body']
                    contact.mail_draft_date = campaign.scheduled_send_date
                    contact.campaign = campaign
                    contact.save(update_fields=[
                        'email_draft_subject', 'email_draft_body',
                        'mail_draft_date', 'campaign',
                    ])
                    drafted += 1
                else:
                    campaign.failed_count += 1
                    campaign.save(update_fields=['failed_count'])
            except Exception as exc:
                logger.exception('[Campaign %d] Draft failed for %s', campaign_id, contact.company_name)
                campaign.failed_count += 1
                campaign.save(update_fields=['failed_count'])

        if drafted == 0:
            campaign.status = EmailCampaign.Status.FAILED
            campaign.error_message = 'Draft generation failed for all selected companies.'
            campaign.completed_at = timezone.now()
            campaign.duration_seconds = int((timezone.now() - start_time).total_seconds())
            campaign.save()
            logger.error('[Campaign %d] All drafts failed', campaign_id)
            return

        campaign.sent_count = 0
        campaign.status = EmailCampaign.Status.SCHEDULED
        campaign.save()

        logger.info(
            '[Campaign %d] Drafting done: %d/%d drafted, scheduled for %s',
            campaign_id, drafted, selected_count, campaign.scheduled_send_date,
        )

    except Exception as exc:
        campaign.status = EmailCampaign.Status.FAILED
        campaign.error_message = str(exc)[:1000]
        campaign.completed_at = timezone.now()
        campaign.duration_seconds = int((timezone.now() - start_time).total_seconds())
        campaign.save()
        logger.exception('[Campaign %d] Failed: %s', campaign_id, exc)


@shared_task
def process_scheduled_emails():
    """Runs every minute via Celery Beat. When the configured send time is
    reached, sends all drafted emails whose schedule date has arrived."""
    now = timezone.localtime(timezone.now())
    send_h, send_m = map(int, settings.EMAIL_SEND_TIME.split(':'))
    target_minutes = send_h * 60 + send_m
    current_minutes = now.hour * 60 + now.minute

    if current_minutes < target_minutes:
        return

    drafts = CompanyContact.objects.filter(
        email_draft_body__gt='',
        is_mail_sent=False,
        mail_draft_date__lte=now.date(),
        email__gt='',
    ).select_related('campaign').order_by('mail_draft_date', 'id')

    if not drafts.exists():
        return

    service = EmailCampaignService()

    # Mark affected campaigns as sending
    campaign_ids = set(d.campaign_id for d in drafts if d.campaign_id)
    EmailCampaign.objects.filter(id__in=campaign_ids).update(
        status=EmailCampaign.Status.SENDING
    )

    sent_count = 0
    failed_count = 0

    for contact in drafts:
        # Runtime quota guard
        if service.sent_today_count() >= settings.EMAIL_DAILY_LIMIT:
            logger.warning('Daily email quota reached - pausing remaining sends')
            EmailCampaign.objects.filter(id__in=campaign_ids).exclude(
                status=EmailCampaign.Status.COMPLETED
            ).update(
                status=EmailCampaign.Status.PAUSED,
                error_message='Daily quota reached. Remaining emails stay drafted - create a new campaign tomorrow.',
            )
            break

        # Test mode routes to test inboxes; production sends to the company
        if settings.SEND_MODE == 'test':
            recipients = [r for r in settings.TEST_RECIPIENTS if r]
            if not recipients:
                logger.error('SEND_MODE is test but TEST_RECIPIENTS is empty')
                break
            recipient = recipients[sent_count % len(recipients)]
            subject = f"[TEST - Intended for: {contact.email}] {contact.email_draft_subject}"
        else:
            recipient = contact.email
            subject = contact.email_draft_subject

        final_body = service.build_final_body(contact.email_draft_body, contact.email)

        try:
            service.send_email(recipient, subject, final_body)
            contact.is_mail_sent = True
            contact.mail_sent_at = timezone.now()
            contact.mail_sent_to = recipient
            contact.save(update_fields=['is_mail_sent', 'mail_sent_at', 'mail_sent_to'])
            sent_count += 1
            logger.info('Email sent for %s -> %s', contact.company_name, recipient)
        except Exception as exc:
            failed_count += 1
            logger.error('Email send failed for %s: %s', contact.company_name, exc)

        time.sleep(settings.EMAIL_SEND_DELAY_SECONDS)

    # Update campaign counters and close finished campaigns
    for cid in campaign_ids:
        campaign = EmailCampaign.objects.filter(id=cid).first()
        if not campaign:
            continue
        campaign_contacts = campaign.contacts.all()
        campaign.sent_count = campaign_contacts.filter(is_mail_sent=True).count()
        campaign.failed_count = campaign_contacts.filter(
            is_mail_sent=False, email_draft_body__gt=''
        ).count()
        remaining = campaign_contacts.filter(
            is_mail_sent=False, email_draft_body__gt=''
        ).count()
        if remaining == 0:
            campaign.status = EmailCampaign.Status.COMPLETED
            campaign.completed_at = timezone.now()
            if campaign.created_at:
                campaign.duration_seconds = int(
                    (campaign.completed_at - campaign.created_at).total_seconds()
                )
        campaign.save()

    logger.info('Scheduled send done: %d sent, %d failed', sent_count, failed_count)