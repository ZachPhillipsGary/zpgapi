"""
Tutoring Session Manager

Manages real-time tutoring sessions using Pipecat and Gemini.
Now integrated with AI Prompt Management System for versioned prompts.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from loguru import logger
import sys

# Add Django path to access prompt service
sys.path.insert(0, '/home/user/zpgapi/language-learning-platform/services/django-backend')

from pipecat.frames.frames import (
    AudioRawFrame,
    TextFrame,
    EndFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.services.google import GoogleLLMService, GoogleTTSService
from pipecat.transports.services.daily import DailyTransport

from models.session import SessionCreate, TutoringSession
from services.gemini_service import GeminiService
from services.supabase_client import SupabaseClient
from config import settings

# Import Django prompt service
try:
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
    django.setup()
    from apps.ai_prompts.services import get_prompt_service
    PROMPT_SERVICE_AVAILABLE = True
except Exception as e:
    logger.warning(f"Django prompt service not available: {e}")
    PROMPT_SERVICE_AVAILABLE = False


class TutoringSessionManager:
    """Manages tutoring sessions with Pipecat and Gemini."""

    def __init__(self):
        self.active_sessions: Dict[str, TutoringSession] = {}
        self.supabase = SupabaseClient()
        self.gemini = GeminiService()

    async def create_session(self, session_data: SessionCreate) -> TutoringSession:
        """Create a new tutoring session."""
        session_id = str(uuid.uuid4())

        # Get language configuration
        language_code = await self._get_language_code(session_data.language_id)

        # Create session object
        session = TutoringSession(
            id=session_id,
            user_id=session_data.user_id,
            language_id=session_data.language_id,
            concept_id=session_data.concept_id,
            session_type=session_data.session_type,
            language_code=language_code,
            started_at=datetime.now(),
        )

        # Save to database
        await self.supabase.create_tutoring_session(session)

        # Store in active sessions
        self.active_sessions[session_id] = session

        logger.info(f"Created tutoring session {session_id} for user {session_data.user_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[TutoringSession]:
        """Get an active session."""
        return self.active_sessions.get(session_id)

    async def run_session(self, session_id: str, websocket):
        """
        Run a tutoring session with real-time audio processing.

        This uses Pipecat to create a pipeline:
        1. User audio input → Speech-to-Text (Gemini)
        2. Text → LLM processing (Gemini) → Tutoring response
        3. Response text → Text-to-Speech (Gemini) → Audio output
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return

        try:
            # Get system prompt based on session type
            system_prompt = await self._get_system_prompt(session)

            # Initialize Gemini services
            llm = GoogleLLMService(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
            )

            tts = GoogleTTSService(
                api_key=settings.GEMINI_API_KEY,
                voice_id=settings.SUPPORTED_LANGUAGES[session.language_code]["voice"],
            )

            # Create pipeline
            pipeline = Pipeline([
                llm,  # Process user input with Gemini
                tts,  # Convert response to speech
            ])

            # Initialize transport (WebSocket in this case)
            # For production, use Daily.co or another WebRTC provider
            # transport = DailyTransport(...)

            # Set initial context
            await llm.set_context(system_prompt)

            # Process incoming audio/text
            while True:
                try:
                    # Receive data from WebSocket
                    data = await websocket.receive()

                    if "text" in data:
                        # Text message (for testing or chat)
                        user_text = data["text"]
                        session.transcript.append({
                            "role": "user",
                            "content": user_text,
                            "timestamp": datetime.now().isoformat()
                        })

                        # Process through pipeline
                        response = await self._process_text(pipeline, user_text, llm, tts)

                        # Send response
                        await websocket.send_json({
                            "type": "text",
                            "content": response["text"]
                        })

                        if response.get("audio"):
                            await websocket.send_bytes(response["audio"])

                        # Log to transcript
                        session.transcript.append({
                            "role": "assistant",
                            "content": response["text"],
                            "timestamp": datetime.now().isoformat()
                        })

                    elif "bytes" in data:
                        # Audio data
                        audio_data = data["bytes"]
                        # Process audio through Gemini STT
                        transcription = await self.gemini.transcribe_audio(
                            audio_data,
                            session.language_code
                        )

                        if transcription:
                            session.transcript.append({
                                "role": "user",
                                "content": transcription,
                                "timestamp": datetime.now().isoformat()
                            })

                            # Process through LLM
                            response = await self._process_text(
                                pipeline, transcription, llm, tts
                            )

                            # Send response
                            await websocket.send_json({
                                "type": "transcription",
                                "user": transcription,
                                "assistant": response["text"]
                            })

                            if response.get("audio"):
                                await websocket.send_bytes(response["audio"])

                            session.transcript.append({
                                "role": "assistant",
                                "content": response["text"],
                                "timestamp": datetime.now().isoformat()
                            })

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    break

        except Exception as e:
            logger.error(f"Session error: {e}")
        finally:
            # Save session data
            await self.end_session(session_id)

    async def _process_text(
        self, pipeline, text: str, llm, tts
    ) -> Dict:
        """Process text through the pipeline and get response."""
        # Send to LLM
        llm_response = await llm.process_text(text)

        # Convert to speech
        audio_response = await tts.synthesize(llm_response)

        return {
            "text": llm_response,
            "audio": audio_response
        }

    async def _get_system_prompt(self, session: TutoringSession) -> str:
        """Generate system prompt based on session configuration using versioned prompts."""
        language_name = settings.SUPPORTED_LANGUAGES[session.language_code]["name"]

        # Use versioned prompts if available, fallback to hardcoded
        if PROMPT_SERVICE_AVAILABLE:
            try:
                service = get_prompt_service()

                # Get base system prompt
                base_prompt_version = service.get_prompt_version(
                    'tutoring_system',
                    user_id=session.user_id
                )

                if base_prompt_version:
                    base_prompt = service.render_prompt(base_prompt_version, {
                        'language_name': language_name,
                        'session_type': session.session_type,
                        'concept_title': '',
                        'concept_description': ''
                    })
                else:
                    # Fallback to hardcoded
                    base_prompt = self._get_fallback_system_prompt(language_name, session.session_type)

                # Add context-specific additions if available
                if session.concept_id:
                    concept_data = await self.supabase.get_concept(session.concept_id)
                    if concept_data:
                        context_version = service.get_prompt_version(
                            'tutoring_context',
                            user_id=session.user_id
                        )

                        if context_version:
                            # Determine focus area based on session type
                            focus_map = {
                                'pronunciation': 'PRONUNCIATION',
                                'grammar_practice': 'GRAMMAR',
                                'conversation': 'CONVERSATION',
                                'vocabulary': 'VOCABULARY'
                            }
                            focus_area = focus_map.get(session.session_type, 'GENERAL')

                            context_prompt = service.render_prompt(context_version, {
                                'focus_area': focus_area,
                                'concept_title': concept_data.get('title', ''),
                                'concept_description': concept_data.get('description', '')
                            })
                            base_prompt += "\n\n" + context_prompt

                return base_prompt

            except Exception as e:
                logger.error(f"Error using prompt service: {e}, falling back to hardcoded")
                return self._get_fallback_system_prompt(language_name, session.session_type)
        else:
            return self._get_fallback_system_prompt(language_name, session.session_type)

    def _get_fallback_system_prompt(self, language_name: str, session_type: str) -> str:
        """Fallback to hardcoded system prompt if prompt service is unavailable."""
        base_prompt = f"""You are an expert {language_name} language tutor. Your goal is to help the student improve their {language_name} skills through natural conversation.

Guidelines:
1. Speak clearly and at an appropriate pace for the student's level
2. Provide corrections gently and explain why
3. Encourage the student and celebrate their progress
4. Ask follow-up questions to keep the conversation flowing
5. Use simple vocabulary and grammar for beginners, more complex for advanced students
6. Focus on pronunciation, grammar, and natural expression
"""

        if session_type == "pronunciation":
            base_prompt += """
Special focus: PRONUNCIATION
- Listen carefully to how the student pronounces words
- Provide specific feedback on pronunciation
- Use phonetic explanations when helpful
- Practice difficult sounds repeatedly
- Give examples of correct pronunciation
"""
        elif session_type == "grammar_practice":
            base_prompt += """
Special focus: GRAMMAR
- Identify and correct grammatical errors
- Explain grammar rules clearly
- Provide examples of correct usage
- Practice specific grammar points
- Build on previous corrections
"""

        return base_prompt

    async def _get_language_code(self, language_id: str) -> str:
        """Get language code from language ID."""
        language = await self.supabase.get_language(language_id)
        return language.get("code", "en")

    async def end_session(self, session_id: str) -> Dict:
        """End a session and save results."""
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return {}

        session.ended_at = datetime.now()
        session.duration_seconds = int(
            (session.ended_at - session.started_at).total_seconds()
        )

        # Generate AI feedback
        feedback = await self.gemini.generate_session_feedback(
            session.transcript,
            session.language_code
        )
        session.feedback = feedback

        # Save to database
        await self.supabase.update_tutoring_session(session_id, {
            "ended_at": session.ended_at.isoformat(),
            "duration_seconds": session.duration_seconds,
            "transcript": session.transcript,
            "feedback": feedback,
        })

        # Remove from active sessions
        del self.active_sessions[session_id]

        logger.info(f"Session {session_id} ended. Duration: {session.duration_seconds}s")
        return {
            "duration_seconds": session.duration_seconds,
            "message_count": len(session.transcript),
            "feedback": feedback
        }

    async def cleanup_all_sessions(self):
        """Cleanup all active sessions on shutdown."""
        logger.info("Cleaning up all active sessions...")
        for session_id in list(self.active_sessions.keys()):
            await self.end_session(session_id)
