"""Learning Plans models"""
from django.db import models
from apps.languages.models import TimeStampedModel, Language, Concept
import uuid


class LearningPlan(TimeStampedModel):
    """Curated learning paths that can be shared among users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='learning_plans')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    difficulty_level = models.IntegerField(default=1, help_text="1-10 scale")
    estimated_hours = models.IntegerField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Creator
    created_by = models.UUIDField(null=True, blank=True)

    # Categorization
    category = models.CharField(max_length=100, blank=True, help_text="e.g., 'beginner_course', 'business', 'travel'")
    tags = models.JSONField(default=list, blank=True)

    # Media
    cover_image_url = models.URLField(blank=True)
    preview_video_url = models.URLField(blank=True)

    # Stats (denormalized for performance)
    enrollment_count = models.IntegerField(default=0)
    completion_count = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = 'mala_learning_plans'
        verbose_name = 'Learning Plan'
        verbose_name_plural = 'Learning Plans'
        ordering = ['-enrollment_count', 'title']
        indexes = [
            models.Index(fields=['language', 'is_public']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} ({self.language.code})"


class LearningPlanConcept(TimeStampedModel):
    """Many-to-many relationship between learning plans and concepts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_plan = models.ForeignKey(LearningPlan, on_delete=models.CASCADE, related_name='plan_concepts')
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='in_plans')

    # Ordering within the plan
    sequence_order = models.IntegerField()

    # Optional: make some concepts optional vs required
    is_required = models.BooleanField(default=True)

    # Optional: add notes or instructions
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'mala_learning_plan_concepts'
        verbose_name = 'Learning Plan Concept'
        verbose_name_plural = 'Learning Plan Concepts'
        unique_together = [
            ['learning_plan', 'concept'],
            ['learning_plan', 'sequence_order'],
        ]
        ordering = ['learning_plan', 'sequence_order']

    def __str__(self):
        return f"{self.learning_plan.title} - {self.sequence_order}. {self.concept.title}"


class UserLearningPlan(TimeStampedModel):
    """User enrollment in learning plans"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    learning_plan = models.ForeignKey(LearningPlan, on_delete=models.CASCADE, related_name='user_enrollments')

    # Progress tracking
    current_concept_index = models.IntegerField(default=0)
    completed_concept_count = models.IntegerField(default=0)
    total_concept_count = models.IntegerField(default=0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    # Engagement
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.IntegerField(default=0)

    # Completion tracking
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # User feedback
    user_rating = models.IntegerField(null=True, blank=True, help_text="1-5 stars")
    user_review = models.TextField(blank=True)

    class Meta:
        db_table = 'mala_user_learning_plans'
        verbose_name = 'User Learning Plan'
        verbose_name_plural = 'User Learning Plans'
        unique_together = [['user_id', 'learning_plan']]
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user_id', 'status']),
        ]

    def __str__(self):
        return f"User {self.user_id} - {self.learning_plan.title} ({self.status})"


class UserPlanConceptProgress(TimeStampedModel):
    """Track user progress on individual concepts within a plan"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_learning_plan = models.ForeignKey(UserLearningPlan, on_delete=models.CASCADE, related_name='concept_progress')
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='plan_progress')

    # Progress tracking
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    # Activities completed
    stories_read = models.IntegerField(default=0)
    quizzes_passed = models.IntegerField(default=0)
    flashcards_reviewed = models.IntegerField(default=0)
    tutoring_sessions = models.IntegerField(default=0)

    # Time tracking
    time_spent_minutes = models.IntegerField(default=0)
    first_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'mala_user_plan_concept_progress'
        verbose_name = 'User Plan Concept Progress'
        verbose_name_plural = 'User Plan Concept Progress'
        unique_together = [['user_learning_plan', 'concept']]

    def __str__(self):
        return f"{self.user_learning_plan} - {self.concept.title} ({self.completion_percentage}%)"


class LearningPlanCollaborator(models.Model):
    """Plan sharing and collaboration"""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_plan = models.ForeignKey(LearningPlan, on_delete=models.CASCADE, related_name='collaborators')
    user_id = models.UUIDField(db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    invited_by = models.UUIDField(null=True, blank=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mala_learning_plan_collaborators'
        verbose_name = 'Learning Plan Collaborator'
        verbose_name_plural = 'Learning Plan Collaborators'
        unique_together = [['learning_plan', 'user_id']]

    def __str__(self):
        return f"{self.learning_plan.title} - User {self.user_id} ({self.role})"
