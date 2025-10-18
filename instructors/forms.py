from django import forms
from .models import ClassPlan, ClassPlanSequence


class ClassPlanForm(forms.ModelForm):
    """Form for creating and editing class plans"""
    
    class Meta:
        model = ClassPlan
        fields = ['title', 'description', 'difficulty_level', 'estimated_duration', 'instructor_notes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-colors',
                'placeholder': 'Enter class plan title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-colors',
                'rows': 4,
                'placeholder': 'Describe the class plan'
            }),
            'difficulty_level': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-colors'
            }),
            'estimated_duration': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-colors',
                'placeholder': 'Duration in minutes',
                'min': 1
            }),
            'instructor_notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-colors',
                'rows': 4,
                'placeholder': 'Private notes for yourself'
            }),
        }


class ClassPlanSequenceForm(forms.ModelForm):
    """Form for adding choreographies to class plan sequences"""
    
    class Meta:
        model = ClassPlanSequence
        fields = ['choreography', 'notes', 'estimated_time']
        widgets = {
            'choreography': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-colors'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-colors',
                'rows': 3,
                'placeholder': 'Notes for this sequence'
            }),
            'estimated_time': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:outline-none transition-colors',
                'placeholder': 'Time in minutes',
                'min': 1
            }),
        }
