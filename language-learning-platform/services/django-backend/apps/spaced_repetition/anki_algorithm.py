"""
Anki Spaced Repetition Algorithm (SM-2 variant)

Based on the SuperMemo SM-2 algorithm used by Anki.
"""
from datetime import datetime, timedelta
from typing import Tuple
from decimal import Decimal


class AnkiAlgorithm:
    """
    Implements the Anki spaced repetition algorithm.

    Rating scale:
    - 1 (Again): Complete blackout, wrong response
    - 2 (Hard): Correct response with difficulty
    - 3 (Good): Correct response with some hesitation
    - 4 (Easy): Perfect response
    """

    # New card intervals (in minutes for learning phase)
    LEARNING_STEPS = [1, 10]  # 1 minute, then 10 minutes
    GRADUATING_INTERVAL = 1  # Days until card graduates to review
    EASY_INTERVAL = 4  # Days if card is marked as easy immediately

    # Review intervals
    STARTING_EASE = Decimal('2.50')  # Starting ease factor
    MINIMUM_EASE = Decimal('1.30')  # Minimum ease factor
    EASY_BONUS = Decimal('1.30')  # Multiplier for easy interval
    HARD_INTERVAL_MULTIPLIER = Decimal('1.20')  # Multiplier for hard cards

    # Ease factor adjustments
    EASE_AGAIN = Decimal('-0.20')  # -20% ease when failed
    EASE_HARD = Decimal('-0.15')   # -15% ease when hard
    EASE_GOOD = Decimal('0.00')    # No change for good
    EASE_EASY = Decimal('0.15')    # +15% ease when easy

    # Lapse settings
    LAPSE_STEPS = [10]  # Steps when relearning
    LAPSE_NEW_INTERVAL = Decimal('0.50')  # New interval is 50% of old
    LAPSE_MINIMUM_INTERVAL = 1  # Minimum interval after lapse (days)

    @staticmethod
    def calculate_next_review(
        rating: int,
        card_state: str,
        ease_factor: Decimal,
        interval_days: int,
        repetitions: int,
        lapses: int,
        step_index: int = 0
    ) -> Tuple[str, Decimal, int, int, int, datetime]:
        """
        Calculate the next review date and update card parameters.

        Args:
            rating: User rating (1-4)
            card_state: Current state ('new', 'learning', 'review', 'relearning')
            ease_factor: Current ease factor
            interval_days: Current interval in days
            repetitions: Number of successful repetitions
            lapses: Number of times card has lapsed
            step_index: Current step index for learning/relearning

        Returns:
            Tuple of (new_state, new_ease, new_interval, new_reps, new_lapses, due_date)
        """
        now = datetime.now()

        if card_state == 'new':
            return AnkiAlgorithm._process_new_card(rating, now)

        elif card_state == 'learning':
            return AnkiAlgorithm._process_learning_card(
                rating, ease_factor, repetitions, step_index, now
            )

        elif card_state == 'review':
            return AnkiAlgorithm._process_review_card(
                rating, ease_factor, interval_days, repetitions, lapses, now
            )

        elif card_state == 'relearning':
            return AnkiAlgorithm._process_relearning_card(
                rating, ease_factor, interval_days, lapses, step_index, now
            )

        else:
            raise ValueError(f"Invalid card state: {card_state}")

    @staticmethod
    def _process_new_card(rating: int, now: datetime) -> Tuple:
        """Process a new card."""
        if rating == 1:  # Again
            # Stay in learning, first step
            due = now + timedelta(minutes=AnkiAlgorithm.LEARNING_STEPS[0])
            return ('learning', AnkiAlgorithm.STARTING_EASE, 0, 0, 0, due)

        elif rating == 2:  # Hard
            # Move to learning, first step
            due = now + timedelta(minutes=AnkiAlgorithm.LEARNING_STEPS[0])
            return ('learning', AnkiAlgorithm.STARTING_EASE, 0, 0, 0, due)

        elif rating == 3:  # Good
            # Move to learning, first step
            due = now + timedelta(minutes=AnkiAlgorithm.LEARNING_STEPS[0])
            return ('learning', AnkiAlgorithm.STARTING_EASE, 0, 0, 0, due)

        else:  # Easy (4)
            # Graduate immediately
            due = now + timedelta(days=AnkiAlgorithm.EASY_INTERVAL)
            return ('review', AnkiAlgorithm.STARTING_EASE, AnkiAlgorithm.EASY_INTERVAL, 1, 0, due)

    @staticmethod
    def _process_learning_card(
        rating: int, ease_factor: Decimal, repetitions: int, step_index: int, now: datetime
    ) -> Tuple:
        """Process a card in the learning phase."""
        if rating == 1:  # Again - restart learning
            due = now + timedelta(minutes=AnkiAlgorithm.LEARNING_STEPS[0])
            return ('learning', ease_factor, 0, 0, 0, due)

        elif rating == 2:  # Hard - repeat current step
            due = now + timedelta(minutes=AnkiAlgorithm.LEARNING_STEPS[step_index])
            return ('learning', ease_factor, 0, repetitions, 0, due)

        elif rating == 3:  # Good - move to next step
            next_step = step_index + 1

            if next_step >= len(AnkiAlgorithm.LEARNING_STEPS):
                # Graduate to review
                due = now + timedelta(days=AnkiAlgorithm.GRADUATING_INTERVAL)
                return ('review', ease_factor, AnkiAlgorithm.GRADUATING_INTERVAL, repetitions + 1, 0, due)
            else:
                # Move to next learning step
                due = now + timedelta(minutes=AnkiAlgorithm.LEARNING_STEPS[next_step])
                return ('learning', ease_factor, 0, repetitions, 0, due)

        else:  # Easy (4) - graduate immediately
            due = now + timedelta(days=AnkiAlgorithm.EASY_INTERVAL)
            return ('review', ease_factor, AnkiAlgorithm.EASY_INTERVAL, repetitions + 1, 0, due)

    @staticmethod
    def _process_review_card(
        rating: int, ease_factor: Decimal, interval_days: int, repetitions: int, lapses: int, now: datetime
    ) -> Tuple:
        """Process a card in the review phase."""
        if rating == 1:  # Again - card has lapsed
            new_lapses = lapses + 1
            new_interval = max(
                AnkiAlgorithm.LAPSE_MINIMUM_INTERVAL,
                int(interval_days * AnkiAlgorithm.LAPSE_NEW_INTERVAL)
            )

            if AnkiAlgorithm.LAPSE_STEPS:
                # Enter relearning
                due = now + timedelta(minutes=AnkiAlgorithm.LAPSE_STEPS[0])
                new_ease = max(AnkiAlgorithm.MINIMUM_EASE, ease_factor + AnkiAlgorithm.EASE_AGAIN)
                return ('relearning', new_ease, new_interval, 0, new_lapses, due)
            else:
                # No relearning steps, go back to review
                due = now + timedelta(days=new_interval)
                new_ease = max(AnkiAlgorithm.MINIMUM_EASE, ease_factor + AnkiAlgorithm.EASE_AGAIN)
                return ('review', new_ease, new_interval, repetitions, new_lapses, due)

        elif rating == 2:  # Hard
            new_ease = max(AnkiAlgorithm.MINIMUM_EASE, ease_factor + AnkiAlgorithm.EASE_HARD)
            new_interval = max(1, int(interval_days * AnkiAlgorithm.HARD_INTERVAL_MULTIPLIER))
            due = now + timedelta(days=new_interval)
            return ('review', new_ease, new_interval, repetitions + 1, lapses, due)

        elif rating == 3:  # Good
            new_ease = ease_factor + AnkiAlgorithm.EASE_GOOD
            new_interval = max(1, int(interval_days * new_ease))
            due = now + timedelta(days=new_interval)
            return ('review', new_ease, new_interval, repetitions + 1, lapses, due)

        else:  # Easy (4)
            new_ease = ease_factor + AnkiAlgorithm.EASE_EASY
            easy_interval = int(interval_days * new_ease * AnkiAlgorithm.EASY_BONUS)
            new_interval = max(1, easy_interval)
            due = now + timedelta(days=new_interval)
            return ('review', new_ease, new_interval, repetitions + 1, lapses, due)

    @staticmethod
    def _process_relearning_card(
        rating: int, ease_factor: Decimal, interval_days: int, lapses: int, step_index: int, now: datetime
    ) -> Tuple:
        """Process a card in the relearning phase."""
        if rating == 1:  # Again - restart relearning
            due = now + timedelta(minutes=AnkiAlgorithm.LAPSE_STEPS[0])
            return ('relearning', ease_factor, interval_days, 0, lapses, due)

        elif rating == 2:  # Hard - repeat current step
            due = now + timedelta(minutes=AnkiAlgorithm.LAPSE_STEPS[step_index])
            return ('relearning', ease_factor, interval_days, 0, lapses, due)

        elif rating == 3:  # Good - complete relearning
            next_step = step_index + 1

            if next_step >= len(AnkiAlgorithm.LAPSE_STEPS):
                # Return to review
                due = now + timedelta(days=interval_days)
                return ('review', ease_factor, interval_days, 1, lapses, due)
            else:
                # Move to next relearning step
                due = now + timedelta(minutes=AnkiAlgorithm.LAPSE_STEPS[next_step])
                return ('relearning', ease_factor, interval_days, 0, lapses, due)

        else:  # Easy (4) - complete relearning with bonus
            new_interval = int(interval_days * AnkiAlgorithm.EASY_BONUS)
            due = now + timedelta(days=new_interval)
            return ('review', ease_factor, new_interval, 1, lapses, due)


def get_cards_due_for_review(user_id: str, limit: int = 20):
    """
    Get cards that are due for review for a specific user.

    This would typically query the database for cards where:
    - due_date <= now()
    - Ordered by due_date (oldest first)
    """
    from apps.spaced_repetition.models import SpacedRepetitionCard

    now = datetime.now()
    return SpacedRepetitionCard.objects.filter(
        user_id=user_id,
        due_date__lte=now
    ).order_by('due_date')[:limit]
