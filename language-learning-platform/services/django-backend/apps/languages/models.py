"""
Django models for Language Learning Platform (MALA)
All tables prefixed with 'mala_'
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.postgres.fields import ArrayField
import uuid


class TimeStampedModel(models.Model):
    """Abstract base model with timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Language(TimeStampedModel):
    """Languages available for learning"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True, help_text="ISO 639-1 code (e.g., 'en', 'fr', 'zh-TW')")
    native_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'mala_languages'
        verbose_name = 'Language'
        verbose_name_plural = 'Languages'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class UserLanguage(TimeStampedModel):
    """User language enrollment (many-to-many)"""
    PROFICIENCY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('native', 'Native'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='user_enrollments')
    proficiency_level = models.CharField(max_length=20, choices=PROFICIENCY_CHOICES, default='beginner')
    daily_goal_minutes = models.IntegerField(default=15)
    started_at = models.DateTimeField(auto_now_add=True)
    last_practiced_at = models.DateTimeField(null=True, blank=True)
    total_study_time_minutes = models.IntegerField(default=0)

    class Meta:
        db_table = 'mala_user_languages'
        verbose_name = 'User Language'
        verbose_name_plural = 'User Languages'
        unique_together = [['user_id', 'language']]

    def __str__(self):
        return f"User {self.user_id} - {self.language.name}"


class Concept(TimeStampedModel):
    """Learning concepts (phrases, grammar, vocabulary)"""
    CONCEPT_TYPES = [
        ('phrase', 'Phrase'),
        ('grammar', 'Grammar'),
        ('vocabulary', 'Vocabulary'),
        ('idiom', 'Idiom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='concepts')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    concept_type = models.CharField(max_length=50, choices=CONCEPT_TYPES)
    difficulty_level = models.IntegerField(default=1, help_text="1-10 scale")
    category = models.CharField(max_length=100, blank=True)
    prerequisites = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = 'mala_concepts'
        verbose_name = 'Concept'
        verbose_name_plural = 'Concepts'
        ordering = ['language', 'difficulty_level', 'title']
        indexes = [
            models.Index(fields=['language', 'concept_type']),
            models.Index(fields=['difficulty_level']),
        ]

    def __str__(self):
        return f"{self.title} ({self.language.code})"


class Word(TimeStampedModel):
    """Words within concepts"""
    PART_OF_SPEECH_CHOICES = [
        ('noun', 'Noun'),
        ('verb', 'Verb'),
        ('adjective', 'Adjective'),
        ('adverb', 'Adverb'),
        ('pronoun', 'Pronoun'),
        ('preposition', 'Preposition'),
        ('conjunction', 'Conjunction'),
        ('interjection', 'Interjection'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='words')
    word = models.TextField()
    translation = models.TextField()
    pronunciation = models.TextField(blank=True, help_text="IPA or pinyin")
    romanization = models.TextField(blank=True, help_text="For languages like Mandarin")
    part_of_speech = models.CharField(max_length=50, choices=PART_OF_SPEECH_CHOICES, blank=True)
    example_sentence = models.TextField(blank=True)
    example_translation = models.TextField(blank=True)
    audio_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    frequency_rank = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'mala_words'
        verbose_name = 'Word'
        verbose_name_plural = 'Words'
        ordering = ['concept', 'word']

    def __str__(self):
        return f"{self.word} - {self.translation}"


class UserConceptProgress(TimeStampedModel):
    """Track user progress on concepts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='user_progress')
    mastery_level = models.DecimalField(max_digits=3, decimal_places=2, default=0.0, help_text="0.0 to 1.0")
    review_count = models.IntegerField(default=0)
    correct_count = models.IntegerField(default=0)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    next_review_date = models.DateTimeField(null=True, blank=True)
    is_learning = models.BooleanField(default=True)

    class Meta:
        db_table = 'mala_user_concept_progress'
        verbose_name = 'User Concept Progress'
        verbose_name_plural = 'User Concept Progress'
        unique_together = [['user_id', 'concept']]
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['next_review_date']),
        ]

    def __str__(self):
        return f"User {self.user_id} - {self.concept.title} ({self.mastery_level})"


