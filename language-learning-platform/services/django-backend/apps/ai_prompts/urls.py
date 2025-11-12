"""
URL Configuration for AI Prompt Management API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AIPromptTemplateViewSet,
    AIPromptVersionViewSet,
    AIPromptAssignmentViewSet,
    AIPromptUsageLogViewSet
)

router = DefaultRouter()
router.register(r'templates', AIPromptTemplateViewSet, basename='ai-prompt-template')
router.register(r'versions', AIPromptVersionViewSet, basename='ai-prompt-version')
router.register(r'assignments', AIPromptAssignmentViewSet, basename='ai-prompt-assignment')
router.register(r'usage-logs', AIPromptUsageLogViewSet, basename='ai-prompt-usage-log')

app_name = 'ai_prompts'

urlpatterns = [
    path('', include(router.urls)),
]
