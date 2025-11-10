from rest_framework import serializers
from .models import ClassPlan, ClassPlanSequence
from apps.collections.serializers import SavedChoreographySerializer


class ClassPlanSequenceSerializer(serializers.ModelSerializer):
    """Serializer for class plan sequences with nested choreography"""
    choreography = SavedChoreographySerializer(read_only=True)
    
    class Meta:
        model = ClassPlanSequence
        fields = [
            'id', 'sequence_order', 'choreography',
            'notes', 'estimated_time'
        ]
        read_only_fields = ['id', 'sequence_order']


class ClassPlanSerializer(serializers.ModelSerializer):
    """Basic serializer for class plans (list view)"""
    sequence_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ClassPlan
        fields = [
            'id', 'title', 'description', 'difficulty_level',
            'estimated_duration', 'instructor_notes', 'sequence_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClassPlanDetailSerializer(ClassPlanSerializer):
    """Detailed serializer for class plans with nested sequences"""
    sequences = ClassPlanSequenceSerializer(many=True, read_only=True)
    
    class Meta(ClassPlanSerializer.Meta):
        fields = ClassPlanSerializer.Meta.fields + ['sequences']


class AddSequenceSerializer(serializers.Serializer):
    """Serializer for adding a choreography to a class plan"""
    choreography_id = serializers.UUIDField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    estimated_time = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_estimated_time(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Estimated time must be positive")
        return value


class ReorderSequencesSerializer(serializers.Serializer):
    """Serializer for reordering sequences in a class plan"""
    sequence_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        allow_empty=False
    )
