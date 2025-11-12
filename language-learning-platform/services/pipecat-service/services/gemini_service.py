"""
Google Gemini Service Integration

Handles all Gemini API interactions including:
- Speech-to-text transcription
- Text-to-speech synthesis
- LLM conversation
- Multimodal understanding (Veo3 for video/image)
- Content generation
"""
import google.generativeai as genai
from typing import Dict, List, Optional
from loguru import logger
import base64
import asyncio

from config import settings


class GeminiService:
    """Service for interacting with Google Gemini API."""

    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)

        # Models
        self.flash_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        self.vision_model = genai.GenerativeModel("gemini-2.0-flash-exp")  # For multimodal

    async def transcribe_audio(
        self,
        audio_data: bytes,
        language_code: str = "en"
    ) -> Optional[str]:
        """
        Transcribe audio using Gemini's multimodal capabilities.

        Args:
            audio_data: Raw audio bytes
            language_code: Target language code

        Returns:
            Transcribed text or None if failed
        """
        try:
            # Encode audio to base64
            audio_b64 = base64.b64encode(audio_data).decode()

            # Use Gemini for transcription
            prompt = f"Transcribe this audio in {language_code}. Only return the transcription, no other text."

            response = await asyncio.to_thread(
                self.flash_model.generate_content,
                [
                    {
                        "mime_type": "audio/wav",
                        "data": audio_b64
                    },
                    prompt
                ]
            )

            return response.text.strip()

        except Exception as e:
            logger.error(f"Audio transcription error: {e}")
            return None

    async def generate_response(
        self,
        messages: List[Dict],
        system_prompt: str,
        temperature: float = 0.7
    ) -> str:
        """
        Generate conversational response using Gemini.

        Args:
            messages: Conversation history
            system_prompt: System instructions
            temperature: Response randomness (0-1)

        Returns:
            Generated response text
        """
        try:
            # Format messages for Gemini
            chat = self.flash_model.start_chat(history=[])

            # Add system context
            full_prompt = f"{system_prompt}\n\n"

            # Add conversation history
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                full_prompt += f"{role}: {content}\n"

            # Generate response
            response = await asyncio.to_thread(
                chat.send_message,
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=1024,
                )
            )

            return response.text

        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return "I apologize, I'm having trouble generating a response right now."

    async def analyze_pronunciation(
        self,
        audio_data: bytes,
        expected_text: str,
        language_code: str
    ) -> Dict:
        """
        Analyze pronunciation quality.

        Args:
            audio_data: User's audio
            expected_text: What they should have said
            language_code: Language code

        Returns:
            Analysis with score and feedback
        """
        try:
            # Transcribe what they actually said
            actual_text = await self.transcribe_audio(audio_data, language_code)

            # Use Gemini to analyze
            prompt = f"""Analyze this pronunciation attempt:

Expected: "{expected_text}"
Actual: "{actual_text}"
Language: {language_code}

Provide:
1. Pronunciation score (0-100)
2. Specific feedback on mispronounced words
3. Suggestions for improvement

Format as JSON with fields: score, feedback, suggestions"""

            response = await asyncio.to_thread(
                self.flash_model.generate_content,
                prompt
            )

            # Parse response (would need proper JSON parsing in production)
            return {
                "actual_text": actual_text,
                "expected_text": expected_text,
                "analysis": response.text
            }

        except Exception as e:
            logger.error(f"Pronunciation analysis error: {e}")
            return {
                "error": str(e),
                "score": 0
            }

    async def generate_session_feedback(
        self,
        transcript: List[Dict],
        language_code: str
    ) -> Dict:
        """
        Generate AI feedback for a tutoring session.

        Args:
            transcript: Session conversation transcript
            language_code: Language being practiced

        Returns:
            Structured feedback
        """
        try:
            # Create summary prompt
            conversation = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in transcript
            ])

            prompt = f"""Analyze this language learning session transcript and provide feedback:

{conversation}

Language: {language_code}

Provide comprehensive feedback including:
1. Overall performance score (0-100)
2. Strengths (what they did well)
3. Areas for improvement
4. Specific grammar/vocabulary corrections needed
5. Recommended next steps

Format as JSON with fields: score, strengths, improvements, corrections, next_steps"""

            response = await asyncio.to_thread(
                self.flash_model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more consistent feedback
                )
            )

            return {
                "raw_feedback": response.text,
                "message_count": len(transcript)
            }

        except Exception as e:
            logger.error(f"Feedback generation error: {e}")
            return {"error": str(e)}

    async def generate_story(
        self,
        concept_title: str,
        concept_description: str,
        language_code: str,
        difficulty: int = 1
    ) -> Dict:
        """
        Generate a short story for a concept using Gemini.

        Args:
            concept_title: The concept to teach
            concept_description: Description of the concept
            language_code: Target language
            difficulty: Difficulty level (1-10)

        Returns:
            Generated story with metadata
        """
        try:
            language_name = settings.SUPPORTED_LANGUAGES.get(language_code, {}).get("name", language_code)

            prompt = f"""Create a short story in {language_name} that teaches this concept:

Concept: {concept_title}
Description: {concept_description}
Difficulty Level: {difficulty}/10

Requirements:
1. Story length: 150-300 words
2. Use vocabulary appropriate for difficulty level {difficulty}
3. Incorporate the concept naturally into the story
4. Include dialogue if appropriate
5. Make it engaging and memorable

Format as JSON with:
- title: Story title
- content: The story text
- vocabulary: Array of key words used (with translations)
- reading_time: Estimated reading time in minutes
"""

            response = await asyncio.to_thread(
                self.flash_model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.8,  # Higher for creative content
                )
            )

            return {
                "content": response.text,
                "generated_at": "now",
                "ai_model": settings.GEMINI_MODEL
            }

        except Exception as e:
            logger.error(f"Story generation error: {e}")
            return {"error": str(e)}

    async def generate_quiz(
        self,
        concept_title: str,
        concept_description: str,
        language_code: str,
        question_count: int = 5
    ) -> Dict:
        """
        Generate a quiz for a concept.

        Args:
            concept_title: The concept to test
            concept_description: Description of the concept
            language_code: Target language
            question_count: Number of questions to generate

        Returns:
            Quiz with questions and answers
        """
        try:
            language_name = settings.SUPPORTED_LANGUAGES.get(language_code, {}).get("name", language_code)

            prompt = f"""Create a quiz in {language_name} to test this concept:

Concept: {concept_title}
Description: {concept_description}

Generate {question_count} questions with these types:
- Multiple choice
- Fill in the blank
- Translation
- True/false

Format as JSON array with each question having:
- type: Question type
- question: The question text
- options: Array of options (for multiple choice)
- correct_answer: The correct answer
- explanation: Why this is correct
"""

            response = await asyncio.to_thread(
                self.flash_model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.6,
                )
            )

            return {
                "questions": response.text,
                "question_count": question_count,
                "ai_model": settings.GEMINI_MODEL
            }

        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            return {"error": str(e)}

    async def generate_flashcards(
        self,
        concept_title: str,
        words: List[Dict],
        language_code: str,
        count: int = 10
    ) -> List[Dict]:
        """
        Generate flashcards for a concept.

        Args:
            concept_title: The concept
            words: List of words with translations
            language_code: Target language
            count: Number of flashcards to generate

        Returns:
            List of flashcard objects
        """
        try:
            words_text = "\n".join([
                f"{w.get('word')} - {w.get('translation')}"
                for w in words[:count]
            ])

            prompt = f"""Create {count} flashcards for learning these words:

Concept: {concept_title}
Words:
{words_text}

For each word, create:
- front: The word in the target language
- back: Translation, pronunciation, example sentence
- hint: A helpful memory aid

Format as JSON array."""

            response = await asyncio.to_thread(
                self.flash_model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                )
            )

            return {
                "flashcards": response.text,
                "count": count
            }

        except Exception as e:
            logger.error(f"Flashcard generation error: {e}")
            return []

    async def analyze_image_or_video(
        self,
        media_data: bytes,
        media_type: str,
        prompt: str,
        language_code: str = "en"
    ) -> str:
        """
        Analyze image or video using Gemini's multimodal capabilities (Veo3).

        Args:
            media_data: Image or video bytes
            media_type: "image" or "video"
            prompt: Analysis prompt
            language_code: Response language

        Returns:
            Analysis text
        """
        try:
            # Encode media
            media_b64 = base64.b64encode(media_data).decode()

            # Determine MIME type
            mime_type = "image/jpeg" if media_type == "image" else "video/mp4"

            # Use vision model for multimodal analysis
            response = await asyncio.to_thread(
                self.vision_model.generate_content,
                [
                    {
                        "mime_type": mime_type,
                        "data": media_b64
                    },
                    f"Language: {language_code}\n{prompt}"
                ]
            )

            return response.text

        except Exception as e:
            logger.error(f"Multimodal analysis error: {e}")
            return f"Error analyzing media: {str(e)}"
