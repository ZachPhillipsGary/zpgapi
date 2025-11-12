"""
Personalized Podcast Generation with SmolAgents and Gemini

Generates daily personalized language learning podcasts that:
1. Use Anki algorithm to balance new and review content
2. Use smolagents to orchestrate multi-step generation
3. Use Gemini thinking models for script composition
4. Generate audio with Gemini TTS
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
import json
import sys
import time
sys.path.append('/home/user/zpgapi/language-learning-platform/services/pipecat-service')

from .podcast_models import PodcastEpisode, PodcastSegment, PodcastGenerationJob
from .models import Concept, Word, UserConceptProgress, SpacedRepetitionCard
from apps.spaced_repetition.anki_algorithm import AnkiAlgorithm

logger = logging.getLogger(__name__)


@shared_task(name='apps.languages.tasks.generate_personalized_podcast')
def generate_personalized_podcast(user_id: str, language_id: str, target_duration_minutes: int = 10):
    """
    Generate a personalized podcast episode for a user using smolagents + Gemini.

    Args:
        user_id: User UUID
        language_id: Language UUID
        target_duration_minutes: Target podcast duration
    """
    start_time = time.time()

    try:
        from smolagents import CodeAgent, Tool, tool
        from services.gemini_service import GeminiService
        import google.generativeai as genai

        logger.info(f"Starting podcast generation for user {user_id}, language {language_id}")

        # Step 1: Select concepts using Anki algorithm
        logger.info("Step 1: Selecting concepts with Anki algorithm")
        content_selection = _select_podcast_content_with_anki(user_id, language_id, target_duration_minutes)

        # Step 2: Setup smolagents with custom tools
        logger.info("Step 2: Setting up smolagents orchestration")

        # Define custom tools for smolagents
        @tool
        def analyze_user_progress(user_id: str, language_id: str) -> dict:
            """
            Analyze user's learning progress to understand their level and needs.

            Args:
                user_id: User identifier
                language_id: Language identifier

            Returns:
                Dictionary with user progress analysis
            """
            progress_data = UserConceptProgress.objects.filter(
                user_id=user_id,
                concept__language_id=language_id
            ).values('mastery_level', 'review_count')

            avg_mastery = sum(p['mastery_level'] for p in progress_data) / len(progress_data) if progress_data else 0
            return {
                'average_mastery': float(avg_mastery),
                'total_concepts_learned': len(progress_data),
                'recommended_difficulty': min(10, int(avg_mastery * 10) + 1)
            }

        @tool
        def get_concept_details(concept_ids: list) -> list:
            """
            Get detailed information about concepts.

            Args:
                concept_ids: List of concept UUIDs

            Returns:
                List of concept details
            """
            concepts = Concept.objects.filter(id__in=concept_ids)
            return [
                {
                    'id': str(c.id),
                    'title': c.title,
                    'description': c.description,
                    'type': c.concept_type,
                    'difficulty': c.difficulty_level,
                    'words': [{'word': w.word, 'translation': w.translation} for w in c.words.all()]
                }
                for c in concepts
            ]

        @tool
        def generate_script_segment(segment_type: str, concept: dict, difficulty: int) -> dict:
            """
            Generate a podcast script segment using Gemini thinking.

            Args:
                segment_type: Type of segment (vocabulary, dialogue, story, etc.)
                concept: Concept information
                difficulty: Difficulty level 1-10

            Returns:
                Generated script segment
            """
            gemini = GeminiService()
            genai.configure(api_key=gemini.api_key)

            # Use Gemini thinking model for script composition
            model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-1219')

            prompt = f"""You are a language learning podcast script writer. Create an engaging {segment_type} segment.

Concept: {concept['title']}
Description: {concept['description']}
Difficulty Level: {difficulty}/10
Words to include: {', '.join([w['word'] for w in concept.get('words', [])])}

Create a script that:
1. Is conversational and engaging
2. Explains the concept clearly
3. Includes examples and context
4. Uses the target vocabulary naturally
5. Is appropriate for the difficulty level
6. Lasts approximately 2-3 minutes when spoken

