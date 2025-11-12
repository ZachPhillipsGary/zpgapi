# MALA Language Learning Platform - Django Backend

Django-first MVP with complete API, admin interface, and Celery task workers.

## 🌟 Features

### Core API (Auto-Generated Swagger Docs)
- **REST API** with automatic Swagger/OpenAPI documentation
- **Reusable API Framework** - Base classes for rapid endpoint development
- **Django Admin** - Full admin interface for content management
- **Supabase Auth** integration for users
- **Anki Spaced Repetition** algorithm implementation

### Content Generation (Celery Tasks)
- ✅ **Stories** - AI-generated stories for concepts
- ✅ **Quizzes** - Multi-format quizzes (multiple choice, fill-in-blank, translation)
- ✅ **Flashcards** - Spaced repetition flashcards
- 🆕 **Personalized Podcasts** - Daily AI-generated podcasts using smolagents + Gemini

### Learning Features
- **Learning Plans** - Curated paths with ordered concepts (many-to-many with users)
- **Progress Tracking** - User progress per concept and plan
- **Spaced Repetition** - Anki SM-2 algorithm for optimal review scheduling
- **Real-time Tutoring** - Pipecat integration for live audio sessions
- **Multimodal AI** - Gemini 2.0 Flash + Veo3 support

### Podcast Generation 🎙️ (NEW!)
- **Daily Personalized Podcasts** using smolagents orchestration
- **Anki-based Content Selection** - Optimal mix of new and review content
- **Gemini Thinking Models** for script composition
- **Voice Generation** with Gemini TTS
- **User Progress Adaptation** - Difficulty adjusts to user level

---

## 📊 Database Schema (All tables prefixed with `mala_`)

### Core Tables
- `mala_languages` - Available languages (FR, EN, ZH-TW)
- `mala_user_languages` - User enrollment (many-to-many)
- `mala_concepts` - Learning concepts (phrases, grammar, vocabulary)
- `mala_words` - Words within concepts
- `mala_user_concept_progress` - Progress tracking

### Learning Plans
- `mala_learning_plans` - Curated learning paths
- `mala_learning_plan_concepts` - Ordered concepts in plans
- `mala_user_learning_plans` - User enrollments
- `mala_user_plan_concept_progress` - Detailed progress

### Content
- `mala_flashcards` - Flashcard content
- `mala_stories` - AI-generated stories
- `mala_quizzes` - Quiz content
- `mala_quiz_attempts` - User quiz results

### Spaced Repetition (Anki)
- `mala_spaced_repetition_cards` - SRS cards with Anki algorithm fields
- `mala_review_logs` - Review history

### Podcasts 🆕
- `mala_podcast_episodes` - Generated podcast episodes
- `mala_podcast_segments` - Individual podcast segments
- `mala_podcast_generation_jobs` - Generation queue

### AI & Tutoring
- `mala_ai_generation_jobs` - Content generation queue
- `mala_tutoring_sessions` - Pipecat session records
- `mala_user_preferences` - User settings

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd services/django-backend

# Copy environment file
cp ../../.env.example .env
# Edit .env with your credentials

# Create virtual environment with uv
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### 2. Run Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Load initial data
python manage.py loaddata apps/languages/fixtures/initial_data.json
```

### 3. Create Admin User

```bash
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

### 5. Access Services

- **Django Admin**: http://localhost:8000/admin
- **API Root**: http://localhost:8000/api/v1/
- **Swagger Docs**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/

---

## 📖 API Documentation

### Auto-Generated Swagger

All endpoints are automatically documented with OpenAPI/Swagger:

```bash
# View schema
curl http://localhost:8000/api/schema/

# View Swagger UI
open http://localhost:8000/api/docs/
```

### Main Endpoints

#### Languages
```
GET    /api/v1/languages/                    # List all languages
GET    /api/v1/languages/active/             # Active languages only
GET    /api/v1/languages/{id}/               # Language details
POST   /api/v1/user-languages/               # Enroll in language
```

