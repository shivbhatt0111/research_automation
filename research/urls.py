from django.urls import path

from .views import CreateResearchView, TaskListView, TaskStatusView

urlpatterns = [
    path('research/', CreateResearchView.as_view(), name='create-research'),
    path('research/list/', TaskListView.as_view(), name='task-list'),
    path('research/<int:task_id>/status/', TaskStatusView.as_view(), name='task-status'),
]