"""
Django Admin for AI Prompt Management

Provides comprehensive admin interfaces for managing prompts, versions, and A/B testing.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
from django import forms

from .models import (
    AIPromptTemplate,
    AIPromptVersion,
    AIPromptAssignment,
    AIPromptUsageLog
)


class AIPromptVersionInline(admin.TabularInline):
    """Inline editor for prompt versions"""
    model = AIPromptVersion
    extra = 0
    fields = [
        'version_number', 'version_name', 'is_active', 'is_archived',
        'usage_count', 'success_rate', 'change_notes'
    ]
    readonly_fields = ['version_number', 'usage_count', 'success_rate']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Prevent adding versions through inline - they should use the main form
        return False


@admin.register(AIPromptTemplate)
class AIPromptTemplateAdmin(admin.ModelAdmin):
    """Admin for AI Prompt Templates"""

    list_display = [
        'name', 'prompt_type_badge', 'active_version_info',
        'total_versions', 'is_active_badge', 'created_at'
    ]
    list_filter = ['prompt_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'prompt_type']
    readonly_fields = ['id', 'created_at', 'updated_at', 'active_version_preview']

    fieldsets = [
        ('Basic Information', {
            'fields': [
                'name', 'prompt_type', 'description', 'is_active'
            ]
        }),
        ('Configuration', {
            'fields': [
                'available_variables', 'created_by'
            ]
        }),
        ('Active Version', {
            'fields': ['active_version_preview'],
            'description': 'Preview of the currently active prompt version'
        }),
        ('Metadata', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    inlines = [AIPromptVersionInline]

    def prompt_type_badge(self, obj):
        """Display prompt type as a colored badge"""
        colors = {
            'story_generation': '#4CAF50',
            'quiz_generation': '#2196F3',
            'flashcard_generation': '#FF9800',
            'podcast_intro': '#9C27B0',
            'podcast_vocab': '#9C27B0',
            'podcast_dialogue': '#9C27B0',
            'podcast_grammar': '#9C27B0',
            'podcast_story': '#9C27B0',
            'podcast_quiz': '#9C27B0',
            'podcast_outro': '#9C27B0',
            'tutoring_system': '#F44336',
            'tutoring_context': '#F44336',
            'multimodal_analysis': '#00BCD4',
        }
        color = colors.get(obj.prompt_type, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_prompt_type_display()
        )
    prompt_type_badge.short_description = 'Type'

    def active_version_info(self, obj):
        """Display active version information"""
        active_version = obj.get_active_version()
        if active_version:
            url = reverse('admin:ai_prompts_aipromptversion_change', args=[active_version.id])
            return format_html(
                '<a href="{}">v{} {}</a> <span style="color: #666;">(used {} times)</span>',
                url,
                active_version.version_number,
                f"({active_version.version_name})" if active_version.version_name else "",
                active_version.usage_count
            )
        return format_html('<span style="color: #999;">No active version</span>')
    active_version_info.short_description = 'Active Version'

    def total_versions(self, obj):
        """Display total number of versions"""
        count = obj.versions.count()
        archived = obj.versions.filter(is_archived=True).count()
        if archived > 0:
            return format_html('{} <span style="color: #999;">({} archived)</span>', count, archived)
        return count
    total_versions.short_description = 'Versions'

    def is_active_badge(self, obj):
        """Display active status as a badge"""
        if obj.is_active:
            return format_html(
                '<span style="color: #4CAF50; font-weight: bold;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: #999;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'

    def active_version_preview(self, obj):
        """Preview the active version's prompt text"""
        active_version = obj.get_active_version()
        if not active_version:
            return format_html('<em style="color: #999;">No active version</em>')

        preview = active_version.prompt_text[:300]
        if len(active_version.prompt_text) > 300:
            preview += '...'

        return format_html(
            '<div style="background: #f5f5f5; padding: 15px; border-radius: 5px; font-family: monospace;">'
            '<strong>Version {}:</strong> {}<br><br>{}'
            '</div>',
            active_version.version_number,
            active_version.version_name or 'Unnamed',
            preview
        )
    active_version_preview.short_description = 'Active Prompt Preview'


