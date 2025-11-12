"""Serializers for Learning Plans"""
from rest_framework import serializers
from apps.core.api import BaseModelSerializer
from apps.languages.serializers import LanguageSerializer, ConceptSerializer
from .models import (
    LearningPlan, LearningPlanConcept, UserLearningPlan,
    UserPlanConceptProgress, LearningPlanCollaborator
)


class LearningPlanConceptSerializer(BaseModelSerializer):
    concept = ConceptSerializer(read_only=True)
    concept_id = serializers.UUIDField(write_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = LearningPlanConcept


class LearningPlanSerializer(BaseModelSerializer):
    language = LanguageSerializer(read_only=True)
    language_id = serializers.UUIDField(write_only=True)
    concepts = LearningPlanConceptSerializer(source='plan_concepts', many=True, read_only=True)
    concept_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = LearningPlan

    def get_concept_count(self, obj):
        return obj.plan_concepts.count()


class UserLearningPlanSerializer(BaseModelSerializer):
    learning_plan = LearningPlanSerializer(read_only=True)
    learning_plan_id = serializers.UUIDField(write_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = UserLearningPlan


class UserPlanConceptProgressSerializer(BaseModelSerializer):
    concept = ConceptSerializer(read_only=True)
    concept_id = serializers.UUIDField(write_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = UserPlanConceptProgress


class LearningPlanCollaboratorSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = LearningPlanCollaborator
