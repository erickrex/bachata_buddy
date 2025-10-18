from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db import models
from .models import ClassPlan, ClassPlanSequence
from .forms import ClassPlanForm, ClassPlanSequenceForm
from choreography.models import SavedChoreography


def require_instructor(view_func):
    """Decorator to ensure user is an instructor"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not request.user.is_instructor:
            raise PermissionDenied("You must be an instructor to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@require_instructor
def dashboard(request):
    """
    Instructor dashboard view showing all class plans.
    
    Requirements: 11.5
    - Filter ClassPlan by instructor (request.user)
    - Display list of class plans
    - Require is_instructor check
    """
    class_plans = ClassPlan.objects.filter(
        instructor=request.user
    ).prefetch_related('sequences__choreography')
    
    context = {
        'class_plans': class_plans,
        'total_plans': class_plans.count(),
    }
    
    return render(request, 'instructors/dashboard.html', context)


@login_required
@require_instructor
def class_plan_create(request):
    """
    Create a new class plan.
    
    Requirements: 11.5
    - Verify user is instructor
    - Handle ClassPlanSequence relationships
    """
    try:
        if request.method == 'POST':
            form = ClassPlanForm(request.POST)
            if form.is_valid():
                try:
                    class_plan = form.save(commit=False)
                    class_plan.instructor = request.user
                    class_plan.save()
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Class plan {class_plan.id} created by instructor {request.user.id}")
                    return redirect('instructors:class_plan_detail', pk=class_plan.id)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error saving class plan for instructor {request.user.id}: {e}", exc_info=True)
                    from django.contrib import messages
                    messages.error(request, 'An error occurred while creating the class plan.')
        else:
            form = ClassPlanForm()
        
        context = {
            'form': form,
        }
        return render(request, 'instructors/class_plan_form.html', context)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in class_plan_create for instructor {request.user.id}: {e}", exc_info=True)
        from django.contrib import messages
        messages.error(request, 'An unexpected error occurred.')
        return redirect('instructors:dashboard')


@login_required
@require_instructor
def class_plan_detail(request, pk):
    """
    View details of a specific class plan.
    
    Requirements: 11.5
    - Verify user is instructor and owns the class plan
    - Display class plan with sequences
    """
    class_plan = get_object_or_404(
        ClassPlan,
        pk=pk,
        instructor=request.user
    )
    
    # Get sequences with choreography details
    sequences = class_plan.sequences.select_related('choreography').all()
    
    # Get user's choreographies for adding to sequences
    available_choreographies = SavedChoreography.objects.filter(
        user=request.user
    ).exclude(
        id__in=sequences.values_list('choreography_id', flat=True)
    )
    
    context = {
        'class_plan': class_plan,
        'sequences': sequences,
        'available_choreographies': available_choreographies,
    }
    
    return render(request, 'instructors/class_plan_detail.html', context)


@login_required
@require_instructor
def class_plan_edit(request, pk):
    """
    Edit an existing class plan.
    
    Requirements: 11.5
    - Verify user is instructor and owns the class plan
    """
    class_plan = get_object_or_404(
        ClassPlan,
        pk=pk,
        instructor=request.user
    )
    
    if request.method == 'POST':
        form = ClassPlanForm(request.POST, instance=class_plan)
        if form.is_valid():
            form.save()
            return redirect('instructors:class_plan_detail', pk=class_plan.id)
    else:
        form = ClassPlanForm(instance=class_plan)
    
    context = {
        'form': form,
        'class_plan': class_plan,
        'is_edit': True,
    }
    return render(request, 'instructors/class_plan_form.html', context)


@login_required
@require_instructor
@require_http_methods(["POST", "DELETE"])
def class_plan_delete(request, pk):
    """
    Delete a class plan.
    
    Requirements: 11.5
    - Verify user is instructor and owns the class plan
    """
    class_plan = get_object_or_404(
        ClassPlan,
        pk=pk,
        instructor=request.user
    )
    
    class_plan_title = class_plan.title
    class_plan.delete()
    
    # Check if HTMX request
    if request.headers.get('HX-Request'):
        return JsonResponse({
            'success': True,
            'message': f'Class plan "{class_plan_title}" deleted successfully'
        })
    
    return redirect('instructors:dashboard')


@login_required
@require_instructor
@require_http_methods(["POST"])
def sequence_add(request, pk):
    """
    Add a choreography to a class plan sequence.
    
    Requirements: 11.5
    - Handle ClassPlanSequence relationships
    - Verify user owns both class plan and choreography
    """
    try:
        class_plan = get_object_or_404(
            ClassPlan,
            pk=pk,
            instructor=request.user
        )
        
        choreography_id = request.POST.get('choreography_id')
        notes = request.POST.get('notes', '').strip()
        estimated_time = request.POST.get('estimated_time', '')
        
        if not choreography_id:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Missing choreography_id in sequence_add for class plan {pk}")
            return JsonResponse({
                'success': False,
                'error': 'Choreography ID is required'
            }, status=400)
        
        # Verify user owns the choreography
        choreography = get_object_or_404(
            SavedChoreography,
            pk=choreography_id,
            user=request.user
        )
        
        # Get next sequence order
        max_order = class_plan.sequences.aggregate(
            models.Max('sequence_order')
        )['sequence_order__max']
        next_order = (max_order or 0) + 1
        
        # Parse and validate estimated_time
        parsed_time = None
        if estimated_time:
            try:
                parsed_time = int(estimated_time)
                if parsed_time < 0:
                    parsed_time = None
            except (ValueError, TypeError):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Invalid estimated_time value: {estimated_time}")
        
        # Create sequence
        sequence = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=choreography,
            sequence_order=next_order,
            notes=notes,
            estimated_time=parsed_time
        )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Sequence {sequence.id} added to class plan {class_plan.id}")
        
        if request.headers.get('HX-Request'):
            return JsonResponse({
                'success': True,
                'sequence_id': str(sequence.id),
                'message': 'Choreography added to class plan'
            })
        
        return redirect('instructors:class_plan_detail', pk=class_plan.id)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error adding sequence to class plan {pk}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred while adding choreography'
        }, status=500)


@login_required
@require_instructor
@require_http_methods(["POST", "DELETE"])
def sequence_delete(request, pk, sequence_id):
    """
    Remove a choreography from a class plan sequence.
    
    Requirements: 11.5
    - Handle ClassPlanSequence relationships
    - Verify user owns the class plan
    """
    class_plan = get_object_or_404(
        ClassPlan,
        pk=pk,
        instructor=request.user
    )
    
    sequence = get_object_or_404(
        ClassPlanSequence,
        pk=sequence_id,
        class_plan=class_plan
    )
    
    sequence.delete()
    
    # Reorder remaining sequences
    remaining_sequences = class_plan.sequences.order_by('sequence_order')
    for index, seq in enumerate(remaining_sequences, start=1):
        if seq.sequence_order != index:
            seq.sequence_order = index
            seq.save()
    
    if request.headers.get('HX-Request'):
        return JsonResponse({
            'success': True,
            'message': 'Choreography removed from class plan'
        })
    
    return redirect('instructors:class_plan_detail', pk=class_plan.id)


@login_required
@require_instructor
@require_http_methods(["POST"])
def sequence_reorder(request, pk):
    """
    Reorder sequences in a class plan.
    
    Requirements: 11.5
    - Handle ClassPlanSequence relationships
    """
    class_plan = get_object_or_404(
        ClassPlan,
        pk=pk,
        instructor=request.user
    )
    
    # Expect JSON with sequence_ids in new order
    import json
    try:
        data = json.loads(request.body)
        sequence_ids = data.get('sequence_ids', [])
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    # Update sequence orders
    for index, sequence_id in enumerate(sequence_ids, start=1):
        ClassPlanSequence.objects.filter(
            pk=sequence_id,
            class_plan=class_plan
        ).update(sequence_order=index)
    
    return JsonResponse({
        'success': True,
        'message': 'Sequences reordered successfully'
    })



@login_required
@require_instructor
def class_plan_summary(request, pk):
    """
    Generate a structured summary of a class plan.
    
    FastAPI parity: GET /instructor/class-plans/{id}/summary
    Returns detailed summary with timing, progression analysis, and teaching recommendations.
    """
    try:
        class_plan = get_object_or_404(
            ClassPlan,
            pk=pk,
            instructor=request.user
        )
        
        # Get sequences with choreography details
        sequences = class_plan.sequences.select_related('choreography').order_by('sequence_order')
        
        # Calculate timing information
        total_estimated_time = sum(seq.estimated_time or 0 for seq in sequences)
        sequence_count = sequences.count()
        
        # Analyze difficulty progression
        difficulty_map = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
        difficulties = [difficulty_map.get(seq.choreography.difficulty, 2) for seq in sequences]
        
        progression_analysis = "balanced"
        if len(difficulties) > 1:
            if all(difficulties[i] <= difficulties[i+1] for i in range(len(difficulties)-1)):
                progression_analysis = "progressive"
            elif all(difficulties[i] >= difficulties[i+1] for i in range(len(difficulties)-1)):
                progression_analysis = "regressive"
        
        # Generate recommendations
        recommendations = []
        if total_estimated_time < 30:
            recommendations.append("Consider adding more choreographies to reach a standard class length (45-60 minutes)")
        if total_estimated_time > 90:
            recommendations.append("Class may be too long. Consider splitting into multiple sessions")
        if sequence_count < 3:
            recommendations.append("Add more choreographies for variety")
        if progression_analysis == "regressive":
            recommendations.append("Consider reordering to progress from easier to harder choreographies")
        
        # Build sequence details
        sequence_details = []
        for seq in sequences:
            sequence_details.append({
                'sequence_order': seq.sequence_order,
                'choreography_id': str(seq.choreography.id),
                'choreography_title': seq.choreography.title,
                'difficulty': seq.choreography.difficulty,
                'duration': seq.choreography.duration,
                'estimated_time': seq.estimated_time,
                'notes': seq.notes
            })
        
        summary = {
            'class_plan_id': str(class_plan.id),
            'title': class_plan.title,
            'description': class_plan.description,
            'difficulty_level': class_plan.difficulty_level,
            'total_sequences': sequence_count,
            'total_estimated_time': total_estimated_time,
            'progression_analysis': progression_analysis,
            'recommendations': recommendations,
            'sequences': sequence_details
        }
        
        return JsonResponse(summary)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating class plan summary for {pk}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to generate class plan summary'
        }, status=500)


@login_required
@require_instructor
def class_plan_export(request, pk):
    """
    Export class plan as printable HTML.
    
    FastAPI parity: GET /instructor/class-plans/{id}/export
    Generates a formatted HTML document suitable for printing or saving as PDF.
    """
    from django.http import HttpResponse
    
    try:
        class_plan = get_object_or_404(
            ClassPlan,
            pk=pk,
            instructor=request.user
        )
        
        # Get sequences with choreography details
        sequences = class_plan.sequences.select_related('choreography').order_by('sequence_order')
        
        # Calculate timing
        total_estimated_time = sum(seq.estimated_time or 0 for seq in sequences)
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{class_plan.title} - Class Plan</title>
    <style>
        @media print {{
            body {{ margin: 0; }}
            .no-print {{ display: none; }}
        }}
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .metadata {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .metadata p {{
            margin: 5px 0;
        }}
        .sequence {{
            border: 1px solid #ddd;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .sequence-header {{
            font-weight: bold;
            color: #4CAF50;
            margin-bottom: 10px;
        }}
        .difficulty {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }}
        .difficulty.beginner {{ background: #4CAF50; color: white; }}
        .difficulty.intermediate {{ background: #FF9800; color: white; }}
        .difficulty.advanced {{ background: #F44336; color: white; }}
        .notes {{
            background: #fffacd;
            padding: 10px;
            margin-top: 10px;
            border-left: 3px solid #ffd700;
        }}
        .print-button {{
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }}
        .print-button:hover {{
            background: #45a049;
        }}
    </style>
</head>
<body>
    <div class="no-print">
        <button class="print-button" onclick="window.print()">🖨️ Print Class Plan</button>
    </div>
    
    <h1>{class_plan.title}</h1>
    
    <div class="metadata">
        <p><strong>Instructor:</strong> {request.user.display_name}</p>
        <p><strong>Difficulty Level:</strong> <span class="difficulty {class_plan.difficulty_level}">{class_plan.difficulty_level.upper()}</span></p>
        <p><strong>Total Sequences:</strong> {sequences.count()}</p>
        <p><strong>Estimated Duration:</strong> {total_estimated_time} minutes</p>
        {f'<p><strong>Description:</strong> {class_plan.description}</p>' if class_plan.description else ''}
    </div>
    
    {f'<div class="notes"><strong>Instructor Notes:</strong><br>{class_plan.instructor_notes}</div>' if class_plan.instructor_notes else ''}
    
    <h2>Choreography Sequence</h2>
"""
        
        for seq in sequences:
            html_content += f"""
    <div class="sequence">
        <div class="sequence-header">
            {seq.sequence_order}. {seq.choreography.title}
            <span class="difficulty {seq.choreography.difficulty}">{seq.choreography.difficulty.upper()}</span>
        </div>
        <p><strong>Duration:</strong> {seq.choreography.duration:.1f} seconds</p>
        {f'<p><strong>Teaching Time:</strong> {seq.estimated_time} minutes</p>' if seq.estimated_time else ''}
        {f'<div class="notes"><strong>Notes:</strong><br>{seq.notes}</div>' if seq.notes else ''}
    </div>
"""
        
        html_content += """
    <div class="no-print" style="margin-top: 30px;">
        <button class="print-button" onclick="window.print()">🖨️ Print Class Plan</button>
    </div>
</body>
</html>
"""
        
        return HttpResponse(html_content, content_type='text/html')
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error exporting class plan {pk}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to export class plan'
        }, status=500)


