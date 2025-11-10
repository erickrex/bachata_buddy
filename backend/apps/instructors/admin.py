from django.contrib import admin
from .models import ClassPlan, ClassPlanSequence


class ClassPlanSequenceInline(admin.TabularInline):
    model = ClassPlanSequence
    extra = 0
    fields = ['sequence_order', 'choreography', 'notes', 'estimated_time']
    ordering = ['sequence_order']


@admin.register(ClassPlan)
class ClassPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'instructor', 'difficulty_level', 'estimated_duration', 'created_at']
    list_filter = ['difficulty_level', 'created_at']
    search_fields = ['title', 'instructor__username', 'instructor__display_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ClassPlanSequenceInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'instructor', 'title', 'description', 'difficulty_level')
        }),
        ('Planning Details', {
            'fields': ('estimated_duration', 'instructor_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ClassPlanSequence)
class ClassPlanSequenceAdmin(admin.ModelAdmin):
    list_display = ['class_plan', 'sequence_order', 'choreography', 'estimated_time']
    list_filter = ['class_plan__difficulty_level']
    search_fields = ['class_plan__title', 'choreography__title']
    readonly_fields = ['id']
    ordering = ['class_plan', 'sequence_order']
