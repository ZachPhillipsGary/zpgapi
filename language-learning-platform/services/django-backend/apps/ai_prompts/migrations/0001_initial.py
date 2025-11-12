# Generated migration for AI Prompts app

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AIPromptTemplate',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Human-readable name for the prompt', max_length=200)),
                ('prompt_type', models.CharField(choices=[('story_generation', 'Story Generation'), ('quiz_generation', 'Quiz Generation'), ('flashcard_generation', 'Flashcard Generation'), ('podcast_intro', 'Podcast Introduction'), ('podcast_vocab', 'Podcast Vocabulary'), ('podcast_dialogue', 'Podcast Dialogue'), ('podcast_grammar', 'Podcast Grammar'), ('podcast_story', 'Podcast Story'), ('podcast_quiz', 'Podcast Quiz'), ('podcast_outro', 'Podcast Outro'), ('tutoring_system', 'Tutoring System Prompt'), ('tutoring_context', 'Tutoring Context Prompt'), ('multimodal_analysis', 'Multimodal Analysis Prompt')], max_length=50, unique=True)),
                ('description', models.TextField(blank=True, help_text='Description of what this prompt does')),
                ('available_variables', models.JSONField(default=list, help_text="List of variable names available for this prompt type, e.g., ['concept_title', 'language', 'difficulty']")),
                ('is_active', models.BooleanField(default=True)),
                ('created_by', models.CharField(blank=True, help_text='Creator/author of the prompt template', max_length=100)),
            ],
            options={
                'verbose_name': 'AI Prompt Template',
                'verbose_name_plural': 'AI Prompt Templates',
                'db_table': 'mala_ai_prompt_templates',
                'ordering': ['prompt_type'],
            },
        ),
        migrations.CreateModel(
            name='AIPromptVersion',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version_number', models.PositiveIntegerField(help_text='Version number (auto-incremented)')),
                ('version_name', models.CharField(blank=True, help_text='Optional name for this version, e.g., \'More conversational\', \'Stricter grammar\'', max_length=100)),
                ('prompt_text', models.TextField(help_text='The prompt text with variables like {concept_title}, {language}, etc.')),
                ('is_active', models.BooleanField(default=False, help_text='Is this the currently active version? Only one version should be active per template.')),
                ('is_archived', models.BooleanField(default=False, help_text='Archived versions are hidden from active use')),
                ('usage_count', models.PositiveIntegerField(default=0, help_text='Number of times this version has been used')),
                ('success_rate', models.DecimalField(blank=True, decimal_places=2, help_text='Success rate percentage (0-100)', max_digits=5, null=True)),
                ('avg_generation_time', models.DecimalField(blank=True, decimal_places=2, help_text='Average generation time in seconds', max_digits=8, null=True)),
                ('change_notes', models.TextField(blank=True, help_text='Notes about what changed in this version')),
                ('created_by', models.CharField(blank=True, help_text='Who created this version', max_length=100)),
                ('prompt_template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='ai_prompts.aiprompttemplate')),
            ],
            options={
                'verbose_name': 'AI Prompt Version',
                'verbose_name_plural': 'AI Prompt Versions',
                'db_table': 'mala_ai_prompt_versions',
                'ordering': ['prompt_template', '-version_number'],
                'unique_together': {('prompt_template', 'version_number')},
            },
        ),
        migrations.CreateModel(
            name='AIPromptUsageLog',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.UUIDField(blank=True, help_text='User who triggered this prompt', null=True)),
                ('context_data', models.JSONField(default=dict, help_text='The variables used to render the prompt')),
                ('rendered_prompt', models.TextField(help_text='The final rendered prompt sent to AI')),
                ('success', models.BooleanField(help_text='Was the generation successful?')),
                ('generation_time', models.DecimalField(decimal_places=2, help_text='Time taken to generate in seconds', max_digits=8)),
                ('ai_model', models.CharField(blank=True, help_text="AI model used, e.g., 'gemini-2.0-flash'", max_length=100)),
                ('token_count', models.PositiveIntegerField(blank=True, help_text='Number of tokens used', null=True)),
                ('error_message', models.TextField(blank=True, help_text='Error message if generation failed')),
                ('prompt_version', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='usage_logs', to='ai_prompts.aipromptversion')),
            ],
            options={
                'verbose_name': 'AI Prompt Usage Log',
                'verbose_name_plural': 'AI Prompt Usage Logs',
                'db_table': 'mala_ai_prompt_usage_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AIPromptAssignment',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.UUIDField(help_text='Supabase user ID')),
                ('is_active', models.BooleanField(default=True)),
                ('test_group_name', models.CharField(blank=True, help_text="Name of the A/B test group, e.g., 'control', 'variant_a'", max_length=100)),
                ('notes', models.TextField(blank=True, help_text='Notes about this assignment')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_by', models.CharField(blank=True, help_text='Who created this assignment', max_length=100)),
                ('prompt_template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='ai_prompts.aiprompttemplate')),
                ('prompt_version', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='ai_prompts.aipromptversion')),
            ],
            options={
                'verbose_name': 'AI Prompt Assignment',
                'verbose_name_plural': 'AI Prompt Assignments',
                'db_table': 'mala_ai_prompt_assignments',
                'ordering': ['-created_at'],
                'unique_together': {('prompt_template', 'user_id')},
            },
        ),
        migrations.AddIndex(
            model_name='aipromptversion',
            index=models.Index(fields=['prompt_template', 'is_active'], name='mala_ai_pro_prompt__a8e8e1_idx'),
        ),
        migrations.AddIndex(
            model_name='aipromptversion',
            index=models.Index(fields=['is_active', 'is_archived'], name='mala_ai_pro_is_acti_8d8a0d_idx'),
        ),
        migrations.AddIndex(
            model_name='aipromptusagelog',
            index=models.Index(fields=['prompt_version', 'created_at'], name='mala_ai_pro_prompt__9c3e8a_idx'),
        ),
        migrations.AddIndex(
            model_name='aipromptusagelog',
            index=models.Index(fields=['user_id', 'created_at'], name='mala_ai_pro_user_id_7d2e1a_idx'),
        ),
        migrations.AddIndex(
            model_name='aipromptusagelog',
            index=models.Index(fields=['success', 'created_at'], name='mala_ai_pro_success_6c4f2b_idx'),
        ),
        migrations.AddIndex(
            model_name='aipromptassignment',
            index=models.Index(fields=['user_id', 'is_active'], name='mala_ai_pro_user_id_5e3d9c_idx'),
        ),
        migrations.AddIndex(
            model_name='aipromptassignment',
            index=models.Index(fields=['prompt_template', 'user_id'], name='mala_ai_pro_prompt__1f7a4b_idx'),
        ),
    ]
