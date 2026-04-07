from firebase_admin import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ImproperlyConfigured
User = get_user_model()
class FirebaseAuthenticationBackend(BaseBackend):
    def authenticate(self, request, id_token=None):
        if id_token is None:
            return None
        try:
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token.get('uid')
            email = decoded_token.get('email')
            if not uid:
                return None
            user, created = User.objects.get_or_create(
                username=uid, 
                defaults={'email': email or ''}
            )
                        
            return user
        except auth.InvalidIdToken:
            # Token verification failed (expired, malformed, etc.)
            return None
        except Exception as e:
            # Handle other potential errors
            print(f"Firebase authentication error: {e}")
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None