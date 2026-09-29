import logging

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CompanyContact, ResearchTask
from .serializers import (
    CompanyContactSerializer,
    CreateResearchSerializer,
    ResearchTaskSerializer,
)
from .tasks import run_company_research

logger = logging.getLogger(__name__)


class CreateResearchView(APIView):
    """POST /api/research/ — start a new research task."""

    def post(self, request):
        serializer = CreateResearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = ResearchTask.objects.create(**serializer.validated_data)
        run_company_research.delay(task.id)

        return Response(
            {
                'message': 'Research started',
                'task_id': task.id,
                'status_url': f'/api/research/{task.id}/status/',
            },
            status=status.HTTP_202_ACCEPTED,
        )


class TaskStatusView(APIView):
    """GET /api/research/<task_id>/status/ — poll task progress."""

    def get(self, request, task_id: int):
        task = get_object_or_404(ResearchTask, id=task_id)
        return Response(ResearchTaskSerializer(task).data)


class TaskListView(APIView):
    """GET /api/research/list/ — all research tasks."""

    def get(self, request):
        tasks = ResearchTask.objects.all()[:50]
        return Response(ResearchTaskSerializer(tasks, many=True).data)


# ===== Data viewing APIs: DB se filtered data, no AI =====

def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class DataSearchView(APIView):
    """GET /api/data/?industry=food&location=pune&search=reliance&page=1&page_size=20
    DB se companies filter karke deta hai — no AI, instant."""

    def get(self, request):
        industry = request.query_params.get('industry', '').strip()
        location = request.query_params.get('location', '').strip()
        search = request.query_params.get('search', '').strip()
        verified = request.query_params.get('verified', '').strip()
        has_email = request.query_params.get('has_email', '').strip()
        has_phone = request.query_params.get('has_phone', '').strip()
        page = _safe_int(request.query_params.get('page'), 1)
        page_size = _safe_int(request.query_params.get('page_size'), 20)
        page = max(1, page)
        page_size = min(100, max(1, page_size))

        qs = CompanyContact.objects.filter(
            Q(email__gt='') | Q(phone__gt='') | Q(address__gt='')
        ).select_related('task').order_by('-id')

        if industry:
            qs = qs.filter(task__industry__icontains=industry)

        if location:
            qs = qs.filter(
                Q(task__location__icontains=location)
                | Q(address__icontains=location)
            )

        if search:
            qs = qs.filter(
                Q(company_name__icontains=search)
                | Q(website__icontains=search)
                | Q(email__icontains=search)
            )

        if verified == 'true':
            qs = qs.filter(is_verified=True)
        elif verified == 'false':
            qs = qs.filter(is_verified=False)

        if has_email == 'true':
            qs = qs.exclude(email='')
        if has_phone == 'true':
            qs = qs.exclude(phone='')

        total = qs.count()
        offset = (page - 1) * page_size
        contacts = qs[offset:offset + page_size]

        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'filters_applied': {
                'industry': industry, 'location': location,
                'search': search, 'verified': verified,
            },
            'results': CompanyContactSerializer(contacts, many=True).data,
        })


class IndustryStatsView(APIView):
    """GET /api/data/stats/ — DB summary: kis industry/location me kitna data hai."""

    def get(self, request):
        rows = (
            CompanyContact.objects
            .filter(Q(email__gt='') | Q(phone__gt='') | Q(address__gt=''))
            .values('task__industry', 'task__location')
            .annotate(companies=Count('id'))
            .order_by('-companies')
        )

        datasets = []
        for row in rows:
            industry = row['task__industry']
            qs = CompanyContact.objects.filter(task__industry=industry)
            datasets.append({
                'industry': industry,
                'location': row['task__location'],
                'companies': row['companies'],
                'emails': qs.exclude(email='').count(),
                'phones': qs.exclude(phone='').count(),
            })

        return Response({
            'total_datasets': len(datasets),
            'datasets': datasets,
        })


class CompanyDetailView(APIView):
    """GET /api/data/<company_id>/ — ek company ka pura detail + key persons."""

    def get(self, request, company_id: int):
        contact = get_object_or_404(CompanyContact, id=company_id)
        return Response(CompanyContactSerializer(contact).data)