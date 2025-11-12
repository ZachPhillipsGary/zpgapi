"""
Views for AI Prompt Management API
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from apps.core.api import BaseModelViewSet
from .models import (
    AIPromptTemplate,
    AIPromptVersion,
    AIPromptAssignment,
    AIPromptUsageLog
)
from .serializers import (
    AIPromptTemplateSerializer,
    AIPromptTemplateListSerializer,
    AIPromptVersionSerializer,
    AIPromptAssignmentSerializer,
    AIPromptUsageLogSerializer
)
from .services import get_prompt_service


class AIPromptTemplateViewSet(BaseModelViewSet):
    """
    ViewSet for AI Prompt Templates.

    Endpoints:
    - GET /api/v1/ai-prompts/templates/ - List all templates
    - GET /api/v1/ai-prompts/templates/{id}/ - Get template details
    - POST /api/v1/ai-prompts/templates/ - Create new template
    - PATCH /api/v1/ai-prompts/templates/{id}/ - Update template
    - DELETE /api/v1/ai-prompts/templates/{id}/ - Delete template
    - GET /api/v1/ai-prompts/templates/{id}/analytics/ - Get analytics for template
    - GET /api/v1/ai-prompts/templates/by_type/{prompt_type}/ - Get templates by type
    """

    queryset = AIPromptTemplate.objects.all()
    serializer_class = AIPromptTemplateSerializer
    filterset_fields = ['prompt_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return AIPromptTemplateListSerializer
        return AIPromptTemplateSerializer

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """
        Get analytics for a specific template.

        GET /api/v1/ai-prompts/templates/{id}/analytics/
        """
        template = self.get_object()
        service = get_prompt_service()
        analytics = service.get_prompt_analytics(template.prompt_type)

        return Response(analytics)

    @action(detail=False, methods=['get'], url_path='by_type/(?P<prompt_type>[^/.]+)')
    def by_type(self, request, prompt_type=None):
        """
        Get template by prompt type.

        GET /api/v1/ai-prompts/templates/by_type/story_generation/
        """
        try:
            template = AIPromptTemplate.objects.get(
                prompt_type=prompt_type,
                is_active=True
            )
            serializer = self.get_serializer(template)
            return Response(serializer.data)
        except AIPromptTemplate.DoesNotExist:
            return Response(
                {'error': f'No active template found for type: {prompt_type}'},
                status=status.HTTP_404_NOT_FOUND
            )


class AIPromptVersionViewSet(BaseModelViewSet):
    """
    ViewSet for AI Prompt Versions.

    Endpoints:
    - GET /api/v1/ai-prompts/versions/ - List all versions
    - GET /api/v1/ai-prompts/versions/{id}/ - Get version details
    - POST /api/v1/ai-prompts/versions/ - Create new version
    - PATCH /api/v1/ai-prompts/versions/{id}/ - Update version
    - POST /api/v1/ai-prompts/versions/{id}/activate/ - Activate version
    - POST /api/v1/ai-prompts/versions/{id}/clone/ - Clone version
    """

    queryset = AIPromptVersion.objects.all()
    serializer_class = AIPromptVersionSerializer
    filterset_fields = ['prompt_template', 'is_active', 'is_archived']
    search_fields = ['version_name', 'change_notes']
    ordering_fields = ['version_number', 'created_at', 'usage_count']

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activate a specific version.

        POST /api/v1/ai-prompts/versions/{id}/activate/
        """
        version = self.get_object()

        if version.is_archived:
            return Response(
                {'error': 'Cannot activate an archived version'},
                status=status.HTTP_400_BAD_REQUEST
            )

        version.is_active = True
        version.save()  # This will deactivate other versions

        serializer = self.get_serializer(version)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """
        Clone a version to create a new one.

        POST /api/v1/ai-prompts/versions/{id}/clone/
        Body: {"version_name": "New name", "change_notes": "Cloned from..."}
        """
        source_version = self.get_object()

        version_name = request.data.get('version_name', f"{source_version.version_name} (Copy)")
        change_notes = request.data.get('change_notes', f"Cloned from v{source_version.version_number}")

        new_version = AIPromptVersion.objects.create(
            prompt_template=source_version.prompt_template,
            version_name=version_name,
            prompt_text=source_version.prompt_text,
            is_active=False,
            is_archived=False,
            change_notes=change_notes,
            created_by=request.data.get('created_by', '')
        )

        serializer = self.get_serializer(new_version)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AIPromptAssignmentViewSet(BaseModelViewSet):
    """
    ViewSet for AI Prompt Assignments (A/B Testing).

    Endpoints:
    - GET /api/v1/ai-prompts/assignments/ - List all assignments
    - GET /api/v1/ai-prompts/assignments/{id}/ - Get assignment details
    - POST /api/v1/ai-prompts/assignments/ - Create new assignment
    - PATCH /api/v1/ai-prompts/assignments/{id}/ - Update assignment
    - DELETE /api/v1/ai-prompts/assignments/{id}/ - Delete assignment
    - GET /api/v1/ai-prompts/assignments/for_user/{user_id}/ - Get assignments for user
    """

    queryset = AIPromptAssignment.objects.all()
    serializer_class = AIPromptAssignmentSerializer
    filterset_fields = ['prompt_template', 'user_id', 'is_active', 'test_group_name']
    search_fields = ['user_id', 'notes']
    ordering_fields = ['assigned_at', 'created_at']

    @action(detail=False, methods=['get'], url_path='for_user/(?P<user_id>[^/.]+)')
    def for_user(self, request, user_id=None):
        """
        Get all active assignments for a specific user.

        GET /api/v1/ai-prompts/assignments/for_user/{user_id}/
        """
        assignments = AIPromptAssignment.objects.filter(
            user_id=user_id,
            is_active=True
        ).select_related('prompt_template', 'prompt_version')

        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)


class AIPromptUsageLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for AI Prompt Usage Logs (Analytics).

    Endpoints:
    - GET /api/v1/ai-prompts/usage-logs/ - List usage logs
    - GET /api/v1/ai-prompts/usage-logs/{id}/ - Get log details
    - GET /api/v1/ai-prompts/usage-logs/stats/ - Get usage statistics
    """

    queryset = AIPromptUsageLog.objects.all()
    serializer_class = AIPromptUsageLogSerializer
    filterset_fields = ['prompt_version', 'user_id', 'success', 'ai_model']
    search_fields = ['user_id', 'error_message']
    ordering_fields = ['created_at', 'generation_time']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get usage statistics.

        GET /api/v1/ai-prompts/usage-logs/stats/
        Query params:
        - prompt_type: Filter by prompt type
        - days: Number of days to analyze (default: 7)
        - user_id: Filter by user
        """
        prompt_type = request.query_params.get('prompt_type')
        days = int(request.query_params.get('days', 7))
        user_id = request.query_params.get('user_id')

        # Build filter
        filters = Q(created_at__gte=timezone.now() - timedelta(days=days))

        if prompt_type:
            filters &= Q(prompt_version__prompt_template__prompt_type=prompt_type)

        if user_id:
            filters &= Q(user_id=user_id)

        # Get aggregated stats
        logs = AIPromptUsageLog.objects.filter(filters)

        total_uses = logs.count()
        successful_uses = logs.filter(success=True).count()
        failed_uses = logs.filter(success=False).count()

        avg_time = logs.aggregate(avg=Avg('generation_time'))['avg']
        avg_tokens = logs.filter(token_count__isnull=False).aggregate(avg=Avg('token_count'))['avg']

        # Stats by prompt type
        by_type = logs.values(
            'prompt_version__prompt_template__prompt_type',
            'prompt_version__prompt_template__name'
        ).annotate(
            total=Count('id'),
            successes=Count('id', filter=Q(success=True)),
            avg_time=Avg('generation_time')
        ).order_by('-total')

        # Stats by version
        by_version = logs.values(
            'prompt_version__id',
            'prompt_version__version_number',
            'prompt_version__prompt_template__name'
        ).annotate(
            total=Count('id'),
            successes=Count('id', filter=Q(success=True)),
            avg_time=Avg('generation_time')
        ).order_by('-total')[:10]

        return Response({
            'period_days': days,
            'total_uses': total_uses,
            'successful_uses': successful_uses,
            'failed_uses': failed_uses,
            'success_rate': (successful_uses / total_uses * 100) if total_uses > 0 else 0,
            'avg_generation_time': float(avg_time) if avg_time else None,
            'avg_token_count': float(avg_tokens) if avg_tokens else None,
            'by_prompt_type': list(by_type),
            'top_versions_by_usage': list(by_version),
        })