@login_required
@require_instructor
@require_http_methods(["POST"])
def class_plan_duplicate(request, pk):
    """
    Duplicate an existing class plan.
    
    FastAPI parity: POST /instructor/class-plans/{id}/duplicate
    Creates a copy of the specified class plan with optional sequence copying.
    """
    try:
        source_plan = get_object_or_404(
            ClassPlan,
            pk=pk,
            instructor=request.user
        )
        
        # Parse request data
        data = json.loads(request.body) if request.body else {}
        new_title = data.get('new_title', f"{source_plan.title} (Copy)")
        copy_sequences = data.get('copy_sequences', True)
        
        # Create duplicate class plan
        duplicate_plan = ClassPlan.objects.create(
            instructor=request.user,
            title=new_title,
            description=source_plan.description,
            difficulty_level=source_plan.difficulty_level,
            estimated_duration=source_plan.estimated_duration,
            instructor_notes=source_plan.instructor_notes
        )
        
        # Copy sequences if requested
        if copy_sequences:
            source_sequences = source_plan.sequences.all().order_by('sequence_order')
            for seq in source_sequences:
                ClassPlanSequence.objects.create(
                    class_plan=duplicate_plan,
                    choreography=seq.choreography,
                    sequence_order=seq.sequence_order,
                    notes=seq.notes,
                    estimated_time=seq.estimated_time
                )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Class plan {pk} duplicated to {duplicate_plan.id} by instructor {request.user.id}")
        
        return JsonResponse({
            'success': True,
            'class_plan_id': str(duplicate_plan.id),
            'title': duplicate_plan.title,
            'sequences_copied': copy_sequences
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error duplicating class plan {pk}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to duplicate class plan'
        }, status=500)


