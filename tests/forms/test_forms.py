import pytest
from choreography.forms import ChoreographyGenerationForm, SaveChoreographyForm
from choreography.models import SavedChoreography


@pytest.mark.django_db
class TestChoreographyGenerationForm:
    """Tests for ChoreographyGenerationForm"""
    
    def test_valid_form_with_local_song(self):
        """Test form is valid with local song selection"""
        form_data = {
            'song_selection': 'Amor.mp3',
            'difficulty': 'intermediate',
        }
        form = ChoreographyGenerationForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['song_selection'] == 'Amor.mp3'
        assert form.cleaned_data['difficulty'] == 'intermediate'
    
    def test_valid_form_with_different_song(self):
        """Test form is valid with different song selection"""
        form_data = {
            'song_selection': 'Veneno.mp3',
            'difficulty': 'beginner',
        }
        form = ChoreographyGenerationForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['song_selection'] == 'Veneno.mp3'
    
    def test_invalid_form_invalid_song(self):
        """Test form is invalid with non-existent song"""
        form_data = {
            'song_selection': 'nonexistent.mp3',
            'difficulty': 'advanced',
        }
        form = ChoreographyGenerationForm(data=form_data)
        assert not form.is_valid()
        assert 'song_selection' in form.errors
    
    def test_invalid_form_missing_song_selection(self):
        """Test form is invalid without song selection"""
        form_data = {
            'difficulty': 'intermediate',
        }
        form = ChoreographyGenerationForm(data=form_data)
        assert not form.is_valid()
        assert 'song_selection' in form.errors
    
    def test_invalid_form_missing_difficulty(self):
        """Test form is invalid without difficulty"""
        form_data = {
            'song_selection': 'data/songs/Amor.mp3',
        }
        form = ChoreographyGenerationForm(data=form_data)
        assert not form.is_valid()
        assert 'difficulty' in form.errors
    
    def test_form_has_all_songs(self):
        """Test form includes all available songs"""
        form = ChoreographyGenerationForm()
        song_choices = dict(form.fields['song_selection'].choices)
        
        # Check some key songs are present (using new format without path)
        assert 'Amor.mp3' in song_choices
        assert 'Veneno.mp3' in song_choices
        # Empty choice for "Choose a song..."
        assert '' in song_choices
    
    def test_form_difficulty_default(self):
        """Test difficulty field has correct default"""
        form = ChoreographyGenerationForm()
        assert form.fields['difficulty'].initial == 'intermediate'
    
    def test_form_widgets_have_alpine_attributes(self):
        """Test form widgets include Alpine.js attributes"""
        form = ChoreographyGenerationForm()
        
        # Check song_selection has x-model
        song_widget_attrs = form.fields['song_selection'].widget.attrs
        assert 'x-model' in song_widget_attrs
        assert song_widget_attrs['x-model'] == 'selectedSong'
        
        # Check difficulty has x-model
        difficulty_widget_attrs = form.fields['difficulty'].widget.attrs
        assert 'x-model' in difficulty_widget_attrs
        assert difficulty_widget_attrs['x-model'] == 'difficulty'
    
    def test_form_widgets_have_tailwind_classes(self):
        """Test form widgets include Tailwind CSS classes"""
        form = ChoreographyGenerationForm()
        
        for field_name in ['song_selection', 'difficulty']:
            widget_attrs = form.fields[field_name].widget.attrs
            assert 'class' in widget_attrs
            assert 'w-full' in widget_attrs['class']
            assert 'rounded-xl' in widget_attrs['class']


@pytest.mark.django_db
class TestSaveChoreographyForm:
    """Tests for SaveChoreographyForm"""
    
    def test_valid_form(self):
        """Test form is valid with correct data"""
        form_data = {
            'title': 'My Awesome Choreography',
            'difficulty': 'intermediate',
        }
        form = SaveChoreographyForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['title'] == 'My Awesome Choreography'
        assert form.cleaned_data['difficulty'] == 'intermediate'
    
    def test_invalid_form_missing_title(self):
        """Test form is invalid without title"""
        form_data = {
            'difficulty': 'beginner',
        }
        form = SaveChoreographyForm(data=form_data)
        assert not form.is_valid()
        assert 'title' in form.errors
    
    def test_invalid_form_missing_difficulty(self):
        """Test form is invalid without difficulty"""
        form_data = {
            'title': 'Test Choreography',
        }
        form = SaveChoreographyForm(data=form_data)
        assert not form.is_valid()
        assert 'difficulty' in form.errors
    
    def test_invalid_form_invalid_difficulty(self):
        """Test form is invalid with invalid difficulty choice"""
        form_data = {
            'title': 'Test Choreography',
            'difficulty': 'expert',  # Not a valid choice
        }
        form = SaveChoreographyForm(data=form_data)
        assert not form.is_valid()
        assert 'difficulty' in form.errors
    
    def test_form_is_modelform(self):
        """Test form is a ModelForm for SavedChoreography"""
        form = SaveChoreographyForm()
        assert form._meta.model == SavedChoreography
        assert 'title' in form._meta.fields
        assert 'difficulty' in form._meta.fields
    
    def test_form_widgets_have_tailwind_classes(self):
        """Test form widgets include Tailwind CSS classes"""
        form = SaveChoreographyForm()
        
        for field_name in ['title', 'difficulty']:
            widget_attrs = form.fields[field_name].widget.attrs
            assert 'class' in widget_attrs
            assert 'w-full' in widget_attrs['class']
            assert 'rounded-xl' in widget_attrs['class']
    
    def test_form_save_creates_choreography(self, test_user):
        """Test form save creates SavedChoreography instance"""
        form_data = {
            'title': 'Test Save',
            'difficulty': 'advanced',
        }
        form = SaveChoreographyForm(data=form_data)
        assert form.is_valid()
        
        # Save without committing to add user
        choreography = form.save(commit=False)
        choreography.user = test_user
        choreography.video_path = 'test.mp4'
        choreography.duration = 120.0
        choreography.save()
        
        # Verify it was saved
        assert SavedChoreography.objects.filter(title='Test Save').exists()
        saved = SavedChoreography.objects.get(title='Test Save')
        assert saved.difficulty == 'advanced'
        assert saved.user == test_user
