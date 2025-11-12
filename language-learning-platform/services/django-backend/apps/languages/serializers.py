"""Serializers for Language models"""
from rest_framework import serializers
from apps.core.api import BaseModelSerializer
from .models import (
    Language, UserLanguage, Concept, Word, UserConceptProgress,
    Flashcard, Story, Quiz, QuizAttempt, SpacedRepetitionCard,
    ReviewLog, TutoringSession, AIGenerationJob, UserPreferences
)


class LanguageSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = Language


class UserLanguageSerializer(BaseModelSerializer):
    language = LanguageSerializer(read_only=True)
    language_id = serializers.UUIDField(write_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = UserLanguage


class WordSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = Word


class ConceptSerializer(BaseModelSerializer):
    language = LanguageSerializer(read_only=True)
    words = WordSerializer(many=True, read_only=True)
    word_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Concept

    def get_word_count(self, obj):
        return obj.words.count()


class UserConceptProgressSerializer(BaseModelSerializer):
    concept = ConceptSerializer(read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = UserConceptProgress


class FlashcardSerializer(BaseModelSerializer):
    concept_title = serializers.CharField(source='concept.title', read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = Flashcard


class StorySerializer(BaseModelSerializer):
    concept_title = serializers.CharField(source='concept.title', read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = Story


class QuizSerializer(BaseModelSerializer):
    concept_title = serializers.CharField(source='concept.title', read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Quiz

    def get_question_count(self, obj):
        return len(obj.questions) if obj.questions else 0


class QuizAttemptSerializer(BaseModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = QuizAttempt


class SpacedRepetitionCardSerializer(BaseModelSerializer):
    flashcard_data = FlashcardSerializer(source='flashcard', read_only=True)
    word_data = WordSerializer(source='word', read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = SpacedRepetitionCard


class ReviewLogSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = ReviewLog


class TutoringSessionSerializer(BaseModelSerializer):
    language_name = serializers.CharField(source='language.name', read_only=True)
    concept_title = serializers.CharField(source='concept.title', read_only=True, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = TutoringSession


class AIGenerationJobSerializer(BaseModelSerializer):
    language_name = serializers.CharField(source='language.name', read_only=True)
    concept_title = serializers.CharField(source='concept.title', read_only=True, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = AIGenerationJob


class UserPreferencesSerializer(BaseModelSerializer):
    native_language_name = serializers.CharField(source='native_language.name', read_only=True, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = UserPreferences
