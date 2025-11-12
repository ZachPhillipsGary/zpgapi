"""API Views for Learning Plans"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from django.db import transaction

from apps.core.api import BaseModelViewSet
from .models import (
    LearningPlan, LearningPlanConcept, UserLearningPlan,
    UserPlanConceptProgress, LearningPlanCollaborator
)
from .serializers import *


class LearningPlanViewSet(BaseModelViewSet):
    """API for learning plans"""
    model = LearningPlan
    serializer_class = LearningPlanSerializer
    filterset_fields = ['language', 'difficulty_level', 'category', 'is_public', 'is_featured']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'enrollment_count', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Non-admin users only see public, published plans
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_public=True, is_published=True)
        return queryset

    @extend_schema(
        description="Get featured learning plans",
        parameters=[
            OpenApiParameter('language_id', OpenApiTypes.UUID, location=OpenApiParameter.QUERY),
        ]
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured learning plans"""
        queryset = self.get_queryset().filter(is_featured=True)

        language_id = request.query_params.get('language_id')
        if language_id:
            queryset = queryset.filter(language_id=language_id)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Add concepts to a learning plan",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'concepts': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'concept_id': {'type': 'string', 'format': 'uuid'},
                                'sequence_order': {'type': 'integer'},
                                'is_required': {'type': 'boolean'},
                                'notes': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def add_concepts(self, request, pk=None):
        """Add concepts to a learning plan (admin only)"""
        plan = self.get_object()
        concepts = request.data.get('concepts', [])

        created_concepts = []
        with transaction.atomic():
            for concept_data in concepts:
                plan_concept = LearningPlanConcept.objects.create(
                    learning_plan=plan,
                    concept_id=concept_data['concept_id'],
                    sequence_order=concept_data['sequence_order'],
                    is_required=concept_data.get('is_required', True),
                    notes=concept_data.get('notes', '')
                )
                created_concepts.append(plan_concept)

        serializer = LearningPlanConceptSerializer(created_concepts, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LearningPlanConceptViewSet(BaseModelViewSet):
    """API for learning plan concepts"""
    model = LearningPlanConcept
    serializer_class = LearningPlanConceptSerializer
    filterset_fields = ['learning_plan']
    permission_classes = [permissions.IsAdminUser]  # Admin only for direct access


class UserLearningPlanViewSet(BaseModelViewSet):
    """API for user learning plan enrollments"""
    model = UserLearningPlan
    serializer_class = UserLearningPlanSerializer
    filterset_fields = ['user_id', 'learning_plan', 'status']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)
        return queryset

    @extend_schema(description="Enroll in a learning plan")
    def create(self, request, *args, **kwargs):
        """Enroll user in a learning plan"""
        learning_plan_id = request.data.get('learning_plan_id')

        # Get total concept count
        concept_count = LearningPlanConcept.objects.filter(
            learning_plan_id=learning_plan_id
        ).count()

        # Create enrollment
        with transaction.atomic():
            enrollment = UserLearningPlan.objects.create(
                user_id=request.user.id,
                learning_plan_id=learning_plan_id,
                total_concept_count=concept_count
            )

            # Increment enrollment count on plan
            LearningPlan.objects.filter(id=learning_plan_id).update(
                enrollment_count=models.F('enrollment_count') + 1
            )

        serializer = self.get_serializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(description="Get user's enrolled plans")
    @action(detail=False, methods=['get'])
    def my_plans(self, request):
        """Get current user's enrolled plans"""
        enrollments = self.get_queryset().filter(user_id=request.user.id)
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)

    @extend_schema(description="Mark current concept as complete and move to next")
    @action(detail=True, methods=['post'])
    def complete_concept(self, request, pk=None):
        """Mark the current concept as complete"""
        enrollment = self.get_object()

        # Mark concept as complete
        enrollment.completed_concept_count += 1
        enrollment.current_concept_index += 1

        # Calculate progress
        if enrollment.total_concept_count > 0:
            enrollment.progress_percentage = (
                enrollment.completed_concept_count / enrollment.total_concept_count
            ) * 100

        # Check if completed
        if enrollment.completed_concept_count >= enrollment.total_concept_count:
            enrollment.status = 'completed'
            enrollment.completed_at = timezone.now()

        enrollment.save()

        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)


class UserPlanConceptProgressViewSet(BaseModelViewSet):
    """API for tracking progress on individual concepts within plans"""
    model = UserPlanConceptProgress
    serializer_class = UserPlanConceptProgressSerializer
    filterset_fields = ['user_learning_plan', 'concept', 'is_completed']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_learning_plan__user_id=self.request.user.id)
        return queryset

    @extend_schema(description="Update progress on a concept")
    def update(self, request, *args, **kwargs):
        """Update progress with activity tracking"""
        instance = self.get_object()

        # Update fields
        instance.stories_read = request.data.get('stories_read', instance.stories_read)
        instance.quizzes_passed = request.data.get('quizzes_passed', instance.quizzes_passed)
        instance.flashcards_reviewed = request.data.get('flashcards_reviewed', instance.flashcards_reviewed)
        instance.tutoring_sessions = request.data.get('tutoring_sessions', instance.tutoring_sessions)

        # Calculate completion percentage
        total_activities = (
            instance.stories_read +
            instance.quizzes_passed +
            instance.flashcards_reviewed +
            instance.tutoring_sessions
        )
        instance.completion_percentage = min(100, total_activities * 10)  # Rough calculation

        # Mark as complete if threshold met
        if instance.completion_percentage >= 80 and not instance.is_completed:
            instance.is_completed = True
            instance.completed_at = timezone.now()

        instance.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
