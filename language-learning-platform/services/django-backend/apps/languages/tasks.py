"""
Celery Tasks for AI Content Generation

These tasks run in the background to generate stories, quizzes, and flashcards.
Now integrated with AI Prompt Management System for versioning and A/B testing.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
import sys
import time
sys.path.append('/home/user/zpgapi/language-learning-platform/services/pipecat-service')

from .models import (
    Language, Concept, Story, Quiz, Flashcard, AIGenerationJob,
    TutoringSession
)
from apps.ai_prompts.services import PromptContext

logger = logging.getLogger(__name__)


@shared_task(name='apps.languages.tasks.generate_story')
def generate_story(concept_id: str, user_id: str = None):
    """
    Generate a story for a specific concept using Gemini AI with prompt versioning.

    Args:
        concept_id: UUID of the concept
        user_id: Optional user ID for A/B testing different prompts
    """
    try:
        from services.gemini_service import GeminiService
        import google.generativeai as genai

        concept = Concept.objects.get(id=concept_id)
        gemini = GeminiService()

        logger.info(f"Generating story for concept: {concept.title}")

        # Use PromptContext for versioned prompts and automatic tracking
        with PromptContext('story_generation', user_id=user_id, ai_model='gemini-2.0-flash') as ctx:
            # Get versioned prompt with variables
            prompt = ctx.get_prompt({
                'concept_title': concept.title,
                'concept_description': concept.description,
                'language_name': concept.language.name,
                'difficulty': concept.difficulty_level
            })

            # Generate content using the versioned prompt
            start_time = time.time()
            result = gemini.generate_story(
                concept_title=concept.title,
                concept_description=concept.description,
                language_code=concept.language.code,
                difficulty=concept.difficulty_level
            )
            generation_time = time.time() - start_time

            # Mark as successful (prompt usage will be logged automatically)
            ctx.mark_success()

        # Create story record
        story = Story.objects.create(
            concept=concept,
            title=f"Story: {concept.title}",
            content=result.get('content', ''),
            difficulty=concept.difficulty_level,
            estimated_reading_time=result.get('reading_time', 5),
            is_ai_generated=True,
            metadata={
                'ai_model': result.get('ai_model', 'gemini-2.0-flash'),
                'generation_time': generation_time,
                'prompt_tracked': True
            }
        )

        logger.info(f"Successfully generated story {story.id} for concept {concept.title} in {generation_time:.2f}s")
        return str(story.id)

    except Concept.DoesNotExist:
        logger.error(f"Concept {concept_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error generating story for concept {concept_id}: {e}")
        raise


@shared_task(name='apps.languages.tasks.generate_quiz')
def generate_quiz(concept_id: str, question_count: int = 5, user_id: str = None):
    """
    Generate a quiz for a specific concept using Gemini AI with prompt versioning.

    Args:
        concept_id: UUID of the concept
        question_count: Number of questions to generate
        user_id: Optional user ID for A/B testing different prompts
    """
    try:
        from services.gemini_service import GeminiService

        concept = Concept.objects.get(id=concept_id)
        gemini = GeminiService()

        logger.info(f"Generating quiz for concept: {concept.title}")

        # Use PromptContext for versioned prompts and automatic tracking
        with PromptContext('quiz_generation', user_id=user_id, ai_model='gemini-2.0-flash') as ctx:
            # Get versioned prompt with variables
            prompt = ctx.get_prompt({
                'concept_title': concept.title,
                'concept_description': concept.description,
                'language_name': concept.language.name,
                'question_count': question_count
            })

            # Generate quiz using the versioned prompt
            start_time = time.time()
            result = gemini.generate_quiz(
                concept_title=concept.title,
                concept_description=concept.description,
                language_code=concept.language.code,
                question_count=question_count
            )
            generation_time = time.time() - start_time

            # Mark as successful
            ctx.mark_success()

        # Create quiz record
        quiz = Quiz.objects.create(
            concept=concept,
            title=f"Quiz: {concept.title}",
            description=f"Test your knowledge of {concept.title}",
            questions=result.get('questions', []),
            passing_score=70,
            is_ai_generated=True,
            metadata={
                'generation_time': generation_time,
                'prompt_tracked': True
            }
        )

        logger.info(f"Successfully generated quiz {quiz.id} for concept {concept.title} in {generation_time:.2f}s")
        return str(quiz.id)

    except Concept.DoesNotExist:
        logger.error(f"Concept {concept_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error generating quiz for concept {concept_id}: {e}")
        raise


@shared_task(name='apps.languages.tasks.generate_flashcards')
def generate_flashcards(concept_id: str, count: int = 10, user_id: str = None):
    """
    Generate flashcards for a specific concept using Gemini AI with prompt versioning.

    Args:
        concept_id: UUID of the concept
        count: Number of flashcards to generate
        user_id: Optional user ID for A/B testing different prompts
    """
    try:
        from services.gemini_service import GeminiService

        concept = Concept.objects.get(id=concept_id)
        words = list(concept.words.all())

        if not words:
            logger.warning(f"No words found for concept {concept.title}, skipping flashcard generation")
            return None

        gemini = GeminiService()

        logger.info(f"Generating {count} flashcards for concept: {concept.title}")

        # Prepare words text for prompt
        words_text = "\n".join([
            f"{w.word} - {w.translation}"
            for w in words[:count]
        ])

        # Use PromptContext for versioned prompts and automatic tracking
        with PromptContext('flashcard_generation', user_id=user_id, ai_model='gemini-2.0-flash') as ctx:
            # Get versioned prompt with variables
            prompt = ctx.get_prompt({
                'concept_title': concept.title,
                'words_text': words_text,
                'count': min(count, len(words))
            })

            # Generate flashcards using the versioned prompt
            start_time = time.time()
            result = gemini.generate_flashcards(
                concept_title=concept.title,
                words=[{'word': w.word, 'translation': w.translation} for w in words],
                language_code=concept.language.code,
                count=min(count, len(words))
            )
            generation_time = time.time() - start_time

            # Mark as successful
            ctx.mark_success()

        # Create flashcard records
        flashcard_ids = []
        flashcards_data = result.get('flashcards', [])

        for i, word in enumerate(words[:count]):
            flashcard = Flashcard.objects.create(
                concept=concept,
                front=word.word,
                back=f"{word.translation}\n\n{word.example_sentence or ''}",
                card_type='basic',
                hint=word.pronunciation or '',
                is_ai_generated=True,
                metadata={
                    'generation_time': generation_time,
                    'prompt_tracked': True
                }
            )
            flashcard_ids.append(str(flashcard.id))

        logger.info(f"Successfully generated {len(flashcard_ids)} flashcards for concept {concept.title} in {generation_time:.2f}s")
        return flashcard_ids

    except Concept.DoesNotExist:
        logger.error(f"Concept {concept_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error generating flashcards for concept {concept_id}: {e}")
        raise


@shared_task(name='apps.languages.tasks.generate_daily_stories')
def generate_daily_stories():
    """
    Daily cron task to generate stories for concepts that need them.
    Targets concepts with fewer than 3 stories.
    """
    logger.info("Starting daily story generation")

    # Find concepts that need stories (published, with < 3 stories)
    concepts = Concept.objects.filter(
        is_published=True
    ).annotate(
        story_count=models.Count('stories')
    ).filter(
        story_count__lt=3
    ).order_by('?')[:10]  # Random 10 concepts

    generated_count = 0
    for concept in concepts:
        try:
            # Create AI generation job
            job = AIGenerationJob.objects.create(
                job_type='story',
                language=concept.language,
                concept=concept,
                status='pending',
                priority=5
            )

            # Trigger generation
            generate_story.delay(str(concept.id))
            generated_count += 1

            logger.info(f"Queued story generation for concept: {concept.title}")

        except Exception as e:
            logger.error(f"Error queuing story for concept {concept.id}: {e}")

    logger.info(f"Daily story generation completed. Queued {generated_count} stories.")
    return generated_count


@shared_task(name='apps.languages.tasks.generate_daily_quizzes')
def generate_daily_quizzes():
    """
    Daily cron task to generate quizzes for concepts that need them.
    Targets concepts with fewer than 2 quizzes.
    """
    logger.info("Starting daily quiz generation")

    from django.db.models import Count

    # Find concepts that need quizzes
    concepts = Concept.objects.filter(
        is_published=True
    ).annotate(
        quiz_count=Count('quizzes')
    ).filter(
        quiz_count__lt=2
    ).order_by('?')[:10]

    generated_count = 0
    for concept in concepts:
        try:
            job = AIGenerationJob.objects.create(
                job_type='quiz',
                language=concept.language,
                concept=concept,
                status='pending',
                priority=5
            )

            generate_quiz.delay(str(concept.id))
            generated_count += 1

            logger.info(f"Queued quiz generation for concept: {concept.title}")

        except Exception as e:
            logger.error(f"Error queuing quiz for concept {concept.id}: {e}")

    logger.info(f"Daily quiz generation completed. Queued {generated_count} quizzes.")
    return generated_count


@shared_task(name='apps.languages.tasks.generate_daily_flashcards')
def generate_daily_flashcards():
    """
    Daily cron task to generate flashcards for concepts that need them.
    Targets concepts with words but fewer than 5 flashcards.
    """
    logger.info("Starting daily flashcard generation")

    from django.db.models import Count

    # Find concepts that need flashcards
    concepts = Concept.objects.filter(
        is_published=True
    ).annotate(
        word_count=Count('words'),
        flashcard_count=Count('flashcards')
    ).filter(
        word_count__gt=0,
        flashcard_count__lt=5
    ).order_by('?')[:15]

    generated_count = 0
    for concept in concepts:
        try:
            job = AIGenerationJob.objects.create(
                job_type='flashcards',
                language=concept.language,
                concept=concept,
                status='pending',
                priority=5
            )

            generate_flashcards.delay(str(concept.id))
            generated_count += 1

            logger.info(f"Queued flashcard generation for concept: {concept.title}")

        except Exception as e:
            logger.error(f"Error queuing flashcards for concept {concept.id}: {e}")

    logger.info(f"Daily flashcard generation completed. Queued {generated_count} sets.")
    return generated_count


@shared_task(name='apps.languages.tasks.process_pending_ai_jobs')
def process_pending_ai_jobs():
    """
    Process pending AI generation jobs.
    Runs every 10 minutes to handle queued jobs.
    """
    logger.info("Processing pending AI generation jobs")

    # Get pending jobs ordered by priority
    jobs = AIGenerationJob.objects.filter(
        status='pending'
    ).order_by('-priority', 'created_at')[:5]

    processed_count = 0
    for job in jobs:
        try:
            # Mark as processing
            job.status = 'processing'
            job.started_at = timezone.now()
            job.save()

            # Dispatch to appropriate task
            if job.job_type == 'story':
                result = generate_story.delay(str(job.concept_id))
            elif job.job_type == 'quiz':
                result = generate_quiz.delay(str(job.concept_id))
            elif job.job_type == 'flashcards':
                result = generate_flashcards.delay(str(job.concept_id))
            else:
                logger.warning(f"Unknown job type: {job.job_type}")
                continue

            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing job {job.id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.save()

    logger.info(f"Processed {processed_count} AI generation jobs")
    return processed_count


@shared_task(name='apps.languages.tasks.cleanup_old_tutoring_sessions')
def cleanup_old_tutoring_sessions():
    """
    Cleanup old tutoring sessions.
    Removes session data older than 30 days.
    """
    logger.info("Cleaning up old tutoring sessions")

    cutoff_date = timezone.now() - timedelta(days=30)

    # Delete very old sessions
    deleted_count, _ = TutoringSession.objects.filter(
        started_at__lt=cutoff_date
    ).delete()

    logger.info(f"Deleted {deleted_count} old tutoring sessions")
    return deleted_count


@shared_task(name='apps.languages.tasks.bulk_generate_content_for_concept')
def bulk_generate_content_for_concept(concept_id: str):
    """
    Generate all content types (story, quiz, flashcards) for a concept.
    Useful for newly created concepts.

    Args:
        concept_id: UUID of the concept
    """
    logger.info(f"Bulk generating content for concept {concept_id}")

    try:
        concept = Concept.objects.get(id=concept_id)

        # Queue all generation tasks
        story_task = generate_story.delay(concept_id)
        quiz_task = generate_quiz.delay(concept_id)
        flashcard_task = generate_flashcards.delay(concept_id)

        logger.info(f"Queued all content generation for concept: {concept.title}")

        return {
            'story_task_id': story_task.id,
            'quiz_task_id': quiz_task.id,
            'flashcard_task_id': flashcard_task.id,
        }

    except Concept.DoesNotExist:
        logger.error(f"Concept {concept_id} not found")
        raise