class AIPromptVersionForm(forms.ModelForm):
    """Custom form for prompt version with validation"""

    class Meta:
        model = AIPromptVersion
        fields = '__all__'
        widgets = {
            'prompt_text': forms.Textarea(attrs={'rows': 20, 'style': 'font-family: monospace; width: 100%;'}),
            'change_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_prompt_text(self):
        """Validate that required variables are used in prompt"""
        prompt_text = self.cleaned_data.get('prompt_text')
        prompt_template = self.cleaned_data.get('prompt_template')

        if prompt_template and prompt_template.available_variables:
            # Check that all required variables are present in the prompt
            missing_vars = []
            for var in prompt_template.available_variables:
                if f'{{{var}}}' not in prompt_text:
                    missing_vars.append(var)

            if missing_vars:
                self.add_error(
                    'prompt_text',
                    f"Missing required variables: {', '.join(missing_vars)}"
                )

        return prompt_text


@admin.register(AIPromptVersion)
class AIPromptVersionAdmin(admin.ModelAdmin):
    """Admin for AI Prompt Versions"""

    form = AIPromptVersionForm

    list_display = [
        'prompt_template_link', 'version_display', 'status_badges',
        'usage_count', 'success_rate_display', 'avg_time', 'created_at'
    ]
    list_filter = [
        'prompt_template__prompt_type', 'is_active', 'is_archived',
        'created_at'
    ]
    search_fields = [
        'prompt_template__name', 'version_name', 'change_notes'
    ]
    readonly_fields = [
        'id', 'version_number', 'usage_count', 'success_rate',
        'avg_generation_time', 'created_at', 'updated_at',
        'prompt_preview'
    ]

    fieldsets = [
        ('Version Information', {
            'fields': [
                'prompt_template', 'version_number', 'version_name'
            ]
        }),
        ('Prompt Content', {
            'fields': ['prompt_text', 'prompt_preview'],
            'description': 'Write your prompt using variables like {concept_title}, {language}, etc.'
        }),
        ('Status', {
            'fields': ['is_active', 'is_archived']
        }),
        ('Performance Metrics', {
            'fields': [
                'usage_count', 'success_rate', 'avg_generation_time'
            ],
            'classes': ['collapse']
        }),
        ('Changelog', {
            'fields': ['change_notes', 'created_by']
        }),
        ('Metadata', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    actions = ['activate_version', 'archive_version', 'clone_version']

    def prompt_template_link(self, obj):
        """Link to parent template"""
        url = reverse('admin:ai_prompts_aiprompttemplate_change', args=[obj.prompt_template.id])
        return format_html('<a href="{}">{}</a>', url, obj.prompt_template.name)
    prompt_template_link.short_description = 'Template'

    def version_display(self, obj):
        """Display version number and name"""
        if obj.version_name:
            return format_html(
                '<strong>v{}</strong> <span style="color: #666;">({})</span>',
                obj.version_number,
                obj.version_name
            )
        return format_html('<strong>v{}</strong>', obj.version_number)
    version_display.short_description = 'Version'

    def status_badges(self, obj):
        """Display status badges"""
        badges = []
        if obj.is_active:
            badges.append(
                '<span style="background: #4CAF50; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 10px; margin-right: 5px;">ACTIVE</span>'
            )
        if obj.is_archived:
            badges.append(
                '<span style="background: #999; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 10px;">ARCHIVED</span>'
            )
        return format_html(''.join(badges)) if badges else '—'
    status_badges.short_description = 'Status'

    def success_rate_display(self, obj):
        """Display success rate with color coding"""
        if obj.success_rate is None:
            return '—'

        rate = float(obj.success_rate)
        if rate >= 95:
            color = '#4CAF50'
        elif rate >= 80:
            color = '#FF9800'
        else:
            color = '#F44336'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            rate
        )
    success_rate_display.short_description = 'Success Rate'

    def avg_time(self, obj):
        """Display average generation time"""
        if obj.avg_generation_time is None:
            return '—'
        return f"{float(obj.avg_generation_time):.2f}s"
    avg_time.short_description = 'Avg Time'

    def prompt_preview(self, obj):
        """Preview the prompt with variable highlighting"""
        import re

        # Highlight variables in the prompt
        highlighted = re.sub(
            r'\{([^}]+)\}',
            r'<span style="background: #FFF9C4; padding: 2px 4px; border-radius: 2px; font-weight: bold;">{\1}</span>',
            obj.prompt_text
        )

        return format_html(
            '<div style="background: #f5f5f5; padding: 15px; border-radius: 5px; '
            'font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto;">{}</div>',
            mark_safe(highlighted)
        )
    prompt_preview.short_description = 'Prompt Preview (with variables highlighted)'

    @admin.action(description='Activate selected versions')
    def activate_version(self, request, queryset):
        """Activate selected versions (one per template)"""
        activated = 0
        for version in queryset:
            if not version.is_active and not version.is_archived:
                version.is_active = True
                version.save()  # This will deactivate other versions via model save()
                activated += 1

        self.message_user(request, f"Activated {activated} version(s).")

    @admin.action(description='Archive selected versions')
    def archive_version(self, request, queryset):
        """Archive selected versions"""
        count = queryset.filter(is_active=False).update(is_archived=True)
        self.message_user(request, f"Archived {count} version(s).")

    @admin.action(description='Clone selected versions')
    def clone_version(self, request, queryset):
        """Clone selected versions"""
        cloned = 0
        for version in queryset:
            # Create a new version based on this one
            new_version = AIPromptVersion.objects.create(
                prompt_template=version.prompt_template,
                version_name=f"{version.version_name} (Copy)" if version.version_name else "Copy",
                prompt_text=version.prompt_text,
                is_active=False,
                is_archived=False,
                change_notes=f"Cloned from v{version.version_number}",
                created_by=request.user.username if request.user.is_authenticated else ''
            )
            cloned += 1

        self.message_user(request, f"Cloned {cloned} version(s).")


@admin.register(AIPromptAssignment)
class AIPromptAssignmentAdmin(admin.ModelAdmin):
    """Admin for AI Prompt Assignments (A/B Testing)"""

    list_display = [
        'user_id_short', 'prompt_template_link', 'version_link',
        'test_group_badge', 'is_active_badge', 'assigned_at'
    ]
    list_filter = [
        'prompt_template__prompt_type', 'test_group_name',
        'is_active', 'assigned_at'
    ]
    search_fields = [
        'user_id', 'test_group_name', 'notes',
        'prompt_template__name'
    ]
    readonly_fields = ['id', 'assigned_at', 'created_at', 'updated_at']

    fieldsets = [
        ('Assignment', {
            'fields': [
                'prompt_template', 'prompt_version', 'user_id', 'is_active'
            ]
        }),
        ('A/B Testing', {
            'fields': [
                'test_group_name', 'notes', 'assigned_by'
            ]
        }),
        ('Metadata', {
            'fields': ['id', 'assigned_at', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def user_id_short(self, obj):
        """Display shortened user ID"""
        uid = str(obj.user_id)
        return format_html(
            '<code title="{}">{}</code>',
            uid,
            uid[:8] + '...' if len(uid) > 8 else uid
        )
    user_id_short.short_description = 'User'

    def prompt_template_link(self, obj):
        """Link to template"""
        url = reverse('admin:ai_prompts_aiprompttemplate_change', args=[obj.prompt_template.id])
        return format_html('<a href="{}">{}</a>', url, obj.prompt_template.name)
    prompt_template_link.short_description = 'Template'

    def version_link(self, obj):
        """Link to version"""
        url = reverse('admin:ai_prompts_aipromptversion_change', args=[obj.prompt_version.id])
        return format_html(
            '<a href="{}">v{}</a>',
            url,
            obj.prompt_version.version_number
        )
    version_link.short_description = 'Version'

    def test_group_badge(self, obj):
        """Display test group as badge"""
        if not obj.test_group_name:
            return '—'

        colors = {
            'control': '#2196F3',
            'variant_a': '#4CAF50',
            'variant_b': '#FF9800',
            'variant_c': '#9C27B0',
        }
        color = colors.get(obj.test_group_name.lower(), '#757575')

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.test_group_name
        )
    test_group_badge.short_description = 'Test Group'

    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: #4CAF50;">✓ Active</span>')
        return format_html('<span style="color: #999;">Inactive</span>')
    is_active_badge.short_description = 'Status'


@admin.register(AIPromptUsageLog)
class AIPromptUsageLogAdmin(admin.ModelAdmin):
    """Admin for AI Prompt Usage Logs (Analytics)"""

    list_display = [
        'created_at', 'prompt_version_link', 'user_id_short',
        'success_badge', 'generation_time_display', 'ai_model', 'token_count'
    ]
    list_filter = [
        'success', 'ai_model', 'created_at',
        'prompt_version__prompt_template__prompt_type'
    ]
    search_fields = [
        'user_id', 'rendered_prompt', 'error_message'
    ]
    readonly_fields = [
        'id', 'prompt_version', 'user_id', 'context_data', 'rendered_prompt',
        'success', 'generation_time', 'ai_model', 'token_count',
        'error_message', 'created_at', 'updated_at', 'rendered_prompt_preview'
    ]

    fieldsets = [
        ('Prompt Information', {
            'fields': ['prompt_version', 'rendered_prompt_preview']
        }),
        ('Context', {
            'fields': ['user_id', 'context_data'],
            'classes': ['collapse']
        }),
        ('Results', {
            'fields': [
                'success', 'generation_time', 'ai_model', 'token_count', 'error_message'
            ]
        }),
        ('Metadata', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def has_add_permission(self, request):
        # Usage logs are created automatically
        return False

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of old logs (retention policy)
        return True

    def prompt_version_link(self, obj):
        """Link to prompt version"""
        if not obj.prompt_version:
            return '—'
        url = reverse('admin:ai_prompts_aipromptversion_change', args=[obj.prompt_version.id])
        return format_html(
            '<a href="{}">{} v{}</a>',
            url,
            obj.prompt_version.prompt_template.name,
            obj.prompt_version.version_number
        )
    prompt_version_link.short_description = 'Prompt Version'

    def user_id_short(self, obj):
        """Display shortened user ID"""
        if not obj.user_id:
            return '—'
        uid = str(obj.user_id)
        return format_html(
            '<code title="{}">{}</code>',
            uid,
            uid[:8] + '...' if len(uid) > 8 else uid
        )
    user_id_short.short_description = 'User'

    def success_badge(self, obj):
        """Display success status as badge"""
        if obj.success:
            return format_html(
                '<span style="color: #4CAF50; font-weight: bold;">✓ Success</span>'
            )
        return format_html(
            '<span style="color: #F44336; font-weight: bold;">✗ Failed</span>'
        )
    success_badge.short_description = 'Status'

    def generation_time_display(self, obj):
        """Display generation time with color coding"""
        time = float(obj.generation_time)
        if time < 1.0:
            color = '#4CAF50'
        elif time < 3.0:
            color = '#FF9800'
        else:
            color = '#F44336'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}s</span>',
            color,
            time
        )
    generation_time_display.short_description = 'Generation Time'

    def rendered_prompt_preview(self, obj):
        """Preview the rendered prompt"""
        if not obj.rendered_prompt:
            return '—'

        preview = obj.rendered_prompt[:500]
        if len(obj.rendered_prompt) > 500:
            preview += '...'

        return format_html(
            '<div style="background: #f5f5f5; padding: 15px; border-radius: 5px; '
            'font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">{}</div>',
            preview
        )
    rendered_prompt_preview.short_description = 'Rendered Prompt Preview'
