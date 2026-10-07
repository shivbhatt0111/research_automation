import logging
import re
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .campaign_tasks import run_email_campaign
from .models import CompanyContact, EmailCampaign, ResearchTask
from .serializers import (
    CompanyContactSerializer,
    CreateResearchSerializer,
    ResearchTaskSerializer,
)
from .services.email_campaign_service import EmailCampaignService
from .tasks import run_company_research


logger = logging.getLogger(__name__)


def _safe_int(value, default):
    """Convert a value to an integer and return the default on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class CreateResearchView(APIView):
    """POST /api/research/ — Start a new research task."""

    def post(self, request):
        serializer = CreateResearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = ResearchTask.objects.create(**serializer.validated_data)
        run_company_research.delay(task.id)

        return Response(
            {
                "message": "Research started",
                "task_id": task.id,
                "status_url": f"/api/research/{task.id}/status/",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class TaskStatusView(APIView):
    """GET /api/research/<task_id>/status/ — Poll research task progress."""

    def get(self, request, task_id: int):
        task = get_object_or_404(ResearchTask, id=task_id)
        return Response(ResearchTaskSerializer(task).data)


class TaskListView(APIView):
    """GET /api/research/list/ — Return all research tasks."""

    def get(self, request):
        tasks = ResearchTask.objects.all()[:50]
        return Response(ResearchTaskSerializer(tasks, many=True).data)


# Data viewing APIs: Filter database records without using AI.


class DataSearchView(APIView):
    """
    GET /api/data/?industry=food&location=pune&search=reliance&page=1&page_size=20

    Filter company records from the database without using AI.
    """

    def get(self, request):
        industry = request.query_params.get("industry", "").strip()
        location = request.query_params.get("location", "").strip()
        search = request.query_params.get("search", "").strip()
        verified = request.query_params.get("verified", "").strip()
        has_email = request.query_params.get("has_email", "").strip()
        has_phone = request.query_params.get("has_phone", "").strip()

        page = _safe_int(request.query_params.get("page"), 1)
        page_size = _safe_int(request.query_params.get("page_size"), 20)

        page = max(1, page)
        page_size = min(100, max(1, page_size))

        queryset = (
            CompanyContact.objects.filter(
                Q(email__gt="") |
                Q(phone__gt="") |
                Q(address__gt="")
            )
            .select_related("task")
            .order_by("-id")
        )

        if industry:
            queryset = queryset.filter(
                task__industry__icontains=industry
            )

        if location:
            queryset = queryset.filter(
                Q(task__location__icontains=location) |
                Q(address__icontains=location)
            )

        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) |
                Q(website__icontains=search) |
                Q(email__icontains=search)
            )

        if verified == "true":
            queryset = queryset.filter(is_verified=True)
        elif verified == "false":
            queryset = queryset.filter(is_verified=False)

        if has_email == "true":
            queryset = queryset.exclude(email="")

        if has_phone == "true":
            queryset = queryset.exclude(phone="")

        total = queryset.count()

        offset = (page - 1) * page_size
        contacts = queryset[offset:offset + page_size]

        return Response(
            {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "filters_applied": {
                    "industry": industry,
                    "location": location,
                    "search": search,
                    "verified": verified,
                },
                "results": CompanyContactSerializer(
                    contacts,
                    many=True,
                ).data,
            }
        )


class IndustryStatsView(APIView):
    """GET /api/data/stats/ — Return database statistics by industry and location."""

    def get(self, request):
        rows = (
            CompanyContact.objects
            .filter(
                Q(email__gt="") |
                Q(phone__gt="") |
                Q(address__gt="")
            )
            .values("task__industry", "task__location")
            .annotate(companies=Count("id"))
            .order_by("-companies")
        )

        datasets = []

        for row in rows:
            industry = row["task__industry"]

            queryset = CompanyContact.objects.filter(
                task__industry=industry
            )

            datasets.append(
                {
                    "industry": industry,
                    "location": row["task__location"],
                    "companies": row["companies"],
                    "emails": queryset.exclude(email="").count(),
                    "phones": queryset.exclude(phone="").count(),
                }
            )

        return Response(
            {
                "total_datasets": len(datasets),
                "datasets": datasets,
            }
        )


class CompanyDetailView(APIView):
    """GET /api/data/<company_id>/ — Return complete company details and key persons."""

    def get(self, request, company_id: int):
        contact = get_object_or_404(
            CompanyContact,
            id=company_id,
        )

        return Response(
            CompanyContactSerializer(contact).data
        )


class TaskDeleteView(APIView):
    """
    GET or DELETE /api/delete-task/<task_id>/

    Delete a research task and all related data permanently.
    """

    def get(self, request, task_id: int):
        return self._delete(request, task_id)

    def delete(self, request, task_id: int):
        return self._delete(request, task_id)

    def _delete(self, request, task_id: int):
        task = get_object_or_404(
            ResearchTask,
            id=task_id,
        )

        contacts_count = task.contacts.count()

        persons_count = sum(
            contact.key_persons.count()
            for contact in task.contacts.all()
        )

        task.delete()

        logger.info(
            "Deleted task %d (%d contacts, %d key persons)",
            task_id,
            contacts_count,
            persons_count,
        )

        return Response(
            {
                "message": (
                    f"Task {task_id} and all related data "
                    "were deleted successfully"
                ),
                "deleted_task": task_id,
                "deleted_contacts": contacts_count,
                "deleted_key_persons": persons_count,
            }
        )


class CreateEmailCampaignView(APIView):
    """
    POST /api/email-campaign/

    Start an email campaign after performing a daily quota check.
    """

    def post(self, request):
        industry = request.data.get("industry", "").strip()
        location = request.data.get("location", "").strip()
        number_of_emails = request.data.get("number_of_emails")

        if not industry or not location:
            return Response(
                {
                    "error": "Industry and location are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        number_of_emails = _safe_int(
            number_of_emails,
            10,
        )

        number_of_emails = min(
            100,
            max(1, number_of_emails),
        )

        # Perform the initial daily quota check.
        service = EmailCampaignService()

        sent_today = service.sent_today_count()
        remaining_today = service.remaining_quota()

        if number_of_emails > remaining_today:
            return Response(
                {
                    "error": "Daily quota exceeded",
                    "message": (
                        f"You can send only {remaining_today} more emails today. "
                        f"Gmail daily limit: {settings.EMAIL_DAILY_LIMIT}. "
                        "The quota resets at midnight. "
                        "Reduce the number of emails or try again tomorrow."
                    ),
                    "daily_limit": settings.EMAIL_DAILY_LIMIT,
                    "sent_today": sent_today,
                    "remaining_today": remaining_today,
                    "requested": number_of_emails,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Check whether eligible companies are available.
        eligible = (
            CompanyContact.objects
            .filter(
                email__gt="",
                is_mail_sent=False,
            )
            .filter(
                Q(task__industry__icontains=industry) |
                Q(address__icontains=industry)
            )
            .filter(
                Q(task__location__icontains=location) |
                Q(address__icontains=location)
            )
            .count()
        )

        if eligible == 0:
            return Response(
                {
                    "error": "No eligible companies",
                    "message": (
                        "No companies match these filters that have an email "
                        "address and have not been contacted yet. "
                        "Run a research task first or adjust the filters."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine the scheduled email send date.
        now = timezone.localtime(timezone.now())

        send_hour, send_minute = map(
            int,
            settings.EMAIL_SEND_TIME.split(":"),
        )

        today_slot = now.replace(
            hour=send_hour,
            minute=send_minute,
            second=0,
            microsecond=0,
        )

        scheduled_date = (
            now.date()
            if now < today_slot
            else (now + timedelta(days=1)).date()
        )

        campaign = EmailCampaign.objects.create(
            industry=industry,
            location=location,
            requested_count=min(
                number_of_emails,
                eligible,
            ),
            scheduled_send_date=scheduled_date,
            status=EmailCampaign.Status.PENDING,
        )

        run_email_campaign.delay(campaign.id)

        scheduled_display = (
            scheduled_date.strftime("%d %b %Y")
            + f", {settings.EMAIL_SEND_TIME} IST"
        )

        return Response(
            {
                "message": (
                    "Email campaign started. Drafts are being generated "
                    "and will be sent at the scheduled time."
                ),
                "campaign_id": campaign.id,
                "companies_selected": min(
                    number_of_emails,
                    eligible,
                ),
                "eligible_companies": eligible,
                "scheduled_send_time": scheduled_display,
                "send_mode": settings.SEND_MODE,
                "status_url": (
                    f"/api/email-campaign/{campaign.id}/status/"
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class EmailCampaignStatusView(APIView):
    """
    GET /api/email-campaign/<campaign_id>/status/

    Return campaign progress and generated email drafts.
    """

    def get(self, request, campaign_id: int):
        campaign = get_object_or_404(
            EmailCampaign,
            id=campaign_id,
        )

        contacts = campaign.contacts.order_by("id")

        emails = [
            {
                "company_name": contact.company_name,
                "website": contact.website,
                "company_email": contact.email,
                "intended_recipient": contact.email,
                "sent_to": contact.mail_sent_to,
                "is_sent": contact.is_mail_sent,
                "subject": contact.email_draft_subject,
                "body": contact.email_draft_body,
            }
            for contact in contacts
        ]

        duration = None

        if campaign.duration_seconds is not None:
            minutes, seconds = divmod(
                campaign.duration_seconds,
                60,
            )

            hours, minutes = divmod(
                minutes,
                60,
            )

            duration = (
                f"{hours}:{minutes:02d}:{seconds:02d}"
                if hours
                else f"{minutes}:{seconds:02d}"
            )

        created = (
            campaign.created_at.astimezone(
                timezone.get_current_timezone()
            ).strftime("%d %b %Y, %I:%M:%S %p IST")
            if campaign.created_at
            else None
        )

        return Response(
            {
                "id": campaign.id,
                "industry": campaign.industry,
                "location": campaign.location,
                "status": campaign.status,
                "requested_count": campaign.requested_count,
                "sent_count": campaign.sent_count,
                "failed_count": campaign.failed_count,
                "scheduled_send_date": (
                    str(campaign.scheduled_send_date)
                    if campaign.scheduled_send_date
                    else None
                ),
                "send_mode": settings.SEND_MODE,
                "error_message": campaign.error_message,
                "created_at": created,
                "duration": duration,
                "emails": emails,
            }
        )


class EmailCampaignListView(APIView):
    """GET /api/email-campaign/list/ — Return all email campaigns."""

    def get(self, request):
        campaigns = EmailCampaign.objects.all()[:50]

        return Response(
            {
                "total": campaigns.count(),
                "campaigns": [
                    {
                        "id": campaign.id,
                        "industry": campaign.industry,
                        "location": campaign.location,
                        "status": campaign.status,
                        "requested_count": campaign.requested_count,
                        "sent_count": campaign.sent_count,
                        "failed_count": campaign.failed_count,
                        "scheduled_send_date": (
                            str(campaign.scheduled_send_date)
                            if campaign.scheduled_send_date
                            else None
                        ),
                    }
                    for campaign in campaigns
                ],
            }
        )


class CampaignDeleteView(APIView):
    """
    GET or DELETE /api/delete-campaign/<campaign_id>/

    Delete an email campaign while keeping the associated company
    contact records safe. Only the campaign relationship is removed.
    """

    def get(self, request, campaign_id: int):
        return self._delete(request, campaign_id)

    def delete(self, request, campaign_id: int):
        return self._delete(request, campaign_id)

    def _delete(self, request, campaign_id: int):
        campaign = get_object_or_404(
            EmailCampaign,
            id=campaign_id,
        )

        linked_contacts = campaign.contacts.all()
        contacts_count = linked_contacts.count()

        linked_contacts.update(
            campaign=None,
            is_mail_sent=False,
            email_draft_subject="",
            email_draft_body="",
            mail_draft_date=None,
        )

        campaign.delete()

        logger.info(
            "Deleted campaign %d (%d linked contacts unlinked)",
            campaign_id,
            contacts_count,
        )

        return Response(
            {
                "message": (
                    f"Campaign {campaign_id} deleted successfully"
                ),
                "deleted_campaign": campaign_id,
                "unlinked_contacts": contacts_count,
            }
        )
        
        
        
### frontend
from django.shortcuts import render
def home_view(request):
    return render(request, 'index.html')