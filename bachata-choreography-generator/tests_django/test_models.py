"""
Django model tests.

Tests for:
- User model (custom user with display_name, is_instructor)
- SavedChoreography model
- ClassPlan and ClassPlanSequence models

Reference: tests/test_*.py (FastAPI model tests)
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.models
class TestUserModel:
    """Test the custom User model."""
    
    def test_create_user_with_display_name(self):
        """Test creating a user with display_name."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.display_name == 'Test User'
        assert user.is_instructor is False
        assert user.check_password('testpass123')
        assert user.is_active is True
    
    def test_create_user_with_is_instructor(self):
        """Test creating a user with is_instructor flag."""
        user = User.objects.create_user(
            username='instructor',
            email='instructor@example.com',
            password='testpass123',
            display_name='Test Instructor',
            is_instructor=True
        )
        
        assert user.is_instructor is True
        assert user.display_name == 'Test Instructor'
    
    def test_create_user_with_preferences(self):
        """Test creating a user with custom preferences."""
        preferences = {
            'theme': 'dark',
            'auto_save': True,
            'notifications': False
        }
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            preferences=preferences
        )
        
        assert user.preferences == preferences
        assert user.preferences['theme'] == 'dark'
        assert user.preferences['auto_save'] is True
    
    def test_user_string_representation_with_display_name(self):
        """Test user __str__ method returns display_name when set."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
        
        # Should return display_name
        assert str(user) == 'Test User'
    
    def test_user_string_representation_without_display_name(self):
        """Test user __str__ method returns username when display_name is empty."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name=''
        )
        
        # Should return username when display_name is empty
        assert str(user) == 'testuser'
    
    def test_user_preferences_default_value(self):
        """Test user preferences JSONField has default empty dict."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Should have default empty dict
        assert user.preferences is not None
        assert isinstance(user.preferences, dict)
        assert user.preferences == {}


@pytest.mark.django_db
@pytest.mark.models
class TestSavedChoreographyModel:
    """Test the SavedChoreography model."""
    
    def test_create_choreography_with_all_fields(self, test_user):
        """Test creating a saved choreography with all fields."""
        from choreography.models import SavedChoreography
        
        music_info = {
            'title': 'Test Song',
            'artist': 'Test Artist',
            'tempo': 120,
            'genre': 'Bachata'
        }
        generation_params = {
            'difficulty': 'intermediate',
            'song_selection': 'test_song',
            'youtube_url': None
        }
        
        choreography = SavedChoreography.objects.create(
            user=test_user,
            title='Test Choreography',
            video_path='data/output/test_video.mp4',
            thumbnail_path='data/output/test_thumbnail.jpg',
            difficulty='intermediate',
            duration=180.5,
            music_info=music_info,
            generation_parameters=generation_params
        )
        
        # Verify all fields
        assert choreography.title == 'Test Choreography'
        assert choreography.user == test_user
        assert choreography.video_path == 'data/output/test_video.mp4'
        assert choreography.thumbnail_path == 'data/output/test_thumbnail.jpg'
        assert choreography.difficulty == 'intermediate'
        assert choreography.duration == 180.5
        assert choreography.music_info == music_info
        assert choreography.generation_parameters == generation_params
        assert choreography.created_at is not None
        # UUID should be auto-generated
        assert choreography.id is not None
    
    def test_choreography_string_representation(self, test_user):
        """Test choreography __str__ method returns title and difficulty."""
        from choreography.models import SavedChoreography
        
        choreography = SavedChoreography.objects.create(
            user=test_user,
            title='Test Choreography',
            video_path='data/output/test_video.mp4',
            difficulty='intermediate',
            duration=180.5
        )
        
        # Should include both title and difficulty
        str_repr = str(choreography)
        assert 'Test Choreography' in str_repr
        assert 'intermediate' in str_repr
        assert str_repr == 'Test Choreography (intermediate)'
    
    def test_choreography_ordering_by_created_at_descending(self, test_user):
        """Test choreographies are ordered by created_at descending (newest first)."""
        from choreography.models import SavedChoreography
        import time
        
        # Create three choreographies with time differences
        choreo1 = SavedChoreography.objects.create(
            user=test_user,
            title='First',
            video_path='data/output/test1.mp4',
            difficulty='beginner',
            duration=120.0
        )
        
        time.sleep(0.1)
        
        choreo2 = SavedChoreography.objects.create(
            user=test_user,
            title='Second',
            video_path='data/output/test2.mp4',
            difficulty='intermediate',
            duration=150.0
        )
        
        time.sleep(0.1)
        
        choreo3 = SavedChoreography.objects.create(
            user=test_user,
            title='Third',
            video_path='data/output/test3.mp4',
            difficulty='advanced',
            duration=180.0
        )
        
        # Get all choreographies (should be ordered by created_at descending)
        choreographies = list(SavedChoreography.objects.all())
        
        # Most recent should be first
        assert choreographies[0].title == 'Third'
        assert choreographies[1].title == 'Second'
        assert choreographies[2].title == 'First'
        
        # Verify created_at ordering
        assert choreographies[0].created_at > choreographies[1].created_at
        assert choreographies[1].created_at > choreographies[2].created_at
    
    def test_choreography_user_relationship(self, test_user):
        """Test choreography-user relationship (forward and reverse)."""
        from choreography.models import SavedChoreography
        
        choreography = SavedChoreography.objects.create(
            user=test_user,
            title='Test Choreography',
            video_path='data/output/test_video.mp4',
            difficulty='intermediate',
            duration=180.5
        )
        
        # Test forward relationship (choreography -> user)
        assert choreography.user == test_user
        assert choreography.user.username == test_user.username
        
        # Test reverse relationship (user -> choreographies)
        assert choreography in test_user.choreographies.all()
        assert test_user.choreographies.count() == 1
        assert test_user.choreographies.first() == choreography
    
    def test_choreography_cascade_delete_with_user(self, test_user):
        """Test that choreographies are deleted when user is deleted."""
        from choreography.models import SavedChoreography
        
        choreography = SavedChoreography.objects.create(
            user=test_user,
            title='Test Choreography',
            video_path='data/output/test_video.mp4',
            difficulty='intermediate',
            duration=180.5
        )
        
        choreography_id = choreography.id
        
        # Delete the user
        test_user.delete()
        
        # Choreography should also be deleted (CASCADE)
        assert not SavedChoreography.objects.filter(id=choreography_id).exists()


@pytest.mark.django_db
@pytest.mark.models
class TestClassPlanModels:
    """Test ClassPlan and ClassPlanSequence models."""
    
    def test_create_class_plan_with_all_fields(self, test_instructor):
        """Test creating a class plan with all fields."""
        from instructors.models import ClassPlan
        
        class_plan = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Beginner Bachata Class',
            description='Introduction to Bachata basics',
            difficulty_level='beginner',
            estimated_duration=60,
            instructor_notes='Focus on basic steps and timing'
        )
        
        # Verify all fields
        assert class_plan.title == 'Beginner Bachata Class'
        assert class_plan.instructor == test_instructor
        assert class_plan.description == 'Introduction to Bachata basics'
        assert class_plan.difficulty_level == 'beginner'
        assert class_plan.estimated_duration == 60
        assert class_plan.instructor_notes == 'Focus on basic steps and timing'
        assert class_plan.created_at is not None
        assert class_plan.updated_at is not None
        # UUID should be auto-generated
        assert class_plan.id is not None
    
    def test_class_plan_string_representation(self, test_instructor):
        """Test class plan __str__ method."""
        from instructors.models import ClassPlan
        
        class_plan = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Test Class',
            difficulty_level='intermediate',
            estimated_duration=60
        )
        
        # Should include title and instructor display name
        str_repr = str(class_plan)
        assert 'Test Class' in str_repr
        assert 'by' in str_repr
        # Should include instructor's display_name or username
        assert test_instructor.display_name in str_repr or test_instructor.username in str_repr
    
    def test_class_plan_instructor_relationship_with_is_instructor(self, test_instructor, test_user):
        """Test class plan-instructor relationship with is_instructor limit."""
        from instructors.models import ClassPlan
        
        # Create class plan with instructor
        class_plan = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Test Class',
            difficulty_level='intermediate',
            estimated_duration=60
        )
        
        # Test forward relationship
        assert class_plan.instructor == test_instructor
        assert class_plan.instructor.is_instructor is True
        
        # Test reverse relationship
        assert class_plan in test_instructor.class_plans.all()
        assert test_instructor.class_plans.count() == 1
        
        # Note: limit_choices_to is enforced at the form/admin level, not database level
        # So we can technically create a class plan with a non-instructor user in tests
        # but in production, forms would prevent this
    
    def test_class_plan_ordering_by_created_at_descending(self, test_instructor):
        """Test class plans are ordered by created_at descending."""
        from instructors.models import ClassPlan
        import time
        
        # Create three class plans
        plan1 = ClassPlan.objects.create(
            instructor=test_instructor,
            title='First Plan',
            difficulty_level='beginner',
            estimated_duration=45
        )
        
        time.sleep(0.1)
        
        plan2 = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Second Plan',
            difficulty_level='intermediate',
            estimated_duration=60
        )
        
        time.sleep(0.1)
        
        plan3 = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Third Plan',
            difficulty_level='advanced',
            estimated_duration=75
        )
        
        # Get all class plans
        plans = list(ClassPlan.objects.all())
        
        # Most recent should be first
        assert plans[0].title == 'Third Plan'
        assert plans[1].title == 'Second Plan'
        assert plans[2].title == 'First Plan'
    
    def test_create_class_plan_sequence(self, test_instructor, test_choreography):
        """Test creating a class plan sequence."""
        from instructors.models import ClassPlan, ClassPlanSequence
        
        class_plan = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Test Class',
            difficulty_level='intermediate',
            estimated_duration=60
        )
        
        sequence = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=test_choreography,
            sequence_order=1,
            notes='Warm-up sequence',
            estimated_time=15
        )
        
        # Verify all fields
        assert sequence.class_plan == class_plan
        assert sequence.choreography == test_choreography
        assert sequence.sequence_order == 1
        assert sequence.notes == 'Warm-up sequence'
        assert sequence.estimated_time == 15
        assert sequence.id is not None
    
    def test_class_plan_sequence_relationship(self, test_instructor, test_choreography):
        """Test ClassPlanSequence relationships with ClassPlan and SavedChoreography."""
        from instructors.models import ClassPlan, ClassPlanSequence
        
        class_plan = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Test Class',
            difficulty_level='intermediate',
            estimated_duration=60
        )
        
        sequence = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=test_choreography,
            sequence_order=1
        )
        
        # Test forward relationships
        assert sequence.class_plan == class_plan
        assert sequence.choreography == test_choreography
        
        # Test reverse relationships
        assert sequence in class_plan.sequences.all()
        assert sequence in test_choreography.class_sequences.all()
    
    def test_class_plan_sequence_ordering_by_sequence_order(self, test_instructor, test_choreography):
        """Test class plan sequences are ordered by sequence_order."""
        from instructors.models import ClassPlan, ClassPlanSequence
        
        class_plan = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Test Class',
            difficulty_level='intermediate',
            estimated_duration=60
        )
        
        # Create sequences out of order
        seq3 = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=test_choreography,
            sequence_order=3,
            notes='Cool down'
        )
        
        seq1 = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=test_choreography,
            sequence_order=1,
            notes='Warm up'
        )
        
        seq2 = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=test_choreography,
            sequence_order=2,
            notes='Main practice'
        )
        
        # Get sequences (should be ordered by sequence_order)
        sequences = list(class_plan.sequences.all())
        
        # Should be ordered by sequence_order ascending
        assert sequences[0].sequence_order == 1
        assert sequences[0].notes == 'Warm up'
        assert sequences[1].sequence_order == 2
        assert sequences[1].notes == 'Main practice'
        assert sequences[2].sequence_order == 3
        assert sequences[2].notes == 'Cool down'
    
    def test_class_plan_cascade_delete(self, test_instructor, test_choreography):
        """Test that sequences are deleted when class plan is deleted."""
        from instructors.models import ClassPlan, ClassPlanSequence
        
        class_plan = ClassPlan.objects.create(
            instructor=test_instructor,
            title='Test Class',
            difficulty_level='intermediate',
            estimated_duration=60
        )
        
        sequence = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=test_choreography,
            sequence_order=1
        )
        
        sequence_id = sequence.id
        
        # Delete the class plan
        class_plan.delete()
        
        # Sequence should also be deleted (CASCADE)
        assert not ClassPlanSequence.objects.filter(id=sequence_id).exists()
