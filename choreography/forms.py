from django import forms
from .models import SavedChoreography
import logging

logger = logging.getLogger(__name__)


class ChoreographyGenerationForm(forms.Form):
    """Form for choreography generation with song selection and difficulty"""
    
    # Song choices will be populated dynamically
    SONG_CHOICES = [
        ('', 'Choose a song...'),
        ('new_song', 'New song (YouTube URL)'),
    ]
    
    @staticmethod
    def get_song_choices():
        """Dynamically load available songs from storage"""
        from core.services.audio_storage_service import AudioStorageService
        
        choices = [('', 'Choose a song...')]
        
        try:
            audio_storage = AudioStorageService()
            available_songs = audio_storage.list_songs()
            
            # Add each song as a choice (use just filename, not full path)
            for song in available_songs:
                # Create display name from filename (remove .mp3 and format)
                display_name = song.replace('.mp3', '').replace('_', ' ').title()
                choices.append((song, display_name))
            
            logger.info(f"Loaded {len(available_songs)} songs from storage")
        except Exception as e:
            logger.error(f"Failed to load songs from storage: {e}")
            # Fallback to hardcoded list if storage fails
            choices.extend([
                ('Amor.mp3', 'Amor'),
                ('Angel.mp3', 'Angel'),
                ('Aventura.mp3', 'Aventura'),
                ('Besito.mp3', 'Besito'),
                ('Bubalu.mp3', 'Bubalu'),
                ('Chayanne.mp3', 'Chayanne'),
                ('Corazoncandado.mp3', 'Corazón Candado'),
                ('Delmar.mp3', 'Del Mar'),
                ('Desnudate.mp3', 'Desnúdate'),
                ('Emborrachare.mp3', 'Emborracharé'),
                ('Nas.mp3', 'Nas'),
                ('Secreto.mp3', 'Secreto'),
                ('Suegra.mp3', 'Suegra'),
                ('Temevas.mp3', 'Te Me Vas'),
                ('Veneno.mp3', 'Veneno'),
            ])
        
        choices.append(('new_song', 'New song (YouTube URL)'))
        return choices
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    song_selection = forms.ChoiceField(
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all',
            'x-model': 'selectedSong',
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically load song choices
        self.fields['song_selection'].choices = self.get_song_choices()
    
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
