from django import forms
from .models import SavedChoreography


class ChoreographyGenerationForm(forms.Form):
    """Form for choreography generation with song selection and difficulty"""
    
    # Song choices - all available songs plus option for new YouTube URL
    SONG_CHOICES = [
        ('', 'Choose a song...'),
        ('data/songs/Amor.mp3', 'Amor'),
        ('data/songs/Angel.mp3', 'Angel'),
        ('data/songs/Aventura.mp3', 'Aventura'),
        ('data/songs/Besito.mp3', 'Besito'),
        ('data/songs/Bubalu.mp3', 'Bubalu'),
        ('data/songs/Chayanne.mp3', 'Chayanne'),
        ('data/songs/Corazoncandado.mp3', 'Corazón Candado'),
        ('data/songs/Delmar.mp3', 'Del Mar'),
        ('data/songs/Desnudate.mp3', 'Desnúdate'),
        ('data/songs/Emborrachare.mp3', 'Emborracharé'),
        ('data/songs/Nas.mp3', 'Nas'),
        ('data/songs/Secreto.mp3', 'Secreto'),
        ('data/songs/Suegra.mp3', 'Suegra'),
        ('data/songs/Temevas.mp3', 'Te Me Vas'),
        ('data/songs/Veneno.mp3', 'Veneno'),
        ('new_song', 'New song (YouTube URL)'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    song_selection = forms.ChoiceField(
        choices=SONG_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all',
            'x-model': 'selectedSong',
        })
    )
    
    youtube_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all',
            'x-model': 'youtubeUrl',
            'x-show': "selectedSong === 'new_song'",
            'placeholder': 'Enter YouTube URL...',
        })
    )
    
    difficulty = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        initial='intermediate',
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all',
            'x-model': 'difficulty',
        })
    )
    
    def clean(self):
        """Validate that youtube_url is provided when song_selection is 'new_song'"""
        cleaned_data = super().clean()
        song_selection = cleaned_data.get('song_selection')
        youtube_url = cleaned_data.get('youtube_url')
        
        if song_selection == 'new_song' and not youtube_url:
            raise forms.ValidationError(
                'YouTube URL is required when selecting "New song (YouTube URL)"'
            )
        
        return cleaned_data


class SaveChoreographyForm(forms.ModelForm):
    """Form for saving generated choreography to user's collection"""
    
    class Meta:
        model = SavedChoreography
        fields = ['title', 'difficulty']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all',
                'placeholder': 'Enter choreography title...',
            }),
            'difficulty': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all',
            }),
        }
