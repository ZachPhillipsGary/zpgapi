"""Supabase client for database operations."""
from supabase import create_client, Client
from typing import Dict, Optional
from loguru import logger

from config import settings


class SupabaseClient:
    """Client for interacting with Supabase database."""

    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )

    async def create_tutoring_session(self, session) -> Dict:
        """Create a new tutoring session in the database."""
        try:
            data = {
                "id": session.id,
                "user_id": session.user_id,
                "language_id": session.language_id,
                "concept_id": session.concept_id,
                "session_type": session.session_type,
                "started_at": session.started_at.isoformat(),
            }

            result = self.client.table("tutoring_sessions").insert(data).execute()
            return result.data[0] if result.data else {}

        except Exception as e:
            logger.error(f"Database error creating session: {e}")
            return {}

    async def update_tutoring_session(self, session_id: str, updates: Dict) -> Dict:
        """Update a tutoring session."""
        try:
            result = self.client.table("tutoring_sessions") \
                .update(updates) \
                .eq("id", session_id) \
                .execute()

            return result.data[0] if result.data else {}

        except Exception as e:
            logger.error(f"Database error updating session: {e}")
            return {}

    async def get_language(self, language_id: str) -> Dict:
        """Get language by ID."""
        try:
            result = self.client.table("languages") \
                .select("*") \
                .eq("id", language_id) \
                .single() \
                .execute()

            return result.data if result.data else {}

        except Exception as e:
            logger.error(f"Database error fetching language: {e}")
            return {}

    async def get_concept(self, concept_id: str) -> Dict:
        """Get concept by ID."""
        try:
            result = self.client.table("concepts") \
                .select("*") \
                .eq("id", concept_id) \
                .single() \
                .execute()

            return result.data if result.data else {}

        except Exception as e:
            logger.error(f"Database error fetching concept: {e}")
            return {}

    async def get_user_progress(self, user_id: str, concept_id: str) -> Optional[Dict]:
        """Get user's progress on a concept."""
        try:
            result = self.client.table("user_concept_progress") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("concept_id", concept_id) \
                .single() \
                .execute()

            return result.data if result.data else None

        except Exception as e:
            logger.error(f"Database error fetching progress: {e}")
            return None
