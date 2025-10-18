import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from instructors.models import ClassPlan, ClassPlanSequence
from choreography.models import SavedChoreography
import uuid

User = get_user_model()


@pytest.fixture
def instructor_user(db):
    """Create an instructor user"""
    return User.objects.create_user(
        username='instructor@example.com',
        email='instructor@example.com',
        password='testpass123',
        display_name='Test Instructor',
        is_instructor=True
    )


@pytest.fixture
def regular_user(db):
    """Create a regular (non-instructor) user"""
    return User.objects.create_user(
        username='user@example.com',
        email='user@example.com',
        password='testpass123',
        display_name='Regular User',
        is_instructor=False
    )


@pytest.fixture
def class_plan(instructor_user):
    """Create a test class plan"""
    return ClassPlan.objects.create(
        instructor=instructor_user,
        title='Test Class Plan',
        description='Test description',
        difficulty_level='intermediate',
        estimated_duration=60,
        instructor_notes='Test notes'
    )


@pytest.fixture
def choreography(instructor_user):
    """Create a test choreography"""
    return SavedChoreography.objects.create(
        user=instructor_user,
        title='Test Choreography',
        video_path='test.mp4',
        difficulty='intermediate',
        duration=120.0
    )


@pytest.mark.django_db
class TestInstructorDashboard:
    """Test instructor dashboard view"""
    
    def test_dashboard_requires_authentication(self, client):
        """Dashboard should redirect unauthenticated users to login"""
        response = client.get(reverse('instructors:dashboard'))
        assert response.status_code == 302
        assert '/auth/login/' in response.url
    
    def test_dashboard_requires_instructor_status(self, client, regular_user):
        """Dashboard should deny access to non-instructors"""
        client.force_login(regular_user)
        response = client.get(reverse('instructors:dashboard'))
        assert response.status_code == 403
    
    def test_dashboard_shows_class_plans(self, client, instructor_user, class_plan):
        """Dashboard should display instructor's class plans"""
        client.force_login(instructor_user)
        response = client.get(reverse('instructors:dashboard'))
        assert response.status_code == 200
        assert 'class_plans' in response.context
        assert class_plan in response.context['class_plans']
    
    def test_dashboard_filters_by_instructor(self, client, instructor_user, regular_user):
        """Dashboard should only show current instructor's class plans"""
        # Create class plan for another instructor
        other_instructor = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='testpass123',
            is_instructor=True
        )
        other_plan = ClassPlan.objects.create(
            instructor=other_instructor,
            title='Other Plan',
            difficulty_level='beginner'
        )
        
        # Create plan for current instructor
        my_plan = ClassPlan.objects.create(
            instructor=instructor_user,
            title='My Plan',
            difficulty_level='intermediate'
        )
        
        client.force_login(instructor_user)
        response = client.get(reverse('instructors:dashboard'))
        
        assert my_plan in response.context['class_plans']
        assert other_plan not in response.context['class_plans']


@pytest.mark.django_db
class TestClassPlanCreate:
    """Test class plan creation view"""
    
    def test_create_requires_authentication(self, client):
        """Create view should require authentication"""
        response = client.get(reverse('instructors:class_plan_create'))
        assert response.status_code == 302
    
    def test_create_requires_instructor_status(self, client, regular_user):
        """Create view should require instructor status"""
        client.force_login(regular_user)
        response = client.get(reverse('instructors:class_plan_create'))
        assert response.status_code == 403
    
    def test_create_get_shows_form(self, client, instructor_user):
        """GET request should show creation form"""
        client.force_login(instructor_user)
        response = client.get(reverse('instructors:class_plan_create'))
        assert response.status_code == 200
        assert 'form' in response.context
    
    def test_create_post_creates_class_plan(self, client, instructor_user):
        """POST request should create new class plan"""
        client.force_login(instructor_user)
        data = {
            'title': 'New Class Plan',
            'description': 'Test description',
            'difficulty_level': 'advanced',
            'estimated_duration': 90,
            'instructor_notes': 'Test notes'
        }
        response = client.post(reverse('instructors:class_plan_create'), data)
        
        # Should redirect to detail page
        assert response.status_code == 302
        
        # Verify class plan was created
        class_plan = ClassPlan.objects.get(title='New Class Plan')
        assert class_plan.instructor == instructor_user
        assert class_plan.difficulty_level == 'advanced'
        assert class_plan.estimated_duration == 90
    
    def test_create_post_invalid_data(self, client, instructor_user):
        """POST with invalid data should show form with errors"""
        client.force_login(instructor_user)
        data = {
            'title': '',  # Required field
            'difficulty_level': 'intermediate'
        }
        response = client.post(reverse('instructors:class_plan_create'), data)
        
        # Should show form again
        assert response.status_code == 200
        assert 'form' in response.context
        assert not response.context['form'].is_valid()


