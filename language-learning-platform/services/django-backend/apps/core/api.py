"""
Reusable API Framework with Auto-Generated Swagger Documentation

This module provides base classes for creating REST APIs with:
- Automatic CRUD operations
- Swagger/OpenAPI documentation
- Django Admin integration
- Supabase Auth support
- Fixture generation
"""
from rest_framework import viewsets, serializers, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib import admin
from django.core.management import call_command
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import io


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Base serializer with common functionality.
    Automatically includes all fields and handles timestamps.
    """

    class Meta:
        abstract = True
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet with automatic CRUD operations and Swagger docs.

    Usage:
        class LanguageViewSet(BaseModelViewSet):
            model = Language
            filterset_fields = ['code', 'is_active']
            search_fields = ['name', 'native_name']
            ordering_fields = ['name', 'created_at']
    """

    # Override these in subclasses
    model = None
    filterset_fields = []
    search_fields = []
    ordering_fields = ['created_at']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Auto-generate serializer if not provided
        if not hasattr(self, 'serializer_class') and self.model:
            self.serializer_class = self._create_serializer_class()

    def _create_serializer_class(self):
        """Automatically create a serializer for the model"""
        meta_class = type('Meta', (), {
            'model': self.model,
            'fields': '__all__',
            'read_only_fields': ('id', 'created_at', 'updated_at'),
        })

        return type(
            f'{self.model.__name__}Serializer',
            (BaseModelSerializer,),
            {'Meta': meta_class}
        )

    def get_queryset(self):
        """Get the queryset for this view"""
        if self.model is None:
            raise NotImplementedError("model must be defined")
        return self.model.objects.all()

    @extend_schema(
        description="Generate fixtures for this model",
        responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def generate_fixtures(self, request):
        """
        Generate Django fixtures for this model.
        Only accessible to admin users.
        """
        output = io.StringIO()
        call_command(
            'dumpdata',
            self.model._meta.app_label + '.' + self.model.__name__,
            format='json',
            indent=2,
            stdout=output
        )

        fixture_data = output.getvalue()

        # Save to file
        filename = f"{self.model._meta.db_table}_fixture.json"
        fixture_path = f"apps/{self.model._meta.app_label}/fixtures/{filename}"

        with open(fixture_path, 'w') as f:
            f.write(fixture_data)

        return Response({
            'message': f'Fixtures generated successfully',
            'file': fixture_path,
            'count': self.get_queryset().count()
        })

    @extend_schema(
        description="Get statistics for this model",
        responses={200: {'type': 'object'}}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics for this model"""
        queryset = self.get_queryset()
        return Response({
            'total_count': queryset.count(),
            'model_name': self.model.__name__,
        })


class BaseModelAdmin(admin.ModelAdmin):
    """
    Base admin class with common functionality.

    Usage:
        @admin.register(Language)
        class LanguageAdmin(BaseModelAdmin):
            list_display_fields = ['name', 'code', 'is_active']
            search_fields = ['name', 'code']
    """

    list_display_fields = []
    search_fields = []
    list_filter_fields = []
    readonly_fields = ['id', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Auto-configure list_display
        if self.list_display_fields:
            self.list_display = self.list_display_fields

        # Auto-configure list_filter
        if self.list_filter_fields:
            self.list_filter = self.list_filter_fields

    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly"""
        return self.readonly_fields


def create_api_for_model(model, **kwargs):
    """
    Factory function to create a complete API setup for a model.

    Returns: (ViewSet, Serializer, Admin) classes

    Usage:
        from apps.core.api import create_api_for_model
        from apps.languages.models import Language

        LanguageViewSet, LanguageSerializer, LanguageAdmin = create_api_for_model(
            Language,
            filterset_fields=['code', 'is_active'],
            search_fields=['name', 'native_name'],
            list_display=['name', 'code', 'is_active'],
        )
    """

    # Create Serializer
    meta_class = type('Meta', (), {
        'model': model,
        'fields': '__all__',
        'read_only_fields': kwargs.get('read_only_fields', ('id', 'created_at', 'updated_at')),
    })

    serializer_class = type(
        f'{model.__name__}Serializer',
        (BaseModelSerializer,),
        {'Meta': meta_class}
    )

    # Create ViewSet
    viewset_class = type(
        f'{model.__name__}ViewSet',
        (BaseModelViewSet,),
        {
            'model': model,
            'serializer_class': serializer_class,
            'filterset_fields': kwargs.get('filterset_fields', []),
            'search_fields': kwargs.get('search_fields', []),
            'ordering_fields': kwargs.get('ordering_fields', ['created_at']),
        }
    )

    # Create Admin
    admin_class = type(
        f'{model.__name__}Admin',
        (BaseModelAdmin,),
        {
            'list_display_fields': kwargs.get('list_display', []),
            'search_fields': kwargs.get('search_fields', []),
            'list_filter_fields': kwargs.get('list_filter', []),
        }
    )

    return viewset_class, serializer_class, admin_class


# Swagger schema decorators for common patterns
def list_schema(description="List all items"):
    """Decorator for list action"""
    return extend_schema(
        description=description,
        parameters=[
            OpenApiParameter(name='page', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='page_size', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='search', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ]
    )


def create_schema(description="Create a new item"):
    """Decorator for create action"""
    return extend_schema(description=description)


def retrieve_schema(description="Retrieve item details"):
    """Decorator for retrieve action"""
    return extend_schema(description=description)


def update_schema(description="Update an item"):
    """Decorator for update action"""
    return extend_schema(description=description)


def destroy_schema(description="Delete an item"):
    """Decorator for destroy action"""
    return extend_schema(description=description)
