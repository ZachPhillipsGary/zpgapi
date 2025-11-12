# AI Prompt Management System

Complete prompt versioning and A/B testing system for all AI-generated content in the MALA Language Learning Platform.

## 🎯 Features

- **Database-Stored Prompts**: All AI prompts are stored in the database for easy modification
- **Version Control**: Track changes to prompts over time with version history
- **A/B Testing**: Assign different prompt versions to specific users for testing
- **Analytics**: Track prompt usage, success rates, and generation times
- **Admin Interface**: Beautiful Django admin UI for managing prompts
- **REST API**: Full API access to all prompt management features
- **Automatic Logging**: All prompt usage is automatically tracked

## 📊 Database Schema

### Core Tables

#### `mala_ai_prompt_templates`
Stores the different types of AI prompts in the system.

```sql
- id (UUID)
- name (e.g., "Story Generation")
- prompt_type (e.g., "story_generation")
- description
- available_variables (JSON array of variable names)
- is_active
- created_by
```

#### `mala_ai_prompt_versions`
Stores different versions of each prompt template.

```sql
- id (UUID)
- prompt_template_id
- version_number (auto-incremented)
- version_name (e.g., "More conversational")
- prompt_text (the actual prompt with {variables})
- is_active (only one active version per template)
- is_archived
- usage_count (how many times used)
- success_rate (percentage)
- avg_generation_time (in seconds)
- change_notes
```

#### `mala_ai_prompt_assignments`
Assigns specific prompt versions to users for A/B testing.

```sql
- id (UUID)
- prompt_template_id
- prompt_version_id
- user_id (Supabase user UUID)
- is_active
- test_group_name (e.g., "control", "variant_a")
- notes
```

#### `mala_ai_prompt_usage_logs`
Logs every prompt usage for analytics.

```sql
- id (UUID)
- prompt_version_id
- user_id
- context_data (JSON with variables used)
- rendered_prompt (final prompt sent to AI)
- success (boolean)
- generation_time (seconds)
- ai_model (e.g., "gemini-2.0-flash")
- token_count
- error_message (if failed)
```

## 🔧 Usage

### Python Service Usage

```python
from apps.ai_prompts.services import PromptContext

# Option 1: Context manager (recommended - auto-tracks usage)
with PromptContext('story_generation', user_id='user-uuid', ai_model='gemini-2.0-flash') as ctx:
    prompt = ctx.get_prompt({
        'concept_title': 'Basic Greetings',
        'concept_description': 'Essential French greetings',
        'language_name': 'French',
        'difficulty': 1
    })

    # Generate content using the prompt
    result = generate_with_gemini(prompt)

    # Mark as successful (with optional token count)
    ctx.mark_success(token_count=150)


# Option 2: Manual service usage
from apps.ai_prompts.services import get_prompt_service

service = get_prompt_service()

# Get prompt for a user (checks assignments, falls back to active version)
version = service.get_prompt_version('story_generation', user_id='user-uuid')

# Render prompt with variables
rendered = service.render_prompt(version, {
    'concept_title': 'Basic Greetings',
    'language_name': 'French'
})

# Log usage
service.log_usage(
    prompt_version=version,
    rendered_prompt=rendered,
    context={'concept_title': 'Basic Greetings'},
    success=True,
    generation_time=1.23,
    user_id='user-uuid',
    ai_model='gemini-2.0-flash',
    token_count=150
)
```

### API Usage

#### Get All Prompt Templates
```bash
GET /api/v1/ai-prompts/templates/
```

#### Get Template by Type
```bash
GET /api/v1/ai-prompts/templates/by_type/story_generation/
```

#### Get Analytics for a Template
```bash
GET /api/v1/ai-prompts/templates/{id}/analytics/
```

#### Create New Prompt Version
```bash
POST /api/v1/ai-prompts/versions/
{
  "prompt_template": "uuid",
  "version_name": "More conversational",
  "prompt_text": "Create a story about {concept_title}...",
  "change_notes": "Made the tone more friendly"
}
```

#### Activate a Version
```bash
POST /api/v1/ai-prompts/versions/{id}/activate/
```

#### Clone a Version
```bash
POST /api/v1/ai-prompts/versions/{id}/clone/
{
  "version_name": "Experimental variant",
  "change_notes": "Testing shorter prompts"
}
```

#### Assign Version to User (A/B Testing)
```bash
POST /api/v1/ai-prompts/assignments/
{
  "prompt_template": "uuid",
  "prompt_version": "uuid",
  "user_id": "user-uuid",
  "test_group_name": "variant_a",
  "notes": "Testing new story format"
}
```

#### Get User's Assignments
```bash
GET /api/v1/ai-prompts/assignments/for_user/{user_id}/
```

#### Get Usage Statistics
```bash
GET /api/v1/ai-prompts/usage-logs/stats/?days=7&prompt_type=story_generation
```

## 🎨 Django Admin

Access the admin interface at: `http://localhost:8000/admin`

### Features:
- **Prompt Templates**: View all prompt types with active versions
- **Prompt Versions**: Edit prompts with syntax highlighting for variables
- **Inline Version Editing**: Edit versions directly from template page
- **A/B Test Management**: Assign users to specific prompt versions
- **Usage Analytics**: View performance metrics for each version
- **Bulk Actions**: Activate, archive, or clone multiple versions at once
- **Color-Coded Badges**: Visual indicators for status, success rates, etc.

## 📦 Initial Setup

### 1. Run Migrations
```bash
python manage.py makemigrations ai_prompts
python manage.py migrate
```

### 2. Load Initial Prompts
```bash
python manage.py loaddata apps/ai_prompts/fixtures/initial_prompts.json
```

