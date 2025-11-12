"""
Pipecat Real-time Language Tutoring Service

This service provides real-time audio tutoring sessions using:
- Pipecat for audio pipeline management
- Google Gemini 2.0 Flash for multimodal AI
- Daily.co for WebRTC transport
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import settings
from services.tutoring_session import TutoringSessionManager
from services.gemini_service import GeminiService
from services.supabase_client import SupabaseClient
from models.session import SessionCreate, SessionResponse

# Configure logging
logger.add(
    "logs/pipecat_service_{time}.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Starting Pipecat Language Tutoring Service")

    # Initialize services
    app.state.supabase = SupabaseClient()
    app.state.gemini = GeminiService()
    app.state.session_manager = TutoringSessionManager()

    yield

    # Cleanup
    logger.info("🛑 Shutting down Pipecat service")
    await app.state.session_manager.cleanup_all_sessions()


# Create FastAPI app
app = FastAPI(
    title="Pipecat Language Tutoring API",
    description="Real-time audio tutoring service for language learning",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": settings.SERVICE_NAME,
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "gemini": "connected",
        "database": "connected"
    }


@app.post("/sessions", response_model=SessionResponse)
async def create_tutoring_session(
    session_data: SessionCreate,
    session_manager: TutoringSessionManager = Depends(lambda: app.state.session_manager)
):
    """
    Create a new tutoring session.

    Args:
        session_data: Session configuration
        - user_id: User UUID
        - language_id: Language UUID
        - concept_id: Optional concept to focus on
        - session_type: conversation, pronunciation, grammar_practice
    """
    try:
        session = await session_manager.create_session(session_data)
        return session
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/tutoring/{session_id}")
async def websocket_tutoring_endpoint(
    websocket: WebSocket,
    session_id: str,
    session_manager: TutoringSessionManager = Depends(lambda: app.state.session_manager)
):
    """
    WebSocket endpoint for real-time tutoring sessions.

    Handles bidirectional audio streaming:
    - Client sends audio chunks (user speech)
    - Server sends audio chunks (AI tutor speech)
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for session {session_id}")

    try:
        # Get or create session
        session = await session_manager.get_session(session_id)
        if not session:
            await websocket.close(code=1008, reason="Session not found")
            return

        # Start tutoring session
        await session_manager.run_session(session_id, websocket)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))

    finally:
        logger.info(f"WebSocket connection closed for session {session_id}")


@app.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    session_manager: TutoringSessionManager = Depends(lambda: app.state.session_manager)
):
    """End a tutoring session and save results."""
    try:
        result = await session_manager.end_session(session_id)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    session_manager: TutoringSessionManager = Depends(lambda: app.state.session_manager)
):
    """Get session details."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/sessions/{session_id}/transcript")
async def get_session_transcript(session_id: str):
    """Get session transcript."""
    # TODO: Implement transcript retrieval from database
    return {"session_id": session_id, "transcript": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
