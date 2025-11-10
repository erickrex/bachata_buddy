from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    User profile serializer.
    
    Represents user account information. Username is read-only after creation.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'display_name', 'is_instructor', 'preferences']
        read_only_fields = ['id', 'username']
        extra_kwargs = {
            'email': {'help_text': 'User email address'},
            'display_name': {'help_text': 'Display name shown in the app'},
            'is_instructor': {'help_text': 'Whether user has instructor privileges'},
            'preferences': {'help_text': 'User preferences as JSON object'}
        }


class RegisterSerializer(serializers.ModelSerializer):
    """
    User registration serializer.
    
    Validates registration data and creates new user accounts.
    Password must meet Django's validation requirements.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        help_text='Password (min 8 characters, not too common, not entirely numeric)',
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        help_text='Password confirmation (must match password)',
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'display_name']
        extra_kwargs = {
            'username': {'help_text': 'Unique username (letters, numbers, @/./+/-/_ only)'},
            'email': {'help_text': 'Email address'},
            'display_name': {'help_text': 'Display name (optional)'}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Login credentials serializer.
    
    Validates username and password for authentication.
    """
    username = serializers.CharField(
        required=True,
        help_text='Username'
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        help_text='Password',
        style={'input_type': 'password'}
    )


class UserPreferencesSerializer(serializers.Serializer):
    """
    User preferences serializer.
    
    Manages user preferences stored in the User.preferences JSONField.
    All fields are optional to support partial updates.
    """
    DIFFICULTY_CHOICES = ['beginner', 'intermediate', 'advanced']
    
    auto_save_choreographies = serializers.BooleanField(
        required=False,
        help_text='Automatically save generated choreographies to collection'
    )
    default_difficulty = serializers.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        required=False,
        help_text='Default difficulty level for choreography generation'
    )
    email_notifications = serializers.BooleanField(
        required=False,
        help_text='Enable email notifications for task completion'
    )
    
    def validate_default_difficulty(self, value):
        """Validate difficulty is one of the allowed choices"""
        if value not in self.DIFFICULTY_CHOICES:
            raise serializers.ValidationError(
                f"Invalid difficulty. Must be one of: {', '.join(self.DIFFICULTY_CHOICES)}"
            )
        return value
