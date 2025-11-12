"""
API Router Configuration

Automatically registers all ViewSets and generates OpenAPI/Swagger docs.
"""
from rest_framework import routers
from apps.languages.views import (
    LanguageViewSet, UserLanguageViewSet, ConceptViewSet, WordViewSet,
    FlashcardViewSet, StoryViewSet, QuizViewSet, QuizAttemptViewSet,
    SpacedRepetitionCardViewSet, TutoringSessionViewSet,
    AIGenerationJobViewSet, UserPreferencesViewSet
)
from apps.learning_plans.views import (
    LearningPlanViewSet, LearningPlanConceptViewSet,
    UserLearningPlanViewSet, UserPlanConceptProgressViewSet
)

# Create router
router = routers.DefaultRouter()

# Register Language app views
router.register(r'languages', LanguageViewSet, basename='language')
router.register(r'user-languages', UserLanguageViewSet, basename='user-language')
router.register(r'concepts', ConceptViewSet, basename='concept')
router.register(r'words', WordViewSet, basename='word')
router.register(r'flashcards', FlashcardViewSet, basename='flashcard')
router.register(r'stories', StoryViewSet, basename='story')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'quiz-attempts', QuizAttemptViewSet, basename='quiz-attempt')
router.register(r'srs-cards', SpacedRepetitionCardViewSet, basename='srs-card')
router.register(r'tutoring-sessions', TutoringSessionViewSet, basename='tutoring-session')
router.register(r'ai-jobs', AIGenerationJobViewSet, basename='ai-job')
router.register(r'user-preferences', UserPreferencesViewSet, basename='user-preferences')

# Register Learning Plans app views
router.register(r'learning-plans', LearningPlanViewSet, basename='learning-plan')
router.register(r'learning-plan-concepts', LearningPlanConceptViewSet, basename='learning-plan-concept')
router.register(r'user-learning-plans', UserLearningPlanViewSet, basename='user-learning-plan')
router.register(r'user-plan-progress', UserPlanConceptProgressViewSet, basename='user-plan-progress')
