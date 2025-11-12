import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TimeStampedModel


class AIPromptTemplate(TimeStampedModel):
    """
    Stores AI prompt templates for different features.
    Templates can contain variables like {concept_title}, {language}, etc.
    """

    PROMPT_TYPE_CHOICES = [
        ('story_generation', 'Story Generation'),
        ('quiz_generation', 'Quiz Generation'),
        ('flashcard_generation', 'Flashcard Generation'),
        ('podcast_intro', 'Podcast Introduction'),
        ('podcast_vocab', 'Podcast Vocabulary'),
        ('podcast_dialogue', 'Podcast Dialogue'),
        ('podcast_grammar', 'Podcast Grammar'),
        ('podcast_story', 'Podcast Story'),
        ('podcast_quiz', 'Podcast Quiz'),
        ('podcast_outro', 'Podcast Outro'),
        ('tutoring_system', 'Tutoring System Prompt'),
        ('tutoring_context', 'Tutoring Context Prompt'),
        ('multimodal_analysis', 'Multimodal Analysis Prompt'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Human-readable name for the prompt")
    prompt_type = models.CharField(max_length=50, choices=PROMPT_TYPE_CHOICES, unique=True)
    description = models.TextField(blank=True, help_text="Description of what this prompt does")

    # Variables that can be used in this template
    available_variables = models.JSONField(
        default=list,
        help_text="List of variable names available for this prompt type, e.g., ['concept_title', 'language', 'difficulty']"
    )

    # Metadata
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=100, blank=True, help_text="Creator/author of the prompt template")

    class Meta:
        db_table = 'mala_ai_prompt_templates'
        ordering = ['prompt_type']
        verbose_name = 'AI Prompt Template'
        verbose_name_plural = 'AI Prompt Templates'

    def __str__(self):
        return f"{self.name} ({self.get_prompt_type_display()})"

    def get_active_version(self):
        """Get the currently active version of this prompt"""
        return self.versions.filter(is_active=True).first()

    def get_version_for_user(self, user_id):
        """Get the version assigned to a specific user, or the default active version"""
        # Check if user has a specific assignment
        assignment = AIPromptAssignment.objects.filter(
            prompt_template=self,
            user_id=user_id,
            is_active=True
        ).first()

        if assignment:
            return assignment.prompt_version

        # Fall back to default active version
        return self.get_active_version()


class AIPromptVersion(TimeStampedModel):
    """
    Stores different versions of prompt templates for A/B testing and versioning.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt_template = models.ForeignKey(
        AIPromptTemplate,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    version_number = models.PositiveIntegerField(help_text="Version number (auto-incremented)")
    version_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional name for this version, e.g., 'More conversational', 'Stricter grammar'"
    )

    # The actual prompt text (can include variables like {concept_title})
    prompt_text = models.TextField(help_text="The prompt text with variables like {concept_title}, {language}, etc.")

    # Status
    is_active = models.BooleanField(
        default=False,
        help_text="Is this the currently active version? Only one version should be active per template."
    )
    is_archived = models.BooleanField(default=False, help_text="Archived versions are hidden from active use")

    # Metadata for tracking performance
    usage_count = models.PositiveIntegerField(default=0, help_text="Number of times this version has been used")
    success_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Success rate percentage (0-100)"
    )
    avg_generation_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Average generation time in seconds"
    )

    # Changelog
    change_notes = models.TextField(blank=True, help_text="Notes about what changed in this version")
    created_by = models.CharField(max_length=100, blank=True, help_text="Who created this version")

    class Meta:
        db_table = 'mala_ai_prompt_versions'
        ordering = ['prompt_template', '-version_number']
        unique_together = [['prompt_template', 'version_number']]
        verbose_name = 'AI Prompt Version'
        verbose_name_plural = 'AI Prompt Versions'
        indexes = [
            models.Index(fields=['prompt_template', 'is_active']),
            models.Index(fields=['is_active', 'is_archived']),
        ]

    def __str__(self):
        version_display = f"v{self.version_number}"
        if self.version_name:
            version_display += f" ({self.version_name})"
        return f"{self.prompt_template.name} - {version_display}"

    def save(self, *args, **kwargs):
        # Auto-increment version number if not set
        if not self.version_number:
            last_version = AIPromptVersion.objects.filter(
                prompt_template=self.prompt_template
            ).order_by('-version_number').first()

            self.version_number = (last_version.version_number + 1) if last_version else 1

        # If setting this version as active, deactivate all other versions
        if self.is_active:
            AIPromptVersion.objects.filter(
                prompt_template=self.prompt_template,
                is_active=True
            ).exclude(id=self.id).update(is_active=False)

        super().save(*args, **kwargs)

    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])

    def update_metrics(self, success: bool, generation_time: float):
        """Update performance metrics"""
        self.increment_usage()

        # Update success rate
        if self.success_rate is None:
            self.success_rate = 100.0 if success else 0.0
        else:
            # Running average
            total_successes = (self.success_rate * (self.usage_count - 1)) / 100
            if success:
                total_successes += 1
            self.success_rate = (total_successes / self.usage_count) * 100

        # Update average generation time
        if self.avg_generation_time is None:
            self.avg_generation_time = generation_time
        else:
            # Running average
            total_time = self.avg_generation_time * (self.usage_count - 1)
            self.avg_generation_time = (total_time + generation_time) / self.usage_count

        self.save(update_fields=['success_rate', 'avg_generation_time'])


class AIPromptAssignment(TimeStampedModel):
    """
    Assigns specific prompt versions to users for A/B testing.
    If no assignment exists for a user, the default active version is used.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt_template = models.ForeignKey(
        AIPromptTemplate,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    prompt_version = models.ForeignKey(
        AIPromptVersion,
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    # User assignment (using UUID for Supabase users)
    user_id = models.UUIDField(help_text="Supabase user ID")

    # Assignment metadata
    is_active = models.BooleanField(default=True)
    test_group_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of the A/B test group, e.g., 'control', 'variant_a'"
    )
    notes = models.TextField(blank=True, help_text="Notes about this assignment")

    # Tracking
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.CharField(max_length=100, blank=True, help_text="Who created this assignment")

    class Meta:
        db_table = 'mala_ai_prompt_assignments'
        ordering = ['-created_at']
        unique_together = [['prompt_template', 'user_id']]  # One assignment per template per user
        verbose_name = 'AI Prompt Assignment'
        verbose_name_plural = 'AI Prompt Assignments'
        indexes = [
            models.Index(fields=['user_id', 'is_active']),
            models.Index(fields=['prompt_template', 'user_id']),
        ]

    def __str__(self):
        return f"{self.prompt_template.name} -> User {self.user_id} (v{self.prompt_version.version_number})"


class AIPromptUsageLog(TimeStampedModel):
    """
    Logs every usage of AI prompts for analytics and debugging.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt_version = models.ForeignKey(
        AIPromptVersion,
        on_delete=models.SET_NULL,
        null=True,
        related_name='usage_logs'
    )

    # Context
    user_id = models.UUIDField(null=True, blank=True, help_text="User who triggered this prompt")
    context_data = models.JSONField(
        default=dict,
        help_text="The variables used to render the prompt"
    )
    rendered_prompt = models.TextField(help_text="The final rendered prompt sent to AI")

    # Results
    success = models.BooleanField(help_text="Was the generation successful?")
    generation_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Time taken to generate in seconds"
    )

    # AI Response metadata
    ai_model = models.CharField(max_length=100, blank=True, help_text="AI model used, e.g., 'gemini-2.0-flash'")
    token_count = models.PositiveIntegerField(null=True, blank=True, help_text="Number of tokens used")
    error_message = models.TextField(blank=True, help_text="Error message if generation failed")

    class Meta:
        db_table = 'mala_ai_prompt_usage_logs'
        ordering = ['-created_at']
        verbose_name = 'AI Prompt Usage Log'
        verbose_name_plural = 'AI Prompt Usage Logs'
        indexes = [
            models.Index(fields=['prompt_version', 'created_at']),
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['success', 'created_at']),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.prompt_version} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