@login_required
@require_instructor
def dashboard_stats(request):
    """
    Get instructor dashboard statistics.
    
    FastAPI parity: GET /instructor/dashboard/stats
    Returns comprehensive statistics for the instructor dashboard including
    class plan counts, choreography usage, and recent activity.
    """
    try:
        from django.db.models import Count, Sum, Avg
        from datetime import datetime, timedelta
        
        # Get all class plans for this instructor
        class_plans = ClassPlan.objects.filter(instructor=request.user)
        
        # Basic counts
        total_class_plans = class_plans.count()
        
        # Count by difficulty
        beginner_plans = class_plans.filter(difficulty_level='beginner').count()
        intermediate_plans = class_plans.filter(difficulty_level='intermediate').count()
        advanced_plans = class_plans.filter(difficulty_level='advanced').count()
        
        # Get choreography usage stats
        total_sequences = ClassPlanSequence.objects.filter(class_plan__instructor=request.user).count()
        
        # Get unique choreographies used
        unique_choreographies = ClassPlanSequence.objects.filter(
            class_plan__instructor=request.user
        ).values('choreography').distinct().count()
        
        # Calculate average sequences per plan
        avg_sequences = total_sequences / total_class_plans if total_class_plans > 0 else 0
        
        # Get recent activity (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_plans = class_plans.filter(created_at__gte=thirty_days_ago).count()
        
        # Get most used choreographies
        most_used = ClassPlanSequence.objects.filter(
            class_plan__instructor=request.user
        ).values(
            'choreography__id',
            'choreography__title',
            'choreography__difficulty'
        ).annotate(
            usage_count=Count('id')
        ).order_by('-usage_count')[:5]
        
        most_used_list = [
            {
                'choreography_id': str(item['choreography__id']),
                'title': item['choreography__title'],
                'difficulty': item['choreography__difficulty'],
                'usage_count': item['usage_count']
            }
            for item in most_used
        ]
        
        stats = {
            'total_class_plans': total_class_plans,
            'beginner_plans': beginner_plans,
            'intermediate_plans': intermediate_plans,
            'advanced_plans': advanced_plans,
            'total_sequences': total_sequences,
            'unique_choreographies_used': unique_choreographies,
            'avg_sequences_per_plan': round(avg_sequences, 1),
            'recent_plans_30_days': recent_plans,
            'most_used_choreographies': most_used_list
        }
        
        return JsonResponse(stats)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting dashboard stats for instructor {request.user.id}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to retrieve dashboard statistics'
        }, status=500)


