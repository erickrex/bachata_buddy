from rest_framework import serializers
from .models import SavedChoreography
import uuid


class SaveChoreographySerializer(serializers.Serializer):
    """
    Serializer for saving a completed choreography task to collection.
    
    Used to convert a ChoreographyTask result into a SavedChoreography record.
    """
    task_id = serializers.UUIDField(
        required=True,
        help_text='UUID of the completed choreography task'
    )
    title = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text='Optional title for the choreography (auto-generated if not provided)'
    )
    difficulty = serializers.ChoiceField(
        choices=['beginner', 'intermediate', 'advanced'],
        required=False,
        help_text='Optional difficulty level (uses task difficulty if not provided)'
    )
    
    def validate_task_id(self, value):
        """Validate task_id is a valid UUID"""
        if not isinstance(value, uuid.UUID):
            try:
                uuid.UUID(str(value))
            except ValueError:
                raise serializers.ValidationError("Invalid UUID format")
        return value


class BulkDeleteSerializer(serializers.Serializer):
    """
    Serializer for bulk delete confirmation.
    
    Requires explicit confirmation to prevent accidental deletion of all choreographies.
    """
    confirmation = serializers.BooleanField(
        required=True,
        help_text='Must be true to confirm deletion of all choreographies'
    )
    
    def validate_confirmation(self, value):
        """Validate that confirmation is explicitly true"""
        if value is not True:
            raise serializers.ValidationError("Confirmation required to delete all choreographies")
        return value


class SavedChoreographySerializer(serializers.ModelSerializer):
    """
    Saved choreography serializer.
    
    Represents a choreography saved to the user's collection with metadata.
    """
    class Meta:
        model = SavedChoreography
        fields = [
            'id', 'title', 'video_path', 'difficulty', 'duration',
            'music_info', 'generation_parameters', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'title': {'help_text': 'Choreography title'},
            'video_path': {'help_text': 'URL or path to the video file'},
            'difficulty': {'help_text': 'Difficulty level (beginner, intermediate, advanced)'},
            'duration': {'help_text': 'Duration in seconds'},
            'music_info': {'help_text': 'Music metadata as JSON (song, artist, tempo, etc.)'},
            'generation_parameters': {'help_text': 'Parameters used for generation as JSON'}
        }


class CollectionStatsSerializer(serializers.Serializer):
    """
    Collection statistics serializer.
    
    Provides aggregate statistics about a user's choreography collection.
    """
    total_count = serializers.IntegerField(
        help_text='Total number of saved choreographies'
    )
    by_difficulty = serializers.DictField(
        help_text='Count of choreographies by difficulty level'
    )
    total_duration = serializers.FloatField(
        help_text='Total duration of all choreographies in seconds'
    )
