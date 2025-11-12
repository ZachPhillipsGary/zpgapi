"""Supabase authentication backend for Django."""
from rest_framework import authentication, exceptions
from django.conf import settings
from supabase import create_client, Client
import jwt


class SupabaseAuthentication(authentication.BaseAuthentication):
    """
    Authenticate users using Supabase JWT tokens.

    Expects the Authorization header to be in format:
    Authorization: Bearer <supabase_access_token>
    """

    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).decode('utf-8')

        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        try:
            token = auth_header.split(' ')[1]

            # Verify the JWT token
            user_data = self.verify_token(token)

            # Create a user object with Supabase user data
            user = SupabaseUser(user_data)

            return (user, token)

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Authentication failed: {str(e)}')

    def verify_token(self, token):
        """Verify the Supabase JWT token."""
        # Decode the token (Supabase uses HS256 by default)
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}  # Supabase already verified it
        )

        # Verify with Supabase
        user_response = self.supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise exceptions.AuthenticationFailed('Invalid user')

        return user_response.user


class SupabaseUser:
    """
    A user object that wraps Supabase user data.
    Compatible with Django's authentication system.
    """

    def __init__(self, supabase_user):
        self.supabase_user = supabase_user
        self.id = supabase_user.id
        self.email = supabase_user.email
        self.is_authenticated = True
        self.is_active = True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_staff(self):
        # Check if user has admin role in Supabase metadata
        return self.supabase_user.user_metadata.get('is_staff', False)

    @property
    def is_superuser(self):
        return self.supabase_user.user_metadata.get('is_superuser', False)

    def __str__(self):
        return self.email or self.id
