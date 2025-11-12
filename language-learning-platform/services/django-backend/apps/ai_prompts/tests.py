"""
Integration Tests for AI Prompt Management System
"""

import uuid
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import (
    AIPromptTemplate,
    AIPromptVersion,
    AIPromptAssignment,
    AIPromptUsageLog
)
from .services import get_prompt_service, PromptContext


class AIPromptTemplateModelTest(TestCase):
    """Test AIPromptTemplate model"""

    def setUp(self):
        self.template = AIPromptTemplate.objects.create(
            name="Test Story Generation",
            prompt_type="story_generation",
            description="Test template for stories",
            available_variables=["concept_title", "language_name", "difficulty"],
            is_active=True,
            created_by="test"
        )

    def test_template_creation(self):
        """Test that template is created correctly"""
        self.assertEqual(self.template.name, "Test Story Generation")
        self.assertEqual(self.template.prompt_type, "story_generation")
        self.assertTrue(self.template.is_active)
        self.assertEqual(len(self.template.available_variables), 3)

    def test_template_str(self):
        """Test string representation"""
        expected = "Test Story Generation (Story Generation)"
        self.assertEqual(str(self.template), expected)

    def test_get_active_version_none(self):
        """Test getting active version when none exists"""
        version = self.template.get_active_version()
        self.assertIsNone(version)

    def test_get_active_version(self):
        """Test getting active version"""
        active_version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            version_name="Test Version",
            prompt_text="Test prompt with {concept_title}",
            is_active=True
        )

        version = self.template.get_active_version()
        self.assertEqual(version.id, active_version.id)


class AIPromptVersionModelTest(TestCase):
    """Test AIPromptVersion model"""

    def setUp(self):
        self.template = AIPromptTemplate.objects.create(
            name="Test Template",
            prompt_type="story_generation",
            is_active=True
        )

    def test_version_auto_increment(self):
        """Test that version numbers auto-increment"""
        v1 = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Version 1"
        )
        v2 = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Version 2"
        )

        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v2.version_number, 2)

    def test_only_one_active_version(self):
        """Test that only one version can be active per template"""
        v1 = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Version 1",
            is_active=True
        )
        v2 = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Version 2",
            is_active=True
        )

        # Refresh v1 from database
        v1.refresh_from_db()

        # v1 should be deactivated
        self.assertFalse(v1.is_active)
        self.assertTrue(v2.is_active)

    def test_increment_usage(self):
        """Test incrementing usage count"""
        version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Test"
        )

        self.assertEqual(version.usage_count, 0)

        version.increment_usage()
        self.assertEqual(version.usage_count, 1)

        version.increment_usage()
        self.assertEqual(version.usage_count, 2)

    def test_update_metrics(self):
        """Test updating performance metrics"""
        version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Test"
        )

        # First success
        version.update_metrics(success=True, generation_time=1.5)
        self.assertEqual(version.usage_count, 1)
        self.assertEqual(version.success_rate, Decimal('100.00'))
        self.assertEqual(version.avg_generation_time, Decimal('1.50'))

        # One failure
        version.update_metrics(success=False, generation_time=2.0)
        self.assertEqual(version.usage_count, 2)
        self.assertEqual(version.success_rate, Decimal('50.00'))
        self.assertAlmostEqual(float(version.avg_generation_time), 1.75, places=2)


