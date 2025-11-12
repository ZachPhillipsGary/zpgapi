"""
AI Prompt Service

Provides centralized prompt lookup, rendering, and usage tracking.
All AI prompt usage should go through this service.
"""

import time
from typing import Dict, Optional, Any
from decimal import Decimal
from django.core.cache import cache
from django.db import transaction

from .models import (
    AIPromptTemplate,
    AIPromptVersion,
    AIPromptAssignment,
    AIPromptUsageLog
)


class AIPromptService:
    """
    Service for managing AI prompt lookup, rendering, and usage tracking.

    Usage:
        service = AIPromptService()
        prompt = service.get_prompt('story_generation', user_id='uuid-here')
        rendered = service.render_prompt(prompt, {'concept_title': 'Greetings', 'language': 'French'})

        # Track usage
        service.log_usage(prompt, user_id='uuid', context={...}, success=True, time=1.5)
    """

    CACHE_TIMEOUT = 300  # 5 minutes

    def __init__(self):
        pass

    def get_prompt_template(self, prompt_type: str) -> Optional[AIPromptTemplate]:
        """
        Get a prompt template by type.

        Args:
            prompt_type: The type of prompt (e.g., 'story_generation')

        Returns:
            AIPromptTemplate instance or None
        """
        cache_key = f'prompt_template:{prompt_type}'
        template = cache.get(cache_key)

        if template is None:
            template = AIPromptTemplate.objects.filter(
                prompt_type=prompt_type,
                is_active=True
            ).first()

            if template:
                cache.set(cache_key, template, self.CACHE_TIMEOUT)

        return template

    def get_prompt_version(
        self,
        prompt_type: str,
        user_id: Optional[str] = None
    ) -> Optional[AIPromptVersion]:
        """
        Get the appropriate prompt version for a user.
        Checks for user-specific assignments first, then falls back to default active version.

        Args:
            prompt_type: The type of prompt (e.g., 'story_generation')
            user_id: Optional Supabase user ID for user-specific prompts

        Returns:
            AIPromptVersion instance or None
        """
        template = self.get_prompt_template(prompt_type)
        if not template:
            return None

        # Check cache first
        cache_key = f'prompt_version:{prompt_type}:{user_id or "default"}'
        version = cache.get(cache_key)

        if version is None:
            if user_id:
                version = template.get_version_for_user(user_id)
            else:
                version = template.get_active_version()

            if version:
                cache.set(cache_key, version, self.CACHE_TIMEOUT)

        return version

    def render_prompt(
        self,
        prompt_version: AIPromptVersion,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a prompt template with the provided context variables.

        Args:
            prompt_version: The prompt version to render
            context: Dictionary of variables to substitute

        Returns:
            Rendered prompt string

        Example:
            context = {
                'concept_title': 'Basic Greetings',
                'language': 'French',
                'difficulty': 1
            }
            rendered = service.render_prompt(version, context)
        """
        try:
            return prompt_version.prompt_text.format(**context)
        except KeyError as e:
            # Missing variable in context
            raise ValueError(f"Missing required variable in context: {e}")

    def get_and_render_prompt(
        self,
        prompt_type: str,
        context: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Convenience method: get prompt version and render in one call.

        Args:
            prompt_type: The type of prompt
            context: Variables for rendering
            user_id: Optional user ID

        Returns:
            Rendered prompt string or None if prompt not found
        """
        version = self.get_prompt_version(prompt_type, user_id)
        if not version:
            return None

        return self.render_prompt(version, context)

    @transaction.atomic
    def log_usage(
        self,
        prompt_version: AIPromptVersion,
        rendered_prompt: str,
        context: Dict[str, Any],
        success: bool,
        generation_time: float,
        user_id: Optional[str] = None,
        ai_model: str = '',
        token_count: Optional[int] = None,
        error_message: str = ''
    ):
        """
        Log prompt usage for analytics and update version metrics.

        Args:
            prompt_version: The prompt version that was used
            rendered_prompt: The final rendered prompt
            context: The context variables used
            success: Whether generation was successful
            generation_time: Time taken in seconds
            user_id: Optional user ID
            ai_model: AI model used (e.g., 'gemini-2.0-flash')
            token_count: Number of tokens used
            error_message: Error message if failed
        """
        # Create usage log
        AIPromptUsageLog.objects.create(
            prompt_version=prompt_version,
            user_id=user_id,
            context_data=context,
            rendered_prompt=rendered_prompt,
            success=success,
            generation_time=Decimal(str(generation_time)),
            ai_model=ai_model,
            token_count=token_count,
            error_message=error_message
        )

        # Update version metrics
        prompt_version.update_metrics(success, generation_time)

    def create_user_assignment(
        self,
        prompt_type: str,
        user_id: str,
        version_number: int,
        test_group_name: str = '',
        notes: str = '',
        assigned_by: str = ''
    ) -> AIPromptAssignment:
        """
        Assign a specific prompt version to a user for A/B testing.

        Args:
            prompt_type: The type of prompt
            user_id: Supabase user ID
            version_number: Version number to assign
            test_group_name: Name of test group (e.g., 'control', 'variant_a')
            notes: Optional notes
            assigned_by: Who created this assignment

        Returns:
            AIPromptAssignment instance
        """
        template = self.get_prompt_template(prompt_type)
        if not template:
            raise ValueError(f"Prompt template not found: {prompt_type}")

        version = template.versions.filter(version_number=version_number).first()
        if not version:
            raise ValueError(f"Version {version_number} not found for {prompt_type}")

        # Create or update assignment
        assignment, created = AIPromptAssignment.objects.update_or_create(
            prompt_template=template,
            user_id=user_id,
            defaults={
                'prompt_version': version,
                'is_active': True,
                'test_group_name': test_group_name,
                'notes': notes,
                'assigned_by': assigned_by
            }
        )

        # Invalidate cache
        cache_key = f'prompt_version:{prompt_type}:{user_id}'
        cache.delete(cache_key)

        return assignment

    def remove_user_assignment(self, prompt_type: str, user_id: str):
        """
        Remove a user's specific prompt assignment (they'll use default version).

        Args:
            prompt_type: The type of prompt
            user_id: Supabase user ID
        """
        template = self.get_prompt_template(prompt_type)
        if not template:
            return

        AIPromptAssignment.objects.filter(
            prompt_template=template,
            user_id=user_id
        ).update(is_active=False)

        # Invalidate cache
        cache_key = f'prompt_version:{prompt_type}:{user_id}'
        cache.delete(cache_key)

    def get_prompt_analytics(self, prompt_type: str) -> Dict[str, Any]:
        """
        Get analytics for a prompt template across all versions.

        Args:
            prompt_type: The type of prompt

        Returns:
            Dictionary with analytics data
        """
        template = self.get_prompt_template(prompt_type)
        if not template:
            return {}

        versions = template.versions.filter(is_archived=False)

        analytics = {
            'template': {
                'name': template.name,
                'type': template.prompt_type,
                'active_version': None
            },
            'versions': []
        }

        for version in versions:
            version_data = {
                'version_number': version.version_number,
                'version_name': version.version_name,
                'is_active': version.is_active,
                'usage_count': version.usage_count,
                'success_rate': float(version.success_rate) if version.success_rate else None,
                'avg_generation_time': float(version.avg_generation_time) if version.avg_generation_time else None,
            }

            if version.is_active:
                analytics['template']['active_version'] = version.version_number

            analytics['versions'].append(version_data)

        return analytics


# Global singleton instance
_prompt_service = None


def get_prompt_service() -> AIPromptService:
    """
    Get the global AIPromptService instance.

    Returns:
        AIPromptService singleton
    """
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = AIPromptService()
    return _prompt_service


class PromptContext:
    """
    Context manager for tracking prompt usage.

    Usage:
        with PromptContext('story_generation', user_id='uuid') as ctx:
            prompt = ctx.get_prompt({'concept_title': 'Greetings'})
            # ... use prompt to generate content ...
            result = generate_content(prompt)
            ctx.mark_success(result)
    """

    def __init__(
        self,
        prompt_type: str,
        user_id: Optional[str] = None,
        ai_model: str = ''
    ):
        self.prompt_type = prompt_type
        self.user_id = user_id
        self.ai_model = ai_model
        self.service = get_prompt_service()

        self.prompt_version = None
        self.context = {}
        self.rendered_prompt = None
        self.start_time = None
        self.success = False
        self.error_message = ''
        self.token_count = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.prompt_version and self.rendered_prompt:
            generation_time = time.time() - self.start_time

            # If exception occurred, mark as failure
            if exc_type is not None:
                self.success = False
                self.error_message = str(exc_val)

            self.service.log_usage(
                prompt_version=self.prompt_version,
                rendered_prompt=self.rendered_prompt,
                context=self.context,
                success=self.success,
                generation_time=generation_time,
                user_id=self.user_id,
                ai_model=self.ai_model,
                token_count=self.token_count,
                error_message=self.error_message
            )

        return False  # Don't suppress exceptions

    def get_prompt(self, context: Dict[str, Any]) -> str:
        """
        Get and render the prompt with context.

        Args:
            context: Variables for rendering

        Returns:
            Rendered prompt string
        """
        self.context = context
        self.prompt_version = self.service.get_prompt_version(
            self.prompt_type,
            self.user_id
        )

        if not self.prompt_version:
            raise ValueError(f"No active prompt found for type: {self.prompt_type}")

        self.rendered_prompt = self.service.render_prompt(
            self.prompt_version,
            context
        )

        return self.rendered_prompt

    def mark_success(self, token_count: Optional[int] = None):
        """Mark the generation as successful"""
        self.success = True
        self.token_count = token_count

    def mark_failure(self, error_message: str):
        """Mark the generation as failed"""
        self.success = False
        self.error_message = error_message
