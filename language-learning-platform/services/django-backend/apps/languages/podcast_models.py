"""
Podcast Models for Personalized Language Learning Podcasts
"""
from django.db import models
from apps.languages.models import TimeStampedModel, Language, Concept, Word
import uuid


class PodcastEpisode(TimeStampedModel):
    """Daily personalized podcast episodes for language learning"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    language = models.ForeignKey('languages.Language', on_delete=models.CASCADE, related_name='podcast_episodes')

    # Episode metadata
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    episode_number = models.IntegerField(default=1)

    # Content
    script = models.TextField(help_text="Generated podcast script")
    audio_url = models.URLField(blank=True, help_text="URL to podcast audio file")
    transcript = models.TextField(blank=True, help_text="Full transcript with timestamps")

    # AI generation metadata
    concepts_used = models.JSONField(default=list, help_text="Array of concept IDs used")
    words_used = models.JSONField(default=list, help_text="Array of word IDs used")
    difficulty_level = models.IntegerField(default=1, help_text="1-10 scale")

    # Anki-based content selection
    new_concepts_count = models.IntegerField(default=0)
    review_concepts_count = models.IntegerField(default=0)
    optimal_repetition_mix = models.JSONField(default=dict, help_text="Anki-calculated content mix")

    # User interaction
    listened = models.BooleanField(default=False)
    listened_at = models.DateTimeField(null=True, blank=True)
    user_rating = models.IntegerField(null=True, blank=True, help_text="1-5 stars")
    user_feedback = models.TextField(blank=True)

    # Generation details
    generation_model = models.CharField(max_length=100, default='smolagents+gemini-2.0-flash')
    generation_time_seconds = models.IntegerField(null=True, blank=True)
    generation_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'mala_podcast_episodes'
        verbose_name = 'Podcast Episode'
        verbose_name_plural = 'Podcast Episodes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'language']),
            models.Index(fields=['created_at']),
            models.Index(fields=['listened']),
        ]

    def __str__(self):
        return f"{self.title} - Episode {self.episode_number}"


class PodcastSegment(TimeStampedModel):
    """Individual segments within a podcast episode"""
    SEGMENT_TYPES = [
        ('intro', 'Introduction'),
        ('vocabulary', 'Vocabulary'),
        ('dialogue', 'Dialogue'),
        ('grammar', 'Grammar Explanation'),
        ('story', 'Story'),
        ('quiz', 'Interactive Quiz'),
        ('recap', 'Recap'),
        ('outro', 'Outro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(PodcastEpisode, on_delete=models.CASCADE, related_name='segments')

    # Segment details
    segment_type = models.CharField(max_length=50, choices=SEGMENT_TYPES)
    sequence_order = models.IntegerField()
    title = models.CharField(max_length=255, blank=True)

    # Content
    script = models.TextField()
    audio_url = models.URLField(blank=True)
    start_time_seconds = models.IntegerField(default=0)
    duration_seconds = models.IntegerField(null=True, blank=True)

    # Related learning content
    concept = models.ForeignKey('languages.Concept', on_delete=models.SET_NULL, null=True, blank=True, related_name='podcast_segments')
    words = models.ManyToManyField('languages.Word', blank=True, related_name='podcast_segments')

    # Metadata
    difficulty = models.IntegerField(default=1, help_text="1-10 scale")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'mala_podcast_segments'
        verbose_name = 'Podcast Segment'
        verbose_name_plural = 'Podcast Segments'
        ordering = ['episode', 'sequence_order']
        unique_together = [['episode', 'sequence_order']]

    def __str__(self):
        return f"{self.episode.title} - {self.get_segment_type_display()} ({self.sequence_order})"


class PodcastGenerationJob(TimeStampedModel):
    """Job queue for podcast generation"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('selecting_content', 'Selecting Content'),
        ('generating_script', 'Generating Script'),
        ('generating_audio', 'Generating Audio'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    language = models.ForeignKey('languages.Language', on_delete=models.CASCADE)

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=5, help_text="1-10, higher = more important")

    # Job configuration
    target_duration_minutes = models.IntegerField(default=10)
    difficulty_preference = models.IntegerField(default=5, help_text="1-10 scale")
    include_quiz = models.BooleanField(default=True)

    # Results
    episode = models.ForeignKey(PodcastEpisode, on_delete=models.SET_NULL, null=True, blank=True, related_name='generation_jobs')
    error_message = models.TextField(blank=True)

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'mala_podcast_generation_jobs'
        verbose_name = 'Podcast Generation Job'
        verbose_name_plural = 'Podcast Generation Jobs'
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        return f"Podcast Job {self.id} - {self.status}"
