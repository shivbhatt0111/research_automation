from django.urls import path

from .views import (
    CompanyDetailView,
    CreateResearchView,
    DataSearchView,
    IndustryStatsView,
    TaskListView,
    TaskStatusView,
)

urlpatterns = [
    path('research/', CreateResearchView.as_view(), name='create-research'),
    path('research/list/', TaskListView.as_view(), name='task-list'),
    path('research/<int:task_id>/status/', TaskStatusView.as_view(), name='task-status'),

    # Data APIs — stats/detail order matters: static pehle, dynamic baad me
    path('data/stats/', IndustryStatsView.as_view(), name='data-stats'),
    path('data/<int:company_id>/', CompanyDetailView.as_view(), name='company-detail'),
    path('data/', DataSearchView.as_view(), name='data-search'),
]