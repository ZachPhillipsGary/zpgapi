# 🌍 Language Learning Platform with AI Tutoring

A comprehensive language learning platform featuring real-time AI tutoring, spaced repetition, and personalized content generation.

## 🎯 Features

### Core Learning Features
- **🗣️ Real-time AI Tutoring** - Live audio tutoring sessions using Pipecat + Google Gemini 2.0 Flash
- **📚 Learning Plans** - Curated learning paths shared among users (many-to-many)
- **🃏 Spaced Repetition** - Anki-based SRS algorithm for optimal retention
- **📖 AI-Generated Content** - Personalized stories, quizzes, and flashcards
- **🎯 Concept-Based Learning** - Organized by phrases, grammar points, and vocabulary
- **📊 Progress Tracking** - Detailed analytics and mastery levels

### Supported Languages
- 🇬🇧 English
- 🇫🇷 French (Français)
- 🇹🇼 Mandarin Traditional (中文繁體)

### Technical Features
- **Multimodal AI** - Gemini 2.0 Flash Nano + Veo3 for image/video analysis
- **Authentication** - Supabase Auth for users, Django Admin for content management
- **Real-time Communication** - WebSocket/WebRTC for audio streaming
- **Background Jobs** - Celery with daily crons for content generation
- **Microservices Architecture** - Scalable service-oriented design

---

## 🏗️ Architecture

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   React Web     │◄─────►│   Bun API        │◄─────►│   Supabase DB   │
│  (TypeScript)   │       │  (TypeScript)    │       │  (PostgreSQL)   │
└─────────────────┘       └──────────────────┘       └─────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  Django Backend  │
                          │ (Admin + Tasks)  │
                          └──────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
          ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
          │   Pipecat   │  │  AI Worker   │  │    Redis     │
          │   Service   │  │   (Gemini)   │  │   (Cache)    │
          └─────────────┘  └──────────────┘  └──────────────┘
```

### Services

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| **Bun API** | TypeScript + Hono | 3001 | Fast REST API for content delivery |
| **Django Backend** | Python + Django | 8000 | Admin interface + content management |
| **Pipecat Service** | Python + Pipecat | 8001 | Real-time audio tutoring |
| **AI Worker** | Python + Celery | - | Background content generation |
| **PostgreSQL** | Supabase | 5432 | Main database |
| **Redis** | Redis | 6379 | Cache + job queue |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Supabase account
- Google Gemini API key
- (Optional) Daily.co account for WebRTC

### 1. Clone and Setup

```bash
cd language-learning-platform
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Initialize Database

```bash
# Apply Supabase migrations
psql $DATABASE_URL < supabase/migrations/20250112_initial_schema.sql
psql $DATABASE_URL < supabase/migrations/20250112_learning_plans.sql

# Or use Supabase CLI
supabase db push
```

### 4. Access Services

- **Bun API**: http://localhost:3001
- **Django Admin**: http://localhost:8000/admin
- **Pipecat Service**: http://localhost:8001
- **API Docs**: http://localhost:8000/api/docs

---

## 📦 Database Schema

### Core Tables

#### Languages
```sql
- id, name, code (ISO 639-1), native_name
- user_languages (many-to-many with users)
```

#### Concepts
```sql
- id, language_id, title, description, type
- concept_type: phrase | grammar | vocabulary | idiom
- difficulty_level (1-10)
```

#### Words
```sql
- id, concept_id, word, translation, pronunciation
- example_sentence, audio_url, image_url
```

#### Learning Plans 🆕
```sql
- id, language_id, title, description
- learning_plan_concepts (many-to-many with concepts)
- user_learning_plans (many-to-many with users)
- Ordered concept sequences with progress tracking
```

#### Spaced Repetition
```sql
- spaced_repetition_cards (Anki algorithm)
- ease_factor, interval_days, repetitions, lapses
- card_state: new | learning | review | relearning
```

#### Content
```sql
- flashcards, stories, quizzes
- AI-generated flag
- Associated with concepts
```

---

## 🎓 Learning Plans

Learning plans allow creating curated learning paths that can be shared among users.

### Creating a Learning Plan (Admin)

```typescript
POST /api/v1/learning-plans
{
  "language_id": "uuid",
  "title": "French for Beginners",
  "description": "Complete beginner course",
  "difficulty_level": 1,
  "estimated_hours": 40,
  "category": "beginner_course",
  "is_public": true
}
```

### Adding Concepts to Plan

```typescript
POST /api/v1/learning-plans/{id}/concepts
{
  "concepts": [
    { "concept_id": "uuid", "sequence_order": 1, "is_required": true },
    { "concept_id": "uuid", "sequence_order": 2, "is_required": true }
  ]
}
```

### User Enrollment

```typescript
POST /api/v1/learning-plans/{id}/enroll
{
  "user_id": "uuid"
}
```

---

## 🤖 AI Features

### Real-time Tutoring