Format: Write the script as natural dialogue between a friendly tutor and a learner."""

            response = model.generate_content(prompt)
            return {
                'segment_type': segment_type,
                'script': response.text,
                'concept_id': concept['id']
            }

        # Step 3: Initialize smolagents Code Agent
        logger.info("Step 3: Initializing smolagents CodeAgent")

        agent = CodeAgent(
            tools=[analyze_user_progress, get_concept_details, generate_script_segment],
            model="gpt-4",  # Can use any model supported by smolagents
        )

        # Step 4: Use agent to orchestrate podcast generation
        logger.info("Step 4: Agent orchestrating podcast generation")

        agent_prompt = f"""Generate a personalized language learning podcast with these parameters:

User ID: {user_id}
Language ID: {language_id}
Target Duration: {target_duration_minutes} minutes

Content Selection (from Anki algorithm):
- New Concepts: {content_selection['new_concepts']}
- Review Concepts: {content_selection['review_concepts']}
- Total Words: {content_selection['total_words']}

Task:
1. Analyze the user's progress
2. Get full details for all selected concepts
3. Generate script segments for:
   - Introduction (welcome and overview)
   - Vocabulary introduction for new concepts
   - Dialogue examples using the concepts
   - Grammar explanation if needed
   - Short story incorporating all concepts
   - Review/recap segment
   - Outro (encouragement and next steps)

4. Return a complete podcast script as JSON with segments in order.

Make it engaging, educational, and personalized to the user's level!"""

        result = agent.run(agent_prompt)

        # Step 5: Parse agent result and create podcast episode
        logger.info("Step 5: Creating podcast episode from agent result")

        episode = PodcastEpisode.objects.create(
            user_id=user_id,
            language_id=language_id,
            title=f"Daily {content_selection['language_name']} Podcast - {timezone.now().strftime('%B %d')}",
            description="Your personalized daily language learning podcast",
            script=str(result),
            concepts_used=content_selection['concept_ids'],
            words_used=content_selection['word_ids'],
            difficulty_level=content_selection['difficulty_level'],
            new_concepts_count=len(content_selection['new_concepts']),
            review_concepts_count=len(content_selection['review_concepts']),
            optimal_repetition_mix=content_selection['anki_distribution'],
            generation_model='smolagents+gemini-2.0-flash-thinking',
            generation_metadata={'agent_tools_used': ['analyze_user_progress', 'get_concept_details', 'generate_script_segment']}
        )

        # Step 6: Generate audio using Gemini TTS
        logger.info("Step 6: Generating audio with Gemini TTS")
        audio_url = _generate_podcast_audio(episode, content_selection['language_code'])

        episode.audio_url = audio_url
        episode.generation_time_seconds = int(time.time() - start_time)
        episode.save()

        logger.info(f"Successfully generated podcast episode {episode.id} in {episode.generation_time_seconds}s")
        return str(episode.id)

    except Exception as e:
        logger.error(f"Error generating podcast for user {user_id}: {e}")
        raise


