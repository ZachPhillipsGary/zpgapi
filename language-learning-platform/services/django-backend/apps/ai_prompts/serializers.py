"""
Serializers for AI Prompt Management API
"""

from rest_framework import serializers
from .models import (
    AIPromptTemplate,
    AIPromptVersion,
    AIPromptAssignment,
    AIPromptUsageLog
)


class AIPromptVersionSerializer(serializers.ModelSerializer):
    """Serializer for AI Prompt Versions"""

    class Meta:
        model = AIPromptVersion
        fields = [
            'id', 'prompt_template', 'version_number', 'version_name',
            'prompt_text', 'is_active', 'is_archived', 'usage_count',
            'success_rate', 'avg_generation_time', 'change_notes',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'version_number', 'usage_count', 'success_rate',
            'avg_generation_time', 'created_at', 'updated_at'
        ]


class AIPromptTemplateSerializer(serializers.ModelSerializer):
    """Serializer for AI Prompt Templates"""

    active_version = AIPromptVersionSerializer(
        source='get_active_version',
        read_only=True
    )
    versions = AIPromptVersionSerializer(many=True, read_only=True)

    class Meta:
        model = AIPromptTemplate
        fields = [
            'id', 'name', 'prompt_type', 'description',
            'available_variables', 'is_active', 'created_by',
            'active_version', 'versions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AIPromptTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing templates"""

    active_version_number = serializers.SerializerMethodField()
    total_versions = serializers.SerializerMethodField()

    class Meta:
        model = AIPromptTemplate
        fields = [
            'id', 'name', 'prompt_type', 'description', 'is_active',
            'active_version_number', 'total_versions', 'created_at'
        ]

    def get_active_version_number(self, obj):
        active = obj.get_active_version()
        return active.version_number if active else None

    def get_total_versions(self, obj):
        return obj.versions.count()


class AIPromptAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for AI Prompt Assignments"""

    prompt_template_name = serializers.CharField(
        source='prompt_template.name',
        read_only=True
    )
    prompt_version_number = serializers.IntegerField(
        source='prompt_version.version_number',
        read_only=True
    )

    class Meta:
        model = AIPromptAssignment
        fields = [
            'id', 'prompt_template', 'prompt_template_name',
            'prompt_version', 'prompt_version_number', 'user_id',
            'is_active', 'test_group_name', 'notes', 'assigned_by',
            'assigned_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'assigned_at', 'created_at', 'updated_at'
        ]


class AIPromptUsageLogSerializer(serializers.ModelSerializer):
    """Serializer for AI Prompt Usage Logs"""

    prompt_template_name = serializers.CharField(
        source='prompt_version.prompt_template.name',
        read_only=True
    )
    prompt_version_number = serializers.IntegerField(
        source='prompt_version.version_number',
        read_only=True
    )

    class Meta:
        model = AIPromptUsageLog
        fields = [
            'id', 'prompt_version', 'prompt_template_name',
            'prompt_version_number', 'user_id', 'context_data',
            'rendered_prompt', 'success', 'generation_time',
            'ai_model', 'token_count', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
