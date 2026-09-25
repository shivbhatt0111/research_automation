import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ResearchTask
from .serializers import CreateResearchSerializer, ResearchTaskSerializer
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