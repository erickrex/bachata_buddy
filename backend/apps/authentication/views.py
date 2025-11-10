from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample
from .models import User
from .serializers import RegisterSerializer, UserSerializer, LoginSerializer, UserPreferencesSerializer


@extend_schema_view(
    post=extend_schema(
        summary="Register new user",
        description="Create a new user account with username, email, and password. Returns user data and JWT tokens.",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=UserSerializer,
                description="User successfully registered",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={
                            'user': {
                                'id': 1,
                                'username': 'dancer123',
                                'email': 'dancer@example.com',
                                'display_name': 'Dancer',
                                'is_instructor': False,
                                'preferences': {}
                            },
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                        }
                    )
                ]
            ),
            400: OpenApiResponse(
                description="Validation error (passwords don't match, username taken, etc.)",
                examples=[
                    OpenApiExample(
                        'Password Mismatch',
                        value={'password': ["Password fields didn't match."]}
                    ),
                    OpenApiExample(
                        'Username Taken',
                        value={'username': ['A user with that username already exists.']}
                    )
                ]
            )
        },
        tags=['Authentication']
    )
)
class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.
    
    Creates a new user account and returns JWT tokens for immediate authentication.
    The password must meet Django's password validation requirements (minimum 8 characters,
    not too common, not entirely numeric, not too similar to other user attributes).
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        summary="Login user",
        description="Authenticate with username and password. Returns user data and JWT tokens (access + refresh).",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="Login successful",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={
                            'user': {
                                'id': 1,
                                'username': 'dancer123',
                                'email': 'dancer@example.com',
                                'display_name': 'Dancer',
                                'is_instructor': False,
                                'preferences': {}
                            },
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description="Invalid credentials or account disabled",
                examples=[
                    OpenApiExample(
                        'Invalid Credentials',
                        value={'error': 'Invalid username or password'}
                    ),
                    OpenApiExample(
                        'Account Disabled',
                        value={'error': 'User account is disabled'}
                    )
                ]
            )
        },
        tags=['Authentication']
    )
)
class LoginView(generics.GenericAPIView):
    """
    Authenticate user and obtain JWT tokens.
    
    Validates user credentials and returns JWT access and refresh tokens along with user data.
    Access tokens expire after 60 minutes, refresh tokens after 7 days.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        # Check if user exists and is active
        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                return Response(
                    {'error': 'User account is disabled'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Authenticate user (verify password)
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get user profile",
    description="Retrieve the authenticated user's profile information.",
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description="User profile data",
            examples=[
                OpenApiExample(
                    'Profile Response',
                    value={
                        'id': 1,
                        'username': 'dancer123',
                        'email': 'dancer@example.com',
                        'display_name': 'Dancer',
                        'is_instructor': False,
                        'preferences': {'theme': 'dark', 'notifications': True}
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Authentication'],
    methods=['GET']
)
@extend_schema(
    summary="Update user profile",
    description="Update the authenticated user's profile information. Username cannot be changed.",
    request=UserSerializer,
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description="Profile updated successfully",
            examples=[
                OpenApiExample(
                    'Updated Profile',
                    value={
                        'id': 1,
                        'username': 'dancer123',
                        'email': 'newemail@example.com',
                        'display_name': 'Pro Dancer',
                        'is_instructor': False,
                        'preferences': {'theme': 'light', 'notifications': False}
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Validation error",
            examples=[
                OpenApiExample(
                    'Invalid Email',
                    value={'email': ['Enter a valid email address.']}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Authentication'],
    methods=['PUT']
)
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get or update user profile.
    
    GET: Retrieve the authenticated user's profile information.
    PUT: Update the authenticated user's profile (partial updates supported).
    """
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get user preferences",
    description="""
    Retrieve the authenticated user's preferences.
    
    Returns user preferences stored in the User.preferences JSONField.
    If preferences haven't been set, returns default values:
    - auto_save_choreographies: true
    - default_difficulty: intermediate
    - email_notifications: false
    """,
    responses={
        200: OpenApiResponse(
            description="User preferences",
            examples=[
                OpenApiExample(
                    'Preferences Response',
                    value={
                        'auto_save_choreographies': True,
                        'default_difficulty': 'intermediate',
                        'email_notifications': False
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Authentication'],
    methods=['GET']
)
@extend_schema(
    summary="Update user preferences",
    description="""
    Update the authenticated user's preferences.
    
    Supports partial updates - only include fields you want to change.
    Preferences are stored in the User.preferences JSONField and merged
    with existing preferences.
    
    **Available Preferences:**
    - auto_save_choreographies (boolean): Auto-save generated choreographies
    - default_difficulty (string): Default difficulty (beginner/intermediate/advanced)
    - email_notifications (boolean): Enable email notifications
    """,
    request=UserPreferencesSerializer,
    responses={
        200: OpenApiResponse(
            description="Preferences updated successfully",
            examples=[
                OpenApiExample(
                    'Updated Preferences',
                    value={
                        'auto_save_choreographies': False,
                        'default_difficulty': 'advanced',
                        'email_notifications': True
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Validation error",
            examples=[
                OpenApiExample(
                    'Invalid Difficulty',
                    value={'default_difficulty': ['"expert" is not a valid choice.']}
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required")
    },
    tags=['Authentication'],
    methods=['PUT']
)
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_preferences(request):
    """
    Get or update user preferences.
    
    GET: Retrieve user preferences with defaults if not set.
    PUT: Update user preferences (partial updates supported).
    """
    if request.method == 'GET':
        # Get preferences with defaults
        preferences = request.user.preferences or {}
        
        response_data = {
            'auto_save_choreographies': preferences.get('auto_save_choreographies', True),
            'default_difficulty': preferences.get('default_difficulty', 'intermediate'),
            'email_notifications': preferences.get('email_notifications', False)
        }
        
        return Response(response_data)
    
    elif request.method == 'PUT':
        # Validate and update preferences
        serializer = UserPreferencesSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Merge with existing preferences
        preferences = request.user.preferences or {}
        preferences.update(serializer.validated_data)
        
        # Save to user model
        request.user.preferences = preferences
        request.user.save()
        
        # Return updated preferences with defaults
        response_data = {
            'auto_save_choreographies': preferences.get('auto_save_choreographies', True),
            'default_difficulty': preferences.get('default_difficulty', 'intermediate'),
            'email_notifications': preferences.get('email_notifications', False)
        }
        
        return Response(response_data)
