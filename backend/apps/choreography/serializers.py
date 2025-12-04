from rest_framework import serializers
from .models import ChoreographyTask, Song


class SongSerializer(serializers.ModelSerializer):
    """
    Serializer for song list views.
    
    Returns basic song metadata without the audio_path for list views.
    """
    
    class Meta:
        model = Song
        fields = ['id', 'title', 'artist', 'duration', 'bpm', 'genre', 'created_at']
        read_only_fields = fields


class SongDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer including audio path.
    
    Used for individual song detail views where the audio_path is needed.
    """
    
    class Meta:
        model = Song
        fields = ['id', 'title', 'artist', 'duration', 'bpm', 'genre', 'audio_path', 'created_at', 'updated_at']
        read_only_fields = fields


class SongGenerationSerializer(serializers.Serializer):
    """
    Serializer for generating choreography from a song template.
    
    Validates song_id exists and difficulty level is valid.
    """
    song_id = serializers.IntegerField(required=True)
    difficulty = serializers.ChoiceField(
        choices=['beginner', 'intermediate', 'advanced'],
        default='intermediate',
        help_text="Difficulty level of the choreography"
    )
    energy_level = serializers.ChoiceField(
        choices=['low', 'medium', 'high'],
        required=False,
        allow_blank=True,
        help_text="Energy level of the choreography (optional)"
    )
    style = serializers.ChoiceField(
        choices=['traditional', 'modern', 'romantic', 'sensual'],
        required=False,
        allow_blank=True,
        help_text="Style of the choreography (optional)"
    )
    
    def validate_song_id(self, value):
        """Validate that the song exists in the database."""
        if not Song.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Song with ID {value} does not exist")
        return value


class ChoreographyTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for choreography task status.
    
    Returns the current status and progress of a choreography generation task.
    All fields are read-only as tasks are updated by the background job.
    """
    task_id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    progress = serializers.IntegerField(read_only=True, min_value=0, max_value=100)
    stage = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    result = serializers.SerializerMethodField()
    error = serializers.CharField(read_only=True, allow_null=True)
    song = SongSerializer(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    def get_result(self, obj):
        """
        Convert file:// URLs to HTTP URLs for video access.
        
        The job stores file:// paths, but the frontend needs HTTP URLs.
        """
        if not obj.result:
            return None
        
        result = obj.result.copy() if isinstance(obj.result, dict) else {}
        
        # Convert file:// URL to HTTP URL
        if 'video_url' in result and result['video_url']:
            video_url = result['video_url']
            # If it's a file:// URL, convert to HTTP endpoint
            if video_url.startswith('file://'):
                # Generate HTTP URL for video serving endpoint
                request = self.context.get('request')
                if request:
                    result['video_url'] = request.build_absolute_uri(
                        f'/api/choreography/videos/{obj.task_id}/'
                    )
            elif not video_url.startswith('http'):
                # If it's a relative path, also convert to HTTP
                request = self.context.get('request')
                if request:
                    result['video_url'] = request.build_absolute_uri(
                        f'/api/choreography/videos/{obj.task_id}/'
                    )
        
        return result
    
    class Meta:
        model = ChoreographyTask
        fields = [
            'task_id', 'status', 'progress', 'stage', 'message',
            'result', 'error', 'song', 'created_at', 'updated_at'
        ]
        read_only_fields = ['task_id', 'status', 'progress', 'stage', 'message', 'error', 'song', 'created_at', 'updated_at']


class ChoreographyTaskListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing choreography tasks.
    
    Used for paginated list views where full details are not needed.
    """
    task_id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    progress = serializers.IntegerField(read_only=True)
    stage = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    song = SongSerializer(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = ChoreographyTask
        fields = [
            'task_id', 'status', 'progress', 'stage', 'message',
            'song', 'created_at', 'updated_at'
        ]
        read_only_fields = fields



class QueryParseSerializer(serializers.Serializer):
    """
    Serializer for natural language query parsing.
    
    Validates user's natural language input for AI parsing.
    """
    query = serializers.CharField(
        required=True,
        max_length=1000,
        help_text="Natural language description of desired choreography"
    )
    
    def validate_query(self, value):
        """Validate query is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Query cannot be empty")
        return value.strip()


class AIGenerationSerializer(serializers.Serializer):
    """
    Serializer for AI-enhanced choreography generation.
    
    Accepts natural language query and optional pre-parsed parameters.
    """
    query = serializers.CharField(
        required=True,
        max_length=1000,
        help_text="Natural language description of desired choreography"
    )
    parameters = serializers.JSONField(
        required=False,
        help_text="Optional pre-parsed parameters (if not provided, will parse from query)"
    )
    
    def validate_query(self, value):
        """Validate query is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Query cannot be empty")
        return value.strip()


class DescribeChoreographySerializer(serializers.Serializer):
    """
    Serializer for Path 2 natural language choreography description.
    
    Validates user's natural language request for agent-based choreography generation.
    This endpoint uses OpenAI function calling for intelligent workflow orchestration.
    """
    user_request = serializers.CharField(
        required=True,
        min_length=10,
        max_length=2000,
        help_text="Natural language description of desired choreography"
    )
    
    def validate_user_request(self, value):
        """
        Validate and sanitize user request.
        
        - Ensures request is not empty or only whitespace
        - Strips leading/trailing whitespace
        - Validates minimum meaningful length
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Request cannot be empty")
        
        # Strip whitespace
        value = value.strip()
        
        # Check minimum length after stripping
        if len(value) < 10:
            raise serializers.ValidationError(
                "Request must be at least 10 characters long"
            )
        
        # Basic sanitization - remove excessive whitespace
        import re
        value = re.sub(r'\s+', ' ', value)
        
        return value