@pytest.mark.django_db
class TestClassPlanDetail:
    """Test class plan detail view"""
    
    def test_detail_requires_authentication(self, client, class_plan):
        """Detail view should require authentication"""
        response = client.get(reverse('instructors:class_plan_detail', kwargs={'pk': class_plan.id}))
        assert response.status_code == 302
    
    def test_detail_requires_instructor_status(self, client, regular_user, class_plan):
        """Detail view should require instructor status"""
        client.force_login(regular_user)
        response = client.get(reverse('instructors:class_plan_detail', kwargs={'pk': class_plan.id}))
        assert response.status_code == 403
    
    def test_detail_shows_class_plan(self, client, instructor_user, class_plan):
        """Detail view should display class plan information"""
        client.force_login(instructor_user)
        response = client.get(reverse('instructors:class_plan_detail', kwargs={'pk': class_plan.id}))
        
        assert response.status_code == 200
        assert response.context['class_plan'] == class_plan
    
    def test_detail_shows_sequences(self, client, instructor_user, class_plan, choreography):
        """Detail view should display sequences"""
        # Add sequence
        sequence = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=choreography,
            sequence_order=1,
            notes='Test sequence'
        )
        
        client.force_login(instructor_user)
        response = client.get(reverse('instructors:class_plan_detail', kwargs={'pk': class_plan.id}))
        
        assert sequence in response.context['sequences']
    
    def test_detail_only_shows_own_class_plan(self, client, instructor_user):
        """Detail view should return 404 for other instructor's plans"""
        other_instructor = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='testpass123',
            is_instructor=True
        )
        other_plan = ClassPlan.objects.create(
            instructor=other_instructor,
            title='Other Plan',
            difficulty_level='beginner'
        )
        
        client.force_login(instructor_user)
        response = client.get(reverse('instructors:class_plan_detail', kwargs={'pk': other_plan.id}))
        assert response.status_code == 404


@pytest.mark.django_db
class TestClassPlanEdit:
    """Test class plan edit view"""
    
    def test_edit_requires_authentication(self, client, class_plan):
        """Edit view should require authentication"""
        response = client.get(reverse('instructors:class_plan_edit', kwargs={'pk': class_plan.id}))
        assert response.status_code == 302
    
    def test_edit_requires_instructor_status(self, client, regular_user, class_plan):
        """Edit view should require instructor status"""
        client.force_login(regular_user)
        response = client.get(reverse('instructors:class_plan_edit', kwargs={'pk': class_plan.id}))
        assert response.status_code == 403
    
    def test_edit_get_shows_form(self, client, instructor_user, class_plan):
        """GET request should show edit form with existing data"""
        client.force_login(instructor_user)
        response = client.get(reverse('instructors:class_plan_edit', kwargs={'pk': class_plan.id}))
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['class_plan'] == class_plan
        assert response.context['is_edit'] is True
    
    def test_edit_post_updates_class_plan(self, client, instructor_user, class_plan):
        """POST request should update class plan"""
        client.force_login(instructor_user)
        data = {
            'title': 'Updated Title',
            'description': 'Updated description',
            'difficulty_level': 'advanced',
            'estimated_duration': 120,
            'instructor_notes': 'Updated notes'
        }
        response = client.post(reverse('instructors:class_plan_edit', kwargs={'pk': class_plan.id}), data)
        
        # Should redirect to detail page
        assert response.status_code == 302
        
        # Verify updates
        class_plan.refresh_from_db()
        assert class_plan.title == 'Updated Title'
        assert class_plan.difficulty_level == 'advanced'
        assert class_plan.estimated_duration == 120