This will create 13 prompt templates with their initial versions:
- Story Generation
- Quiz Generation
- Flashcard Generation
- Podcast segments (Intro, Vocab, Dialogue, Grammar, Story, Quiz, Outro)
- Tutoring prompts (System, Context)
- Multimodal Analysis

### 3. Verify in Admin
Go to http://localhost:8000/admin/ai_prompts/ and verify all templates are loaded.

## 🔄 Migration Guide

### Refactoring Existing Code

Before (hardcoded prompt):
```python
def generate_story(concept):
    prompt = f"Create a story about {concept.title}..."
    result = gemini.generate_content(prompt)
    return result
```

After (using prompt service):
```python
def generate_story(concept, user_id=None):
    from apps.ai_prompts.services import PromptContext

    with PromptContext('story_generation', user_id=user_id, ai_model='gemini-2.0-flash') as ctx:
        prompt = ctx.get_prompt({
            'concept_title': concept.title,
            'concept_description': concept.description,
            'language_name': concept.language.name,
            'difficulty': concept.difficulty_level
        })

        result = gemini.generate_content(prompt)
        ctx.mark_success(token_count=result.usage_metadata.total_tokens)

        return result
```

## 📈 Analytics Examples

### Success Rate by Prompt Type
```python
from apps.ai_prompts.services import get_prompt_service

service = get_prompt_service()
analytics = service.get_prompt_analytics('story_generation')

print(f"Active version: v{analytics['template']['active_version']}")
for version in analytics['versions']:
    print(f"v{version['version_number']}: {version['success_rate']}% success, {version['usage_count']} uses")
```

### A/B Test Results
```python
from apps.ai_prompts.models import AIPromptUsageLog
from django.db.models import Avg, Count, Q

# Compare two versions
logs = AIPromptUsageLog.objects.filter(
    prompt_version__prompt_template__prompt_type='story_generation'
)

results = logs.values('prompt_version__version_number').annotate(
    total_uses=Count('id'),
    success_count=Count('id', filter=Q(success=True)),
    avg_time=Avg('generation_time')
)

for result in results:
    success_rate = (result['success_count'] / result['total_uses']) * 100
    print(f"v{result['prompt_version__version_number']}: {success_rate:.1f}% success, {result['avg_time']:.2f}s avg")
```

## 🔬 A/B Testing Workflow

### 1. Create Experimental Version
1. Go to Admin → AI Prompt Versions
2. Find the current active version for a prompt type
3. Use the "Clone selected versions" action to duplicate it
4. Edit the cloned version with your experiment
5. Save (but don't activate yet)

### 2. Assign to Test Users
1. Go to Admin → AI Prompt Assignments
2. Add assignment for each test user:
   - Select the prompt template
   - Select your experimental version
   - Enter user UUID
   - Set test group name (e.g., "variant_a")
3. Save

### 3. Monitor Results
```bash
GET /api/v1/ai-prompts/usage-logs/stats/?days=7&prompt_type=story_generation
```

### 4. Promote Winner
1. Go to Admin → AI Prompt Versions
2. Find the winning version
3. Click "Activate" or use the bulk action
4. Deactivate the old version (happens automatically)

## 🛠️ Prompt Types

Current prompt types in the system:

| Type | Description | Variables |
|------|-------------|-----------|
| `story_generation` | Generate educational stories | `concept_title`, `concept_description`, `language_name`, `difficulty` |
| `quiz_generation` | Generate quizzes | `concept_title`, `concept_description`, `language_name`, `question_count` |
| `flashcard_generation` | Generate flashcards | `concept_title`, `words_text`, `count` |
| `podcast_intro` | Podcast introduction | `segment_type`, `concept_title`, `difficulty`, `words` |
| `podcast_vocab` | Podcast vocabulary segment | `segment_type`, `concept_title`, `difficulty`, `words` |
| `podcast_dialogue` | Podcast dialogue segment | `segment_type`, `concept_title`, `difficulty`, `words` |
| `podcast_grammar` | Podcast grammar segment | `segment_type`, `concept_title`, `difficulty`, `words` |
| `podcast_story` | Podcast story segment | `segment_type`, `concept_title`, `difficulty`, `words` |
| `podcast_quiz` | Podcast quiz segment | `segment_type`, `concept_title`, `difficulty`, `words` |
| `podcast_outro` | Podcast outro | `segment_type`, `concept_title`, `difficulty`, `words` |
| `tutoring_system` | Base tutoring system prompt | `language_name`, `session_type`, `concept_title` |
| `tutoring_context` | Tutoring context additions | `focus_area`, `concept_title`, `concept_description` |
| `multimodal_analysis` | Image/video analysis | `language_code`, `analysis_prompt` |

## 🚀 Next Steps

### Immediate Tasks
1. ✅ Created models and admin interfaces
2. ✅ Created prompt service utility
3. ✅ Created fixtures with initial prompts
4. ⏳ Refactor gemini_service.py to use prompt service
5. ⏳ Refactor podcast_tasks.py to use prompt service
6. ⏳ Refactor tutoring_session.py to use prompt service
7. ⏳ Add integration tests
8. ⏳ Create migration files
9. ⏳ Update documentation

### Future Enhancements
- Prompt performance dashboard in admin
- Automated A/B test analysis
- Prompt suggestion system based on analytics
- Multi-language prompt variants
- Prompt caching optimization
- Export/import prompt templates

## 📚 References

- Django Admin: http://localhost:8000/admin/ai_prompts/
- API Docs: http://localhost:8000/api/docs/
- Models: `apps/ai_prompts/models.py`
- Service: `apps/ai_prompts/services.py`
- Admin: `apps/ai_prompts/admin.py`
- Views: `apps/ai_prompts/views.py`
