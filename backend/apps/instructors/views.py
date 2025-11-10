from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count, Max, Q, F
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from datetime import timedelta
from django.utils import timezone

from .models import ClassPlan, ClassPlanSequence
from .serializers import (
    ClassPlanSerializer,
    ClassPlanDetailSerializer,
    ClassPlanSequenceSerializer,
    AddSequenceSerializer,
    ReorderSequencesSerializer
)
from apps.collections.models import SavedChoreography
from core.permissions import IsInstructor
import logging

logger = logging.getLogger(__name__)


class ClassPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for class plan CRUD operations"""
    permission_classes = [IsAuthenticated, IsInstructor]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['difficulty_level']
    ordering_fields = ['created_at', 'title', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return only instructor's class plans with sequence count"""
        return ClassPlan.objects.filter(
            instructor=self.request.user
        ).annotate(
            sequence_count=Count('sequences')
        )
    
    def get_serializer_class(self):
        """Use detail serializer for retrieve, basic for list"""
        if self.action == 'retrieve':
            return ClassPlanDetailSerializer
        return ClassPlanSerializer
    
    def perform_create(self, serializer):
        """Set instructor to current user"""
        instance = serializer.save(instructor=self.request.user)
        # Re-fetch with annotation for sequence_count
        instance = ClassPlan.objects.annotate(
            sequence_count=Count('sequences')
        ).get(id=instance.id)
        serializer.instance = instance
    
    @action(detail=True, methods=['post'], url_path='add-sequence')
    def add_sequence(self, request, pk=None):
        """Add choreography to class plan"""
        class_plan = self.get_object()
        serializer = AddSequenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        choreography_id = serializer.validated_data['choreography_id']
        
        # Validate choreography exists and belongs to instructor
        choreography = get_object_or_404(
            SavedChoreography,
            id=choreography_id,
            user=request.user
        )
        
        # Get next sequence order
        max_order = class_plan.sequences.aggregate(
            Max('sequence_order')
        )['sequence_order__max']
        next_order = (max_order + 1) if max_order is not None else 0
        
        # Create sequence
        sequence = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=choreography,
            sequence_order=next_order,
            notes=serializer.validated_data.get('notes', ''),
            estimated_time=serializer.validated_data.get('estimated_time')
        )
        
        return Response(
            ClassPlanSequenceSerializer(sequence).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['delete'], url_path='sequences/(?P<sequence_id>[^/.]+)')
    def delete_sequence(self, request, pk=None, sequence_id=None):
        """Delete sequence and reorder remaining"""
        class_plan = self.get_object()
        
        # Get and delete sequence
        sequence = get_object_or_404(
            ClassPlanSequence,
            id=sequence_id,
            class_plan=class_plan
        )
        deleted_order = sequence.sequence_order
        sequence.delete()
        
        # Reorder remaining sequences
        ClassPlanSequence.objects.filter(
            class_plan=class_plan,
            sequence_order__gt=deleted_order
        ).update(sequence_order=F('sequence_order') - 1)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['put'], url_path='sequences/(?P<sequence_id>[^/.]+)')
    def update_sequence(self, request, pk=None, sequence_id=None):
        """Update sequence notes and estimated_time"""
        class_plan = self.get_object()
        
        sequence = get_object_or_404(
            ClassPlanSequence,
            id=sequence_id,
            class_plan=class_plan
        )
        
        # Update fields
        if 'notes' in request.data:
            sequence.notes = request.data['notes']
        if 'estimated_time' in request.data:
            sequence.estimated_time = request.data['estimated_time']
        
        sequence.save()
        
        return Response(
            ClassPlanSequenceSerializer(sequence).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], url_path='reorder-sequences')
    @transaction.atomic
    def reorder_sequences(self, request, pk=None):
        """Reorder sequences in class plan"""
        class_plan = self.get_object()
        serializer = ReorderSequencesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        sequence_ids = serializer.validated_data['sequence_ids']
        
        # Validate all sequences belong to this class plan
        sequences = ClassPlanSequence.objects.filter(
            class_plan=class_plan,
            id__in=sequence_ids
        )
        
        if sequences.count() != len(sequence_ids):
            return Response(
                {'error': 'Invalid sequence IDs'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update sequence orders
        # First, set all to negative values to avoid unique constraint violations
        for i, seq_id in enumerate(sequence_ids):
            ClassPlanSequence.objects.filter(id=seq_id).update(
                sequence_order=-(i + 1)
            )
        
        # Then set to final positive values
        updated = []
        for order, seq_id in enumerate(sequence_ids):
            ClassPlanSequence.objects.filter(id=seq_id).update(
                sequence_order=order
            )
            updated.append({'id': str(seq_id), 'sequence_order': order})
        
        return Response({
            'message': 'Sequences reordered successfully',
            'sequences': updated
        })
    
    @action(detail=True, methods=['post'], url_path='duplicate')
    @transaction.atomic
    def duplicate(self, request, pk=None):
        """Duplicate class plan with all sequences"""
        original = self.get_object()
        
        # Create new class plan
        new_plan = ClassPlan.objects.create(
            instructor=request.user,
            title=f"{original.title} (Copy)",
            description=original.description,
            difficulty_level=original.difficulty_level,
            estimated_duration=original.estimated_duration,
            instructor_notes=original.instructor_notes
        )
        
        # Copy all sequences
        sequences = original.sequences.all()
        for seq in sequences:
            ClassPlanSequence.objects.create(
                class_plan=new_plan,
                choreography=seq.choreography,
                sequence_order=seq.sequence_order,
                notes=seq.notes,
                estimated_time=seq.estimated_time
            )
        
        # Annotate with sequence_count for serializer
        new_plan = ClassPlan.objects.annotate(
            sequence_count=Count('sequences')
        ).get(id=new_plan.id)
        
        return Response(
            ClassPlanDetailSerializer(new_plan).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        """Generate class plan summary"""
        class_plan = self.get_object()
        sequences = class_plan.sequences.select_related('choreography').all()
        
        # Calculate difficulty breakdown
        difficulty_breakdown = {
            'beginner': 0,
            'intermediate': 0,
            'advanced': 0
        }
        for seq in sequences:
            difficulty_breakdown[seq.choreography.difficulty] += 1
        
        # Calculate total estimated duration
        total_duration = sum(
            seq.estimated_time or 0 for seq in sequences
        )
        
        # Build sequence list
        sequence_list = [
            {
                'order': seq.sequence_order,
                'title': seq.choreography.title,
                'difficulty': seq.choreography.difficulty,
                'duration': seq.choreography.duration,
                'estimated_time': seq.estimated_time,
                'notes': seq.notes
            }
            for seq in sequences
        ]
        
        return Response({
            'title': class_plan.title,
            'total_sequences': len(sequences),
            'total_estimated_duration': total_duration,
            'difficulty_breakdown': difficulty_breakdown,
            'sequences': sequence_list
        })
    
    @action(detail=True, methods=['get'], url_path='export')
    def export(self, request, pk=None):
        """Export class plan as formatted HTML"""
        from django.template.loader import render_to_string
        from django.http import HttpResponse
        
        class_plan = self.get_object()
        sequences = class_plan.sequences.select_related('choreography').all()
        
        # Calculate total duration
        total_duration = sum(seq.estimated_time or 0 for seq in sequences)
        
        # Render HTML template
        html_content = render_to_string('instructors/class_plan_export.html', {
            'class_plan': class_plan,
            'sequences': sequences,
            'total_duration': total_duration
        })
        
        return HttpResponse(html_content, content_type='text/html')


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInstructor])
def instructor_stats(request):
    """Get instructor dashboard statistics"""
    class_plans = ClassPlan.objects.filter(instructor=request.user)
    
    # Calculate statistics
    total_plans = class_plans.count()
    
    # Get unique choreographies used
    unique_choreographies = ClassPlanSequence.objects.filter(
        class_plan__instructor=request.user
    ).values('choreography').distinct().count()
    
    # Difficulty breakdown
    difficulty_breakdown = {
        'beginner': class_plans.filter(difficulty_level='beginner').count(),
        'intermediate': class_plans.filter(difficulty_level='intermediate').count(),
        'advanced': class_plans.filter(difficulty_level='advanced').count(),
    }
    
    # Recent plans (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_count = class_plans.filter(created_at__gte=thirty_days_ago).count()
    
    # Average sequences per plan
    if total_plans > 0:
        total_sequences = ClassPlanSequence.objects.filter(
            class_plan__instructor=request.user
        ).count()
        avg_sequences = round(total_sequences / total_plans, 1)
    else:
        avg_sequences = 0
    
    return Response({
        'total_class_plans': total_plans,
        'total_unique_choreographies': unique_choreographies,
        'difficulty_breakdown': difficulty_breakdown,
        'recent_count': recent_count,
        'avg_sequences_per_plan': avg_sequences
    })