@pytest.mark.django_db
class TestClassPlanDelete:
    """Test class plan delete view"""
    
    def test_delete_requires_authentication(self, client, class_plan):
        """Delete view should require authentication"""
        response = client.post(reverse('instructors:class_plan_delete', kwargs={'pk': class_plan.id}))
        assert response.status_code == 302
    
    def test_delete_requires_instructor_status(self, client, regular_user, class_plan):
        """Delete view should require instructor status"""
        client.force_login(regular_user)
        response = client.post(reverse('instructors:class_plan_delete', kwargs={'pk': class_plan.id}))
        assert response.status_code == 403
    
    def test_delete_removes_class_plan(self, client, instructor_user, class_plan):
        """POST request should delete class plan"""
        client.force_login(instructor_user)
        class_plan_id = class_plan.id
        
        response = client.post(reverse('instructors:class_plan_delete', kwargs={'pk': class_plan.id}))
        
        # Should redirect to dashboard
        assert response.status_code == 302
        
        # Verify deletion
        assert not ClassPlan.objects.filter(id=class_plan_id).exists()
    
    def test_delete_only_own_class_plan(self, client, instructor_user):
        """Delete should return 404 for other instructor's plans"""
        other_instructor = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='testpass123',
            is_instructor=True
        )
        other_plan = ClassPlan.objects.create(
            instructor=other_instructor,
            title='Other Plan',
            difficulty_level='beginner'
        )
        
        client.force_login(instructor_user)
        response = client.post(reverse('instructors:class_plan_delete', kwargs={'pk': other_plan.id}))
        assert response.status_code == 404


@pytest.mark.django_db
class TestSequenceManagement:
    """Test sequence add/delete/reorder views"""
    
    def test_sequence_add_requires_authentication(self, client, class_plan):
        """Sequence add should require authentication"""
        response = client.post(reverse('instructors:sequence_add', kwargs={'pk': class_plan.id}))
        assert response.status_code == 302
    
    def test_sequence_add_creates_sequence(self, client, instructor_user, class_plan, choreography):
        """POST should add choreography to class plan"""
        client.force_login(instructor_user)
        data = {
            'choreography_id': str(choreography.id),
            'notes': 'Test sequence notes',
            'estimated_time': 15
        }
        response = client.post(reverse('instructors:sequence_add', kwargs={'pk': class_plan.id}), data)
        
        # Should redirect or return JSON
        assert response.status_code in [200, 302]
        
        # Verify sequence was created
        sequence = ClassPlanSequence.objects.get(class_plan=class_plan, choreography=choreography)
        assert sequence.notes == 'Test sequence notes'
        assert sequence.estimated_time == 15
    
    def test_sequence_delete_removes_sequence(self, client, instructor_user, class_plan, choreography):
        """POST should remove sequence from class plan"""
        # Create sequence
        sequence = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=choreography,
            sequence_order=1
        )
        
        client.force_login(instructor_user)
        response = client.post(
            reverse('instructors:sequence_delete', kwargs={'pk': class_plan.id, 'sequence_id': sequence.id})
        )
        
        # Should redirect or return JSON
        assert response.status_code in [200, 302]
        
        # Verify deletion
        assert not ClassPlanSequence.objects.filter(id=sequence.id).exists()
    
    def test_sequence_reorder_updates_order(self, client, instructor_user, class_plan):
        """POST should reorder sequences"""
        # Create multiple choreographies and sequences
        choreo1 = SavedChoreography.objects.create(
            user=instructor_user,
            title='Choreo 1',
            video_path='test1.mp4',
            difficulty='beginner',
            duration=60.0
        )
        choreo2 = SavedChoreography.objects.create(
            user=instructor_user,
            title='Choreo 2',
            video_path='test2.mp4',
            difficulty='intermediate',
            duration=90.0
        )
        
        seq1 = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=choreo1,
            sequence_order=1
        )
        seq2 = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=choreo2,
            sequence_order=2
        )
        
        client.force_login(instructor_user)
        
        # Reorder: swap seq1 and seq2
        import json
        data = json.dumps({
            'sequence_ids': [str(seq2.id), str(seq1.id)]
        })
        response = client.post(
            reverse('instructors:sequence_reorder', kwargs={'pk': class_plan.id}),
            data=data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Verify new order
        seq1.refresh_from_db()
        seq2.refresh_from_db()
        assert seq2.sequence_order == 1
        assert seq1.sequence_order == 2