```typescript
// Connect to tutoring session
const ws = new WebSocket('ws://localhost:8001/ws/tutoring/{session_id}');

// Send audio
ws.send(audioBuffer);

// Receive transcription + AI response
ws.onmessage = (event) => {
  const { type, user, assistant } = JSON.parse(event.data);
  // type: 'transcription' | 'text' | 'audio'
};
```

### Content Generation

The AI worker runs daily cron jobs to generate:
- **Stories**: Contextual stories using concepts
- **Quizzes**: Multiple choice, fill-in-blank, translation
- **Flashcards**: Front/back with hints and examples

On-demand generation also available via API.

### Multimodal Analysis (Veo3)

```python
# Analyze images/videos for language learning
result = await gemini.analyze_image_or_video(
    media_data=image_bytes,
    media_type="image",
    prompt="Describe this scene in French",
    language_code="fr"
)
```

---

## 📖 API Documentation

### Bun API Endpoints

#### Languages
- `GET /api/v1/languages` - List all languages
- `GET /api/v1/languages/:id` - Get language details
- `GET /api/v1/languages/user/:userId` - User's enrolled languages
- `POST /api/v1/languages/user/:userId/enroll` - Enroll in language

#### Learning Plans
- `GET /api/v1/learning-plans/language/:languageId` - Plans for language
- `GET /api/v1/learning-plans/:id` - Plan details with concepts
- `POST /api/v1/learning-plans/:id/enroll` - Enroll user
- `GET /api/v1/learning-plans/user/:userId/enrolled` - User's plans
- `PATCH /api/v1/learning-plans/:id/progress` - Update progress

#### Spaced Repetition
- `GET /api/v1/spaced-repetition/due/:userId` - Cards due for review
- `POST /api/v1/spaced-repetition/review` - Submit card review
- `GET /api/v1/spaced-repetition/stats/:userId` - Review statistics

#### Concepts
- `GET /api/v1/concepts?language_id={id}` - Concepts by language
- `GET /api/v1/concepts/:id` - Concept with words

---

## 🧪 Development

### Dev Container Setup

```bash
# Open in VS Code with Dev Containers extension
code language-learning-platform

# Or use devcontainer CLI
devcontainer open .
```

### Local Development without Docker

#### Django Backend
```bash
cd services/django-backend
uv pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Bun API
```bash
cd services/bun-api
bun install
bun run dev
```

#### Pipecat Service
```bash
cd services/pipecat-service
uv pip install -r requirements.txt
uvicorn main:app --reload
```

---

## ☸️ Kubernetes Deployment

### K3s Setup

```bash
# Apply manifests
kubectl apply -k k8s/overlays/dev

# Check status
kubectl get pods -n language-learning

# View logs
kubectl logs -f deployment/pipecat-service -n language-learning
```

### Production Deployment

```bash
kubectl apply -k k8s/overlays/prod
```

---

## 🔧 Configuration

### Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `DAILY_API_KEY` (optional, for WebRTC)

---

## 📊 Spaced Repetition Algorithm

Uses the Anki variant of SuperMemo SM-2:

### Rating Scale
- **1 (Again)**: Complete blackout, card failed
- **2 (Hard)**: Correct but difficult
- **3 (Good)**: Correct with some hesitation
- **4 (Easy)**: Perfect response

### Card States
- **New**: Never seen before
- **Learning**: In initial learning phase (1min → 10min steps)
- **Review**: Graduated to spaced repetition
- **Relearning**: Failed review, relearning

### Key Parameters
- Starting ease factor: 2.5
- Graduating interval: 1 day
- Easy interval: 4 days
- Lapse interval: 50% of previous

---

## 🎨 Frontend (Coming Soon)

React TypeScript web app with:
- Material UI / Tailwind CSS
- Real-time audio recording
- Flashcard review interface
- Progress dashboards
- Learning plan browser

React Native mobile app for iOS/Android.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📝 License

MIT License - see LICENSE file

---

## 🙏 Acknowledgments

- **Pipecat** - Real-time voice conversation framework
- **Google Gemini** - Multimodal AI capabilities
- **Supabase** - Backend as a service
- **Bun** - Fast JavaScript runtime
- **Anki** - Spaced repetition algorithm inspiration

---

## 📮 Support

For issues and questions:
- GitHub Issues: [link]
- Documentation: [link]
- Discord Community: [link]

---

## 🗺️ Roadmap

- [ ] React web frontend
- [ ] React Native mobile app
- [ ] Video generation with Veo3
- [ ] Community-created learning plans
- [ ] Gamification (streaks, badges, leaderboards)
- [ ] AI conversation partners
- [ ] Pronunciation analysis with visual feedback
- [ ] More languages (Spanish, German, Japanese, Korean)
- [ ] Offline mode
- [ ] Integration with language learning APIs (Forvo, Tatoeba)

---

**Built with ❤️ for language learners worldwide**
