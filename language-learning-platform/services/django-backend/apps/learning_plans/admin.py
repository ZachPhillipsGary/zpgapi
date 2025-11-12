"""Django Admin for Learning Plans"""
from django.contrib import admin
from django.utils.html import format_html
from apps.core.api import BaseModelAdmin
from .models import (
    LearningPlan, LearningPlanConcept, UserLearningPlan,
    UserPlanConceptProgress, LearningPlanCollaborator
)


class LearningPlanConceptInline(admin.TabularInline):
    model = LearningPlanConcept
    extra = 1
    fields = ['concept', 'sequence_order', 'is_required', 'notes']
    autocomplete_fields = ['concept']
    ordering = ['sequence_order']


@admin.register(LearningPlan)
class LearningPlanAdmin(BaseModelAdmin):
    list_display_fields = [
        'title', 'language', 'difficulty_level', 'is_published_badge',
        'is_featured_badge', 'enrollment_count', 'completion_count'
    ]
    search_fields = ['title', 'description']
    list_filter_fields = ['language', 'difficulty_level', 'is_public', 'is_featured', 'is_published', 'category']
    autocomplete_fields = ['language']
    inlines = [LearningPlanConceptInline]
    readonly_fields = ['enrollment_count', 'completion_count', 'average_rating']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'language', 'created_by')
        }),
        ('Configuration', {
            'fields': ('difficulty_level', 'estimated_hours', 'category', 'tags')
        }),
        ('Media', {
            'fields': ('cover_image_url', 'preview_video_url')
        }),
        ('Visibility', {
            'fields': ('is_public', 'is_featured', 'is_published')
        }),
        ('Statistics', {
            'fields': ('enrollment_count', 'completion_count', 'average_rating'),
            'classes': ('collapse',)
        }),
    )

    def is_published_badge(self, obj):
        if obj.is_published:
            return format_html('<span style="color: green;">✓ Published</span>')
        return format_html('<span style="color: gray;">○ Draft</span>')
    is_published_badge.short_description = 'Published'

    def is_featured_badge(self, obj):
        if obj.is_featured:
            return format_html('<span style="color: gold;">⭐ Featured</span>')
        return format_html('<span style="color: gray;">-</span>')
    is_featured_badge.short_description = 'Featured'

    actions = ['publish_plans', 'unpublish_plans', 'feature_plans']

    def publish_plans(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} plans published.')
    publish_plans.short_description = 'Publish selected plans'

    def unpublish_plans(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} plans unpublished.')
    unpublish_plans.short_description = 'Unpublish selected plans'

    def feature_plans(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} plans featured.')
    feature_plans.short_description = 'Feature selected plans'


@admin.register(LearningPlanConcept)
class LearningPlanConceptAdmin(BaseModelAdmin):
    list_display_fields = ['learning_plan', 'sequence_order', 'concept', 'is_required']
    search_fields = ['learning_plan__title', 'concept__title']
    list_filter_fields = ['learning_plan', 'is_required']
    autocomplete_fields = ['learning_plan', 'concept']
    ordering = ['learning_plan', 'sequence_order']


@admin.register(UserLearningPlan)
class UserLearningPlanAdmin(BaseModelAdmin):
    list_display_fields = [
        'user_id', 'learning_plan', 'status_badge', 'progress_percentage',
        'completed_concept_count', 'total_concept_count', 'started_at'
    ]
    search_fields = ['user_id', 'learning_plan__title']
    list_filter_fields = ['status', 'learning_plan', 'started_at']
    autocomplete_fields = ['learning_plan']
    readonly_fields = ['completed_concept_count', 'total_concept_count', 'progress_percentage', 'completed_at']

    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'paused': 'orange',
            'completed': 'blue',
            'abandoned': 'red',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(UserPlanConceptProgress)
class UserPlanConceptProgressAdmin(BaseModelAdmin):
    list_display_fields = [
        'user_learning_plan', 'concept', 'is_completed_badge',
        'completion_percentage', 'stories_read', 'quizzes_passed'
    ]
    search_fields = ['user_learning_plan__user_id', 'concept__title']
    list_filter_fields = ['is_completed', 'concept']
    autocomplete_fields = ['user_learning_plan', 'concept']

    def is_completed_badge(self, obj):
        if obj.is_completed:
            return format_html('<span style="color: green;">✓ Complete</span>')
        return format_html('<span style="color: gray;">○ In Progress</span>')
    is_completed_badge.short_description = 'Status'


@admin.register(LearningPlanCollaborator)
class LearningPlanCollaboratorAdmin(BaseModelAdmin):
    list_display_fields = ['learning_plan', 'user_id', 'role', 'invited_at']
    search_fields = ['user_id', 'learning_plan__title']
    list_filter_fields = ['role', 'learning_plan']
    autocomplete_fields = ['learning_plan']
