from django.urls import path

from .views import (
    CompanyDetailView,
    CreateEmailCampaignView,
    CreateResearchView,
    DataSearchView,
    EmailCampaignListView,
    EmailCampaignStatusView,
    IndustryStatsView,
    TaskDeleteView,
    TaskListView,
    TaskStatusView,
    CampaignDeleteView,
)

urlpatterns = [
    path('research/', CreateResearchView.as_view(), name='create-research'),
    path('research/list/', TaskListView.as_view(), name='task-list'),
    path('research/<int:task_id>/status/', TaskStatusView.as_view(), name='task-status'),
    path('research/<int:task_id>/delete/', TaskDeleteView.as_view(), name='task-delete'),

    # Email campaigns
    path('email-campaign/', CreateEmailCampaignView.as_view(), name='create-campaign'),
    path('email-campaign/list/', EmailCampaignListView.as_view(), name='campaign-list'),
    path('email-campaign/<int:campaign_id>/status/', EmailCampaignStatusView.as_view(), name='campaign-status'),

    # Data APIs
    path('data/stats/', IndustryStatsView.as_view(), name='data-stats'),
    path('data/<int:company_id>/', CompanyDetailView.as_view(), name='company-detail'),
    path('data/', DataSearchView.as_view(), name='data-search'),
    path('delete-campaign/<int:campaign_id>/', CampaignDeleteView.as_view(), name='campaign-delete'),
]