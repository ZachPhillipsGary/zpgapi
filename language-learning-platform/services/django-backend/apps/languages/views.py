"""API Views for Language models using reusable framework"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from datetime import datetime, timedelta

from apps.core.api import BaseModelViewSet
from .models import (
    Language, UserLanguage, Concept, Word, UserConceptProgress,
    Flashcard, Story, Quiz, QuizAttempt, SpacedRepetitionCard,
    ReviewLog, TutoringSession, AIGenerationJob, UserPreferences
)
from .serializers import *
from apps.spaced_repetition.anki_algorithm import AnkiAlgorithm


class LanguageViewSet(BaseModelViewSet):
    """API for managing languages"""
    model = Language
    serializer_class = LanguageSerializer
    filterset_fields = ['code', 'is_active']
    search_fields = ['name', 'native_name', 'code']
    ordering_fields = ['name', 'created_at']
    permission_classes = [permissions.AllowAny]  # Public read access

    @extend_schema(description="Get active languages only")
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active languages"""
        languages = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(languages, many=True)
        return Response(serializer.data)


class UserLanguageViewSet(BaseModelViewSet):
    """API for user language enrollment"""
    model = UserLanguage
    serializer_class = UserLanguageSerializer
    filterset_fields = ['user_id', 'language', 'proficiency_level']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by current user if not admin
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)
        return queryset

    @extend_schema(description="Enroll in a language")
    def create(self, request, *args, **kwargs):
        """Enroll user in a language"""
        data = request.data.copy()
        data['user_id'] = str(request.user.id)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConceptViewSet(BaseModelViewSet):
    """API for concepts"""
    model = Concept
    serializer_class = ConceptSerializer
    filterset_fields = ['language', 'concept_type', 'difficulty_level', 'is_published']
    search_fields = ['title', 'description', 'category']
    ordering_fields = ['title', 'difficulty_level', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only show published concepts to non-admins
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_published=True)
        return queryset

    @extend_schema(
        description="Get concepts by language with optional filtering",
        parameters=[
            OpenApiParameter('language_id', OpenApiTypes.UUID, location=OpenApiParameter.QUERY),
            OpenApiParameter('difficulty', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
        ]
    )
    @action(detail=False, methods=['get'])
    def by_language(self, request):
        """Get concepts for a specific language"""
        language_id = request.query_params.get('language_id')
        difficulty = request.query_params.get('difficulty')

        queryset = self.get_queryset()

        if language_id:
            queryset = queryset.filter(language_id=language_id)
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class WordViewSet(BaseModelViewSet):
    """API for words"""
    model = Word
    serializer_class = WordSerializer
    filterset_fields = ['concept', 'part_of_speech']
    search_fields = ['word', 'translation']


class FlashcardViewSet(BaseModelViewSet):
    """API for flashcards"""
    model = Flashcard
    serializer_class = FlashcardSerializer
    filterset_fields = ['concept', 'card_type', 'is_ai_generated']

    @extend_schema(description="Get flashcards for a concept")
    @action(detail=False, methods=['get'])
    def by_concept(self, request):
        """Get all flashcards for a concept"""
        concept_id = request.query_params.get('concept_id')
        if not concept_id:
            return Response({'error': 'concept_id is required'}, status=400)

        flashcards = self.get_queryset().filter(concept_id=concept_id)
        serializer = self.get_serializer(flashcards, many=True)
        return Response(serializer.data)


class StoryViewSet(BaseModelViewSet):
    """API for stories"""
    model = Story
    serializer_class = StorySerializer
    filterset_fields = ['concept', 'difficulty', 'is_ai_generated']
    search_fields = ['title', 'content']


class QuizViewSet(BaseModelViewSet):
    """API for quizzes"""
    model = Quiz
    serializer_class = QuizSerializer
    filterset_fields = ['concept', 'is_ai_generated']
    search_fields = ['title', 'description']


class QuizAttemptViewSet(BaseModelViewSet):
    """API for quiz attempts"""
    model = QuizAttempt
    serializer_class = QuizAttemptSerializer
    filterset_fields = ['user_id', 'quiz']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)
        return queryset


class SpacedRepetitionCardViewSet(BaseModelViewSet):
    """API for spaced repetition cards with Anki algorithm"""
    model = SpacedRepetitionCard
    serializer_class = SpacedRepetitionCardSerializer
    filterset_fields = ['user_id', 'card_state']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)
        return queryset

    @extend_schema(
        description="Get cards due for review",
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, default=20),
        ]
    )
    @action(detail=False, methods=['get'])
    def due(self, request):
        """Get cards that are due for review"""
        limit = int(request.query_params.get('limit', 20))
        now = timezone.now()

        cards = self.get_queryset().filter(
            user_id=request.user.id,
            due_date__lte=now
        ).order_by('due_date')[:limit]

        serializer = self.get_serializer(cards, many=True)
        return Response(serializer.data)

    @extend_schema(description="Submit a card review with Anki algorithm")
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Submit a review for a card (uses Anki algorithm)"""
        card = self.get_object()
        rating = request.data.get('rating')  # 1-4

        if not rating or rating not in [1, 2, 3, 4]:
            return Response({'error': 'rating must be 1, 2, 3, or 4'}, status=400)

        # Use Anki algorithm to calculate next review
        (
            new_state,
            new_ease,
            new_interval,
            new_reps,
            new_lapses,
            due_date
        ) = AnkiAlgorithm.calculate_next_review(
            rating=rating,
            card_state=card.card_state,
            ease_factor=card.ease_factor,
            interval_days=card.interval_days,
            repetitions=card.repetitions,
            lapses=card.lapses,
        )

        # Log the review
        ReviewLog.objects.create(
            user_id=request.user.id,
            srs_card=card,
            rating=rating,
            previous_ease_factor=card.ease_factor,
            new_ease_factor=new_ease,
            previous_interval_days=card.interval_days,
            new_interval_days=new_interval,
        )

        # Update the card
        card.card_state = new_state
        card.ease_factor = new_ease
        card.interval_days = new_interval
        card.repetitions = new_reps
        card.lapses = new_lapses
        card.due_date = due_date
        card.last_reviewed_at = timezone.now()
        card.save()

        serializer = self.get_serializer(card)
        return Response(serializer.data)

    @extend_schema(description="Get SRS statistics")
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get spaced repetition statistics for the user"""
        queryset = self.get_queryset()

        stats = {
            'new': queryset.filter(card_state='new').count(),
            'learning': queryset.filter(card_state='learning').count(),
            'review': queryset.filter(card_state='review').count(),
            'relearning': queryset.filter(card_state='relearning').count(),
            'total': queryset.count(),
        }

        # Reviews today
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stats['reviews_today'] = ReviewLog.objects.filter(
            user_id=request.user.id,
            reviewed_at__gte=today
        ).count()

        return Response(stats)


class TutoringSessionViewSet(BaseModelViewSet):
    """API for tutoring sessions"""
    model = TutoringSession
    serializer_class = TutoringSessionSerializer
    filterset_fields = ['user_id', 'language', 'session_type']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)
        return queryset


class AIGenerationJobViewSet(BaseModelViewSet):
    """API for AI content generation jobs"""
    model = AIGenerationJob
    serializer_class = AIGenerationJobSerializer
    filterset_fields = ['job_type', 'status', 'language']
    permission_classes = [permissions.IsAdminUser]  # Admin only


class UserPreferencesViewSet(BaseModelViewSet):
    """API for user preferences"""
    model = UserPreferences
    serializer_class = UserPreferencesSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return self.model.objects.filter(user_id=self.request.user.id)
        return super().get_queryset()

    @extend_schema(description="Get or create user preferences")
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's preferences"""
        prefs, created = UserPreferences.objects.get_or_create(
            user_id=request.user.id
        )
        serializer = self.get_serializer(prefs)
        return Response(serializer.data)
