"""Django Admin for Language models"""
from django.contrib import admin
from django.utils.html import format_html
from apps.core.api import BaseModelAdmin
from .models import (
    Language, UserLanguage, Concept, Word, UserConceptProgress,
    Flashcard, Story, Quiz, QuizAttempt, SpacedRepetitionCard,
    ReviewLog, TutoringSession, AIGenerationJob, UserPreferences
)


@admin.register(Language)
class LanguageAdmin(BaseModelAdmin):
    list_display_fields = ['name', 'code', 'native_name', 'is_active_badge', 'created_at']
    search_fields = ['name', 'code', 'native_name']
    list_filter_fields = ['is_active']

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'


@admin.register(UserLanguage)
class UserLanguageAdmin(BaseModelAdmin):
    list_display_fields = ['user_id', 'language', 'proficiency_level', 'daily_goal_minutes', 'total_study_time_minutes']
    search_fields = ['user_id']
    list_filter_fields = ['proficiency_level', 'language']
    autocomplete_fields = ['language']


class WordInline(admin.TabularInline):
    model = Word
    extra = 1
    fields = ['word', 'translation', 'pronunciation', 'part_of_speech']


@admin.register(Concept)
class ConceptAdmin(BaseModelAdmin):
    list_display_fields = ['title', 'language', 'concept_type', 'difficulty_level', 'is_published_badge', 'category']
    search_fields = ['title', 'description']
    list_filter_fields = ['language', 'concept_type', 'difficulty_level', 'is_published']
    autocomplete_fields = ['language']
    inlines = [WordInline]

    def is_published_badge(self, obj):
        if obj.is_published:
            return format_html('<span style="color: green;">✓ Published</span>')
        return format_html('<span style="color: gray;">○ Draft</span>')
    is_published_badge.short_description = 'Status'


@admin.register(Word)
class WordAdmin(BaseModelAdmin):
    list_display_fields = ['word', 'translation', 'concept', 'part_of_speech', 'frequency_rank']
    search_fields = ['word', 'translation']
    list_filter_fields = ['part_of_speech', 'concept__language']
    autocomplete_fields = ['concept']


@admin.register(Flashcard)
class FlashcardAdmin(BaseModelAdmin):
    list_display_fields = ['front_preview', 'concept', 'card_type', 'is_ai_generated_badge']
    search_fields = ['front', 'back']
    list_filter_fields = ['card_type', 'is_ai_generated', 'concept__language']
    autocomplete_fields = ['concept']

    def front_preview(self, obj):
        return obj.front[:50] + '...' if len(obj.front) > 50 else obj.front
    front_preview.short_description = 'Front'

    def is_ai_generated_badge(self, obj):
        if obj.is_ai_generated:
            return format_html('<span style="color: blue;">🤖 AI</span>')
        return format_html('<span style="color: gray;">✍️ Manual</span>')
    is_ai_generated_badge.short_description = 'Source'


@admin.register(Story)
class StoryAdmin(BaseModelAdmin):
    list_display_fields = ['title', 'concept', 'difficulty', 'estimated_reading_time', 'is_ai_generated_badge']
    search_fields = ['title', 'content']
    list_filter_fields = ['difficulty', 'is_ai_generated', 'concept__language']
    autocomplete_fields = ['concept']

    def is_ai_generated_badge(self, obj):
        if obj.is_ai_generated:
            return format_html('<span style="color: blue;">🤖 AI</span>')
        return format_html('<span style="color: gray;">✍️ Manual</span>')
    is_ai_generated_badge.short_description = 'Source'


@admin.register(Quiz)
class QuizAdmin(BaseModelAdmin):
    list_display_fields = ['title', 'concept', 'question_count', 'passing_score', 'is_ai_generated_badge']
    search_fields = ['title', 'description']
    list_filter_fields = ['is_ai_generated', 'concept__language']
    autocomplete_fields = ['concept']

    def question_count(self, obj):
        return len(obj.questions) if obj.questions else 0
    question_count.short_description = 'Questions'

    def is_ai_generated_badge(self, obj):
        if obj.is_ai_generated:
            return format_html('<span style="color: blue;">🤖 AI</span>')
        return format_html('<span style="color: gray;">✍️ Manual</span>')
    is_ai_generated_badge.short_description = 'Source'


@admin.register(QuizAttempt)
class QuizAttemptAdmin(BaseModelAdmin):
    list_display_fields = ['user_id', 'quiz', 'score', 'completed_at']
    search_fields = ['user_id']
    list_filter_fields = ['quiz', 'completed_at']
    autocomplete_fields = ['quiz']


@admin.register(SpacedRepetitionCard)
class SpacedRepetitionCardAdmin(BaseModelAdmin):
    list_display_fields = ['user_id', 'card_state_badge', 'ease_factor', 'interval_days', 'due_date']
    search_fields = ['user_id']
    list_filter_fields = ['card_state', 'due_date']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_reviewed_at']

    def card_state_badge(self, obj):
        colors = {
            'new': 'blue',
            'learning': 'orange',
            'review': 'green',
            'relearning': 'red',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.card_state, 'gray'),
            obj.get_card_state_display()
        )
    card_state_badge.short_description = 'State'


@admin.register(ReviewLog)
class ReviewLogAdmin(BaseModelAdmin):
    list_display_fields = ['user_id', 'rating', 'new_ease_factor', 'new_interval_days', 'reviewed_at']
    search_fields = ['user_id']
    list_filter_fields = ['rating', 'reviewed_at']


@admin.register(TutoringSession)
class TutoringSessionAdmin(BaseModelAdmin):
    list_display_fields = ['user_id', 'language', 'session_type', 'duration_minutes', 'started_at']
    search_fields = ['user_id']
    list_filter_fields = ['language', 'session_type', 'started_at']
    autocomplete_fields = ['language', 'concept']

    def duration_minutes(self, obj):
        if obj.duration_seconds:
            return f"{obj.duration_seconds // 60} min"
        return "In progress"
    duration_minutes.short_description = 'Duration'


@admin.register(AIGenerationJob)
class AIGenerationJobAdmin(BaseModelAdmin):
    list_display_fields = ['job_type', 'language', 'status_badge', 'priority', 'created_at']
    search_fields = ['job_type']
    list_filter_fields = ['job_type', 'status', 'language']
    autocomplete_fields = ['language', 'concept']

    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['retry_failed_jobs']

    def retry_failed_jobs(self, request, queryset):
        """Retry failed jobs"""
        updated = queryset.filter(status='failed').update(
            status='pending',
            error_message='',
            started_at=None
        )
        self.message_user(request, f'{updated} jobs set to retry.')
    retry_failed_jobs.short_description = 'Retry failed jobs'


@admin.register(UserPreferences)
class UserPreferencesAdmin(BaseModelAdmin):
    list_display_fields = ['user_id', 'theme', 'study_streak_days', 'notifications_enabled']
    search_fields = ['user_id']
    list_filter_fields = ['theme', 'notifications_enabled']
    autocomplete_fields = ['native_language']