class Flashcard(TimeStampedModel):
    """Flashcards for concepts"""
    CARD_TYPES = [
        ('basic', 'Basic'),
        ('cloze', 'Cloze'),
        ('audio', 'Audio'),
        ('image', 'Image'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='flashcards')
    front = models.TextField()
    back = models.TextField()
    card_type = models.CharField(max_length=50, choices=CARD_TYPES, default='basic')
    hint = models.TextField(blank=True)
    audio_front_url = models.URLField(blank=True)
    audio_back_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    is_ai_generated = models.BooleanField(default=False)

    class Meta:
        db_table = 'mala_flashcards'
        verbose_name = 'Flashcard'
        verbose_name_plural = 'Flashcards'

    def __str__(self):
        return f"{self.concept.title} - {self.front[:50]}"


class Story(TimeStampedModel):
    """AI-generated stories for concepts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='stories')
    title = models.CharField(max_length=255)
    content = models.TextField()
    difficulty = models.IntegerField(default=1, help_text="1-10 scale")
    estimated_reading_time = models.IntegerField(null=True, blank=True, help_text="Minutes")
    audio_url = models.URLField(blank=True)
    cover_image_url = models.URLField(blank=True)
    vocabulary = models.JSONField(default=list, blank=True, help_text="Array of key words")
    is_ai_generated = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'mala_stories'
        verbose_name = 'Story'
        verbose_name_plural = 'Stories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['concept', 'difficulty']),
        ]

    def __str__(self):
        return self.title


class Quiz(TimeStampedModel):
    """Quizzes for concepts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    questions = models.JSONField(help_text="Array of question objects")
    passing_score = models.IntegerField(default=70)
    time_limit_minutes = models.IntegerField(null=True, blank=True)
    is_ai_generated = models.BooleanField(default=False)

    class Meta:
        db_table = 'mala_quizzes'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return self.title


class QuizAttempt(models.Model):
    """User quiz attempts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField()
    answers = models.JSONField()
    time_taken_seconds = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mala_quiz_attempts'
        verbose_name = 'Quiz Attempt'
        verbose_name_plural = 'Quiz Attempts'
        ordering = ['-completed_at']

    def __str__(self):
        return f"User {self.user_id} - {self.quiz.title} ({self.score}%)"


class SpacedRepetitionCard(TimeStampedModel):
    """Anki-based spaced repetition cards"""
    CARD_STATES = [
        ('new', 'New'),
        ('learning', 'Learning'),
        ('review', 'Review'),
        ('relearning', 'Relearning'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE, null=True, blank=True, related_name='srs_cards')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, null=True, blank=True, related_name='srs_cards')
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, null=True, blank=True, related_name='srs_cards')

    # Anki algorithm fields
    ease_factor = models.DecimalField(max_digits=4, decimal_places=2, default=2.50)
    interval_days = models.IntegerField(default=1)
    repetitions = models.IntegerField(default=0)
    lapses = models.IntegerField(default=0)

    # State
    card_state = models.CharField(max_length=20, choices=CARD_STATES, default='new')
    due_date = models.DateTimeField()
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'mala_spaced_repetition_cards'
        verbose_name = 'SRS Card'
        verbose_name_plural = 'SRS Cards'
        indexes = [
            models.Index(fields=['user_id', 'due_date']),
            models.Index(fields=['card_state']),
        ]

    def __str__(self):
        return f"SRS Card {self.id} - {self.card_state}"


class ReviewLog(models.Model):
    """Review history for SRS"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    srs_card = models.ForeignKey(SpacedRepetitionCard, on_delete=models.CASCADE, related_name='review_logs')
    rating = models.IntegerField(help_text="1 (again), 2 (hard), 3 (good), 4 (easy)")
    time_taken_seconds = models.IntegerField(null=True, blank=True)
    previous_ease_factor = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    new_ease_factor = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    previous_interval_days = models.IntegerField(null=True)
    new_interval_days = models.IntegerField(null=True)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mala_review_logs'
        verbose_name = 'Review Log'
        verbose_name_plural = 'Review Logs'
        ordering = ['-reviewed_at']

    def __str__(self):
        return f"Review {self.id} - Rating {self.rating}"


class TutoringSession(TimeStampedModel):
    """Pipecat tutoring sessions"""
    SESSION_TYPES = [
        ('conversation', 'Conversation'),
        ('pronunciation', 'Pronunciation'),
        ('grammar_practice', 'Grammar Practice'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='tutoring_sessions')
    concept = models.ForeignKey(Concept, on_delete=models.SET_NULL, null=True, blank=True, related_name='tutoring_sessions')
    session_type = models.CharField(max_length=50, choices=SESSION_TYPES, default='conversation')
    duration_seconds = models.IntegerField(null=True, blank=True)
    transcript = models.JSONField(default=list, blank=True)
    feedback = models.JSONField(default=dict, blank=True)
    recording_url = models.URLField(blank=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'mala_tutoring_sessions'
        verbose_name = 'Tutoring Session'
        verbose_name_plural = 'Tutoring Sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f"Session {self.id} - {self.session_type}"


class AIGenerationJob(TimeStampedModel):
    """Queue for AI content generation"""
    JOB_TYPES = [
        ('story', 'Story'),
        ('quiz', 'Quiz'),
        ('flashcards', 'Flashcards'),
        ('video', 'Video'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='ai_jobs')
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=5, help_text="1-10, higher = more important")
    parameters = models.JSONField(default=dict, blank=True)
    result_id = models.UUIDField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'mala_ai_generation_jobs'
        verbose_name = 'AI Generation Job'
        verbose_name_plural = 'AI Generation Jobs'
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
        ]

    def __str__(self):
        return f"{self.job_type} - {self.status}"


class UserPreferences(TimeStampedModel):
    """User settings and preferences"""
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ]

    user_id = models.UUIDField(primary_key=True)
    native_language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True, related_name='native_users')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    notifications_enabled = models.BooleanField(default=True)
    daily_reminder_time = models.TimeField(null=True, blank=True)
    audio_autoplay = models.BooleanField(default=True)
    study_streak_days = models.IntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)
    preferences = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'mala_user_preferences'
        verbose_name = 'User Preferences'
        verbose_name_plural = 'User Preferences'

    def __str__(self):
        return f"Preferences for User {self.user_id}"