@login_required
@require_instructor
@require_http_methods(["PUT"])
def sequence_update(request, pk, sequence_id):
    """
    Update sequence-specific details (notes and estimated time).
    
    FastAPI parity: PUT /instructor/class-plans/{id}/choreographies/{sequence_id}
    Updates the notes and/or estimated teaching time for a choreography in a class plan.
    """
    try:
        class_plan = get_object_or_404(
            ClassPlan,
            pk=pk,
            instructor=request.user
        )
        
        sequence = get_object_or_404(
            ClassPlanSequence,
            pk=sequence_id,
            class_plan=class_plan
        )
        
        # Parse request data
        data = json.loads(request.body)
        
        # Update fields if provided
        if 'notes' in data:
            sequence.notes = data['notes']
        
        if 'estimated_time' in data:
            try:
                estimated_time = int(data['estimated_time'])
                sequence.estimated_time = estimated_time if estimated_time >= 0 else None
            except (ValueError, TypeError):
                pass
        
        sequence.save()
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Sequence {sequence_id} updated in class plan {pk}")
        
        return JsonResponse({
            'success': True,
            'sequence_id': str(sequence.id),
            'notes': sequence.notes,
            'estimated_time': sequence.estimated_time
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating sequence {sequence_id} in class plan {pk}: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to update sequence'
        }, status=500)