#### Concepts
```
GET    /api/v1/concepts/                     # List concepts
GET    /api/v1/concepts/{id}/                # Concept with words
GET    /api/v1/concepts/by_language/         # Filter by language
```

#### Learning Plans
```
GET    /api/v1/learning-plans/               # List plans
GET    /api/v1/learning-plans/{id}/          # Plan details with concepts
POST   /api/v1/user-learning-plans/          # Enroll in plan
GET    /api/v1/user-learning-plans/my_plans/ # User's enrolled plans
POST   /api/v1/user-learning-plans/{id}/complete_concept/  # Mark concept complete
```

#### Spaced Repetition
```
GET    /api/v1/srs-cards/due/                # Cards due for review
POST   /api/v1/srs-cards/{id}/review/        # Submit review (Anki algorithm)
GET    /api/v1/srs-cards/stats/              # User statistics
```

#### Content
```
GET    /api/v1/flashcards/by_concept/        # Flashcards for concept
GET    /api/v1/stories/                      # AI-generated stories
GET    /api/v1/quizzes/                      # Quizzes
POST   /api/v1/quiz-attempts/                # Submit quiz attempt
```

---

## 🔄 Celery Tasks

### Background Workers

```bash
# Start Celery worker
celery -A config worker -l info

# Start Celery Beat (scheduler)
celery -A config beat -l info

# Monitor with Flower
celery -A config flower
```

### Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `generate-daily-podcasts` | 6:00 AM | Generate personalized podcasts for all users |
| `generate-daily-stories` | 2:00 AM | Generate stories for concepts needing content |
| `generate-daily-quizzes` | 2:30 AM | Generate quizzes for concepts |
| `generate-daily-flashcards` | 3:00 AM | Generate flashcards for words |
| `process-ai-jobs` | Every 10 min | Process pending AI generation jobs |
| `cleanup-old-sessions` | 1:00 AM | Cleanup old tutoring sessions |

### Manual Task Execution

```python
from apps.languages.tasks import generate_story, generate_quiz, generate_flashcards
from apps.languages.podcast_tasks import generate_personalized_podcast

# Generate content for a concept
generate_story.delay(concept_id='uuid-here')
generate_quiz.delay(concept_id='uuid-here', question_count=5)
generate_flashcards.delay(concept_id='uuid-here', count=10)

# Generate podcast for a user
generate_personalized_podcast.delay(
    user_id='uuid-here',
    language_id='uuid-here',
    target_duration_minutes=10
)
```

---

## 🎙️ Personalized Podcast Generation

### How It Works

1. **Content Selection** - Anki algorithm selects optimal mix:
   - 20% new concepts
   - 30% learning concepts
   - 50% review concepts

2. **SmolAgents Orchestration** - Multi-step workflow:
   - Analyze user progress
   - Get concept details
   - Generate script segments

3. **Gemini Thinking** - Composes engaging script
4. **Voice Generation** - Gemini TTS creates audio

### Podcast Structure

Each podcast includes:
- Introduction
- Vocabulary introduction (new concepts)
- Dialogue examples
- Grammar explanation
- Short story using all concepts
- Interactive quiz (optional)
- Recap and outro

### API Usage

```bash
# Generate on-demand podcast
curl -X POST http://localhost:8000/api/v1/podcast-jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "uuid-here",
    "language_id": "uuid-here",
    "target_duration_minutes": 10
  }'

# Get user's podcasts
curl http://localhost:8000/api/v1/podcast-episodes/?user_id=uuid-here

# Listen to podcast
curl http://localhost:8000/api/v1/podcast-episodes/{id}/
```

---

## 🔧 Reusable API Framework

### Creating New Endpoints

The platform includes a reusable framework for rapid API development:

```python
from apps.core.api import BaseModelViewSet, BaseModelAdmin

# Create ViewSet (auto-generates serializer)
class MyModelViewSet(BaseModelViewSet):
    model = MyModel
    filterset_fields = ['field1', 'field2']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'name']

# Create Admin (auto-configures list display)
@admin.register(MyModel)
class MyModelAdmin(BaseModelAdmin):
    list_display_fields = ['name', 'status', 'created_at']
    search_fields = ['name']
    list_filter_fields = ['status']
```

### Features:
- ✅ Auto-generated serializers
- ✅ Auto-generated Swagger docs
- ✅ Built-in filtering, search, pagination
- ✅ Fixture generation endpoint
- ✅ Stats endpoint
- ✅ Admin interface integration

---

## 🧪 Testing

### Run Tests

```bash
# All tests
python manage.py test

# Specific app
python manage.py test apps.languages

# With coverage
pytest --cov=apps --cov-report=html

# Integration tests only
pytest apps/languages/tests.py -k Integration
```

### Test Coverage

Includes integration tests for:
- All API endpoints
- Spaced repetition algorithm
- Content generation
- User enrollment
- Swagger documentation
- Rate limiting

---

## 📦 Fixtures & Sample Data

### Load Fixtures

```bash
# Load initial languages and concepts
python manage.py loaddata apps/languages/fixtures/initial_data.json
```

### Generate Fixtures

```bash
# Via API (admin only)
curl -X POST http://localhost:8000/api/v1/languages/generate_fixtures/

# Via Django command
python manage.py dumpdata languages.Language --indent=2 > fixtures/languages.json
```

---

## 🔐 Authentication

### Supabase Auth Integration

Users authenticate with Supabase, admins use Django auth:

```python
# Supabase authentication (for API users)
from apps.users.authentication import SupabaseAuthentication

# Django authentication (for admins)
from django.contrib.auth import authenticate
```

### API Authentication

```bash
# Get token from Supabase
TOKEN="your-supabase-jwt-token"

# Use token in requests
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/concepts/
```

---

## 📊 Django Admin

### Admin Features

- **Languages** - Manage available languages
- **Concepts** - Create and edit learning concepts with inline words
- **Learning Plans** - Build curated learning paths
- **Flashcards, Stories, Quizzes** - Content management
- **AI Jobs** - Monitor content generation queue
- **SRS Cards** - View spaced repetition data
- **Podcast Episodes** - Review generated podcasts

### Access Admin

```
http://localhost:8000/admin
```

---

## 🚢 Deployment

### Docker

```bash
# Build
docker build -t mala-django .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e GEMINI_API_KEY=... \
  mala-django
```

### Kubernetes / ArgoCD

See `../../argocd/README.md` for GitOps deployment with Supabase branch previews.

---

## 🔗 Related Services

- **Bun API** (TypeScript) - Fast REST API (optional alternative)
- **Pipecat Service** (Python) - Real-time audio tutoring
- **Frontend** (React) - Web interface (coming soon)

---

## 📝 Environment Variables

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_ENV=development
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (Supabase)
DATABASE_URL=postgresql://user:pass@host:5432/db
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Redis
REDIS_URL=redis://localhost:6379/0

# AI
GEMINI_API_KEY=your-gemini-api-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b claude/feature-name`
2. Make changes with Django migrations
3. Run tests: `python manage.py test`
4. Commit: `git commit -m "feat: add feature"`
5. Push: `git push origin claude/feature-name`
6. ArgoCD auto-deploys to preview environment

---

## 📚 Documentation

- API Docs: http://localhost:8000/api/docs/
- Swagger Schema: http://localhost:8000/api/schema/
- ReDoc: http://localhost:8000/api/redoc/
- ArgoCD Deployment: `../../argocd/README.md`

---

## 🙏 Credits

- **Django** - Web framework
- **DRF** - REST API framework
- **drf-spectacular** - OpenAPI/Swagger generation
- **Celery** - Task queue
- **smolagents** - AI orchestration (Hugging Face)
- **Google Gemini** - AI content generation
- **Supabase** - Backend as a service
- **Anki** - Spaced repetition algorithm

---

**Built with ❤️ for language learners worldwide**