class AIPromptServiceTest(TestCase):
    """Test AIPromptService"""

    def setUp(self):
        self.service = get_prompt_service()

        # Create template and version
        self.template = AIPromptTemplate.objects.create(
            name="Test Template",
            prompt_type="story_generation",
            available_variables=["concept_title", "language_name"],
            is_active=True
        )

        self.version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Create a story about {concept_title} in {language_name}",
            is_active=True
        )

    def test_get_prompt_template(self):
        """Test getting prompt template by type"""
        template = self.service.get_prompt_template('story_generation')
        self.assertEqual(template.id, self.template.id)

    def test_get_prompt_version_default(self):
        """Test getting default active version"""
        version = self.service.get_prompt_version('story_generation')
        self.assertEqual(version.id, self.version.id)

    def test_get_prompt_version_user_assigned(self):
        """Test getting user-assigned version"""
        user_id = uuid.uuid4()

        # Create alternative version
        alt_version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Alternative prompt",
            is_active=False
        )

        # Assign to user
        AIPromptAssignment.objects.create(
            prompt_template=self.template,
            prompt_version=alt_version,
            user_id=user_id,
            is_active=True
        )

        # Should get assigned version
        version = self.service.get_prompt_version('story_generation', str(user_id))
        self.assertEqual(version.id, alt_version.id)

    def test_render_prompt(self):
        """Test rendering prompt with variables"""
        context = {
            'concept_title': 'Greetings',
            'language_name': 'French'
        }

        rendered = self.service.render_prompt(self.version, context)
        self.assertEqual(rendered, "Create a story about Greetings in French")

    def test_render_prompt_missing_variable(self):
        """Test rendering with missing variable raises error"""
        context = {
            'concept_title': 'Greetings'
            # Missing language_name
        }

        with self.assertRaises(ValueError):
            self.service.render_prompt(self.version, context)

    def test_get_and_render_prompt(self):
        """Test combined get and render"""
        context = {
            'concept_title': 'Greetings',
            'language_name': 'French'
        }

        rendered = self.service.get_and_render_prompt('story_generation', context)
        self.assertEqual(rendered, "Create a story about Greetings in French")

    def test_log_usage(self):
        """Test logging prompt usage"""
        context = {'concept_title': 'Test'}
        rendered = "Rendered prompt"

        self.service.log_usage(
            prompt_version=self.version,
            rendered_prompt=rendered,
            context=context,
            success=True,
            generation_time=1.23,
            user_id=uuid.uuid4(),
            ai_model='gemini-2.0-flash',
            token_count=100
        )

        # Check log was created
        logs = AIPromptUsageLog.objects.filter(prompt_version=self.version)
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertTrue(log.success)
        self.assertEqual(log.generation_time, Decimal('1.23'))
        self.assertEqual(log.ai_model, 'gemini-2.0-flash')
        self.assertEqual(log.token_count, 100)

        # Check version metrics were updated
        self.version.refresh_from_db()
        self.assertEqual(self.version.usage_count, 1)


class PromptContextTest(TestCase):
    """Test PromptContext manager"""

    def setUp(self):
        self.template = AIPromptTemplate.objects.create(
            name="Test Template",
            prompt_type="story_generation",
            available_variables=["concept_title"],
            is_active=True
        )

        self.version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Story about {concept_title}",
            is_active=True
        )

    def test_context_manager_success(self):
        """Test successful usage with context manager"""
        user_id = str(uuid.uuid4())

        with PromptContext('story_generation', user_id=user_id, ai_model='gemini') as ctx:
            prompt = ctx.get_prompt({'concept_title': 'Test'})
            self.assertEqual(prompt, "Story about Test")
            ctx.mark_success(token_count=50)

        # Check log was created
        logs = AIPromptUsageLog.objects.all()
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertTrue(log.success)
        self.assertEqual(log.token_count, 50)
        self.assertEqual(log.ai_model, 'gemini')

    def test_context_manager_failure(self):
        """Test failure handling with context manager"""
        user_id = str(uuid.uuid4())

        with PromptContext('story_generation', user_id=user_id) as ctx:
            prompt = ctx.get_prompt({'concept_title': 'Test'})
            ctx.mark_failure("Test error")

        # Check log was created with failure
        logs = AIPromptUsageLog.objects.all()
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertFalse(log.success)
        self.assertEqual(log.error_message, "Test error")


