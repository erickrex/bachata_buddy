from django.contrib import admin
from .models import ClassPlan, ClassPlanSequence


class ClassPlanSequenceInline(admin.TabularInline):
    """Inline admin for ClassPlanSequence"""
    model = ClassPlanSequence
    extra = 1
    fields = ['choreography', 'sequence_order', 'notes', 'estimated_time']
    ordering = ['sequence_order']


@admin.register(ClassPlan)
class ClassPlanAdmin(admin.ModelAdmin):
    """Admin interface for ClassPlan model"""
    
    list_display = ['title', 'instructor', 'difficulty_level', 'estimated_duration', 'created_at']
    list_filter = ['difficulty_level', 'created_at']
    search_fields = ['title', 'instructor__email', 'description']
    inlines = [ClassPlanSequenceInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('instructor', 'title', 'description', 'difficulty_level')
        }),
        ('Planning', {
            'fields': ('estimated_duration', 'instructor_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