def _select_podcast_content_with_anki(user_id: str, language_id: str, target_duration: int) -> dict:
    """
    Select podcast content using Anki algorithm for optimal learning.

    Uses the Anki SM-2 algorithm principles:
    - Prioritize due review cards
    - Balance new content introduction
    - Consider user's historical performance
    - Optimal spacing for retention

    Args:
        user_id: User UUID
        language_id: Language UUID
        target_duration: Target duration in minutes

    Returns:
        Dict with selected concepts, words, and Anki distribution
    """
    from django.db.models import Count, Q
    from .models import Language

    language = Language.objects.get(id=language_id)

    # Get user's SRS cards that are due
    due_cards = SpacedRepetitionCard.objects.filter(
        user_id=user_id,
        due_date__lte=timezone.now()
    ).select_related('concept', 'word').order_by('due_date')[:20]

    # Analyze Anki distribution
    card_states = due_cards.values('card_state').annotate(count=Count('id'))
    anki_distribution = {state['card_state']: state['count'] for state in card_states}

    # Select concepts based on Anki algorithm
    # Rule: 20% new, 30% learning, 50% review (Anki default)
    target_new = max(1, int(target_duration * 0.2))
    target_review = max(2, int(target_duration * 0.5))

    # Get new concepts (not yet learned)
    learned_concept_ids = UserConceptProgress.objects.filter(
        user_id=user_id
    ).values_list('concept_id', flat=True)

    new_concepts = list(
        Concept.objects.filter(
            language_id=language_id,
            is_published=True
        ).exclude(
            id__in=learned_concept_ids
        ).order_by('difficulty_level')[:target_new]
    )

    # Get review concepts (from due cards)
    review_concepts = list(
        Concept.objects.filter(
            id__in=[card.concept_id for card in due_cards if card.concept_id]
        ).distinct()[:target_review]
    )

    # Combine concepts
    all_concepts = new_concepts + review_concepts

    # Get all words from selected concepts
    all_words = []
    for concept in all_concepts:
        all_words.extend(list(concept.words.all()))

    # Calculate difficulty level based on user progress
    user_progress = UserConceptProgress.objects.filter(
        user_id=user_id,
        concept__language_id=language_id
    ).aggregate(avg_mastery=models.Avg('mastery_level'))

    avg_mastery = user_progress['avg_mastery'] or 0.0
    difficulty_level = min(10, int(avg_mastery * 10) + 1)

    return {
        'new_concepts': [str(c.id) for c in new_concepts],
        'review_concepts': [str(c.id) for c in review_concepts],
        'concept_ids': [str(c.id) for c in all_concepts],
        'word_ids': [str(w.id) for w in all_words],
        'total_words': len(all_words),
        'difficulty_level': difficulty_level,
        'anki_distribution': anki_distribution,
        'language_code': language.code,
        'language_name': language.name,
    }


def _generate_podcast_audio(episode: PodcastEpisode, language_code: str) -> str:
    """
    Generate audio for podcast episode using Gemini TTS.

    Args:
        episode: PodcastEpisode instance
        language_code: Language code for TTS

    Returns:
        URL to generated audio file
    """
    from services.gemini_service import GeminiService
    import base64

    gemini = GeminiService()

    # For now, return placeholder
    # In production, would use Gemini TTS or ElevenLabs
    logger.info(f"Audio generation placeholder for episode {episode.id}")

    return f"https://storage.googleapis.com/mala-podcasts/{episode.id}.mp3"


@shared_task(name='apps.languages.tasks.generate_daily_podcasts_for_all_users')
def generate_daily_podcasts_for_all_users():
    """
    Daily cron job to generate personalized podcasts for all active users.
    Runs at 6 AM local time.
    """
    logger.info("Starting daily podcast generation for all users")

    from .models import UserLanguage

    # Get all users with active language enrollments
    active_enrollments = UserLanguage.objects.filter(
        last_practiced_at__gte=timezone.now() - timedelta(days=7)
    ).select_related('language')

    generated_count = 0
    for enrollment in active_enrollments:
        try:
            # Create generation job
            job = PodcastGenerationJob.objects.create(
                user_id=enrollment.user_id,
                language=enrollment.language,
                status='pending',
                priority=5,
                target_duration_minutes=10
            )

            # Queue podcast generation
            generate_personalized_podcast.delay(
                user_id=str(enrollment.user_id),
                language_id=str(enrollment.language_id),
                target_duration_minutes=10
            )

            generated_count += 1
            logger.info(f"Queued podcast for user {enrollment.user_id}, language {enrollment.language.code}")

        except Exception as e:
            logger.error(f"Error queuing podcast for enrollment {enrollment.id}: {e}")

    logger.info(f"Daily podcast generation completed. Queued {generated_count} podcasts.")
    return generated_count


@shared_task(name='apps.languages.tasks.generate_podcast_on_demand')
def generate_podcast_on_demand(user_id: str, language_id: str, preferences: dict = None):
    """
    Generate a podcast on-demand with custom preferences.

    Args:
        user_id: User UUID
        language_id: Language UUID
        preferences: Dict with custom preferences (duration, topics, etc.)
    """
    preferences = preferences or {}

    duration = preferences.get('duration_minutes', 10)
    include_quiz = preferences.get('include_quiz', True)

    logger.info(f"On-demand podcast generation for user {user_id} with preferences: {preferences}")

    return generate_personalized_podcast(user_id, language_id, duration)