class AIPromptTemplateAPITest(APITestCase):
    """Test AIPromptTemplate API endpoints"""

    def setUp(self):
        self.template = AIPromptTemplate.objects.create(
            name="Test Template",
            prompt_type="story_generation",
            is_active=True
        )

        self.version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Test prompt",
            is_active=True
        )

    def test_list_templates(self):
        """Test listing all templates"""
        url = reverse('ai-prompt-template-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Template')

    def test_get_template_detail(self):
        """Test getting template detail"""
        url = reverse('ai-prompt-template-detail', args=[self.template.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Template')
        self.assertIsNotNone(response.data['active_version'])

    def test_get_template_by_type(self):
        """Test getting template by type"""
        url = reverse('ai-prompt-template-by-type', args=['story_generation'])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['prompt_type'], 'story_generation')

    def test_create_template(self):
        """Test creating new template"""
        url = reverse('ai-prompt-template-list')
        data = {
            'name': 'New Template',
            'prompt_type': 'quiz_generation',
            'description': 'Test quiz template',
            'available_variables': ['concept_title', 'question_count'],
            'is_active': True
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Template')


class AIPromptVersionAPITest(APITestCase):
    """Test AIPromptVersion API endpoints"""

    def setUp(self):
        self.template = AIPromptTemplate.objects.create(
            name="Test Template",
            prompt_type="story_generation",
            is_active=True
        )

        self.version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Test prompt",
            is_active=False
        )

    def test_activate_version(self):
        """Test activating a version"""
        url = reverse('ai-prompt-version-activate', args=[self.version.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_active'])

        # Verify in database
        self.version.refresh_from_db()
        self.assertTrue(self.version.is_active)

    def test_clone_version(self):
        """Test cloning a version"""
        url = reverse('ai-prompt-version-clone', args=[self.version.id])
        data = {
            'version_name': 'Cloned Version',
            'change_notes': 'Cloned for testing'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['version_name'], 'Cloned Version')
        self.assertEqual(response.data['version_number'], 2)


class AIPromptAssignmentAPITest(APITestCase):
    """Test AIPromptAssignment API endpoints"""

    def setUp(self):
        self.template = AIPromptTemplate.objects.create(
            name="Test Template",
            prompt_type="story_generation",
            is_active=True
        )

        self.version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Test prompt",
            is_active=True
        )

        self.user_id = uuid.uuid4()

    def test_create_assignment(self):
        """Test creating user assignment"""
        url = reverse('ai-prompt-assignment-list')
        data = {
            'prompt_template': str(self.template.id),
            'prompt_version': str(self.version.id),
            'user_id': str(self.user_id),
            'test_group_name': 'control',
            'is_active': True
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['test_group_name'], 'control')

    def test_get_assignments_for_user(self):
        """Test getting assignments for a specific user"""
        # Create assignment
        AIPromptAssignment.objects.create(
            prompt_template=self.template,
            prompt_version=self.version,
            user_id=self.user_id,
            test_group_name='variant_a',
            is_active=True
        )

        url = reverse('ai-prompt-assignment-for-user', args=[str(self.user_id)])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['test_group_name'], 'variant_a')


class AIPromptUsageLogAPITest(APITestCase):
    """Test AIPromptUsageLog API endpoints"""

    def setUp(self):
        self.template = AIPromptTemplate.objects.create(
            name="Test Template",
            prompt_type="story_generation",
            is_active=True
        )

        self.version = AIPromptVersion.objects.create(
            prompt_template=self.template,
            prompt_text="Test prompt",
            is_active=True
        )

        # Create some usage logs
        for i in range(5):
            AIPromptUsageLog.objects.create(
                prompt_version=self.version,
                rendered_prompt=f"Rendered {i}",
                context_data={'test': i},
                success=i % 2 == 0,  # 3 successes, 2 failures
                generation_time=Decimal('1.5'),
                ai_model='gemini-2.0-flash'
            )

    def test_get_usage_stats(self):
        """Test getting usage statistics"""
        url = reverse('ai-prompt-usage-log-stats')
        response = self.client.get(url, {'days': 7})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_uses'], 5)
        self.assertEqual(response.data['successful_uses'], 3)
        self.assertEqual(response.data['failed_uses'], 2)
        self.assertEqual(response.data['success_rate'], 60.0)
