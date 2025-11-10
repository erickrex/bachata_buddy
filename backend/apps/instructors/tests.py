from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import ClassPlan, ClassPlanSequence
from apps.collections.models import SavedChoreography
import uuid

User = get_user_model()


class ClassPlanTests(TestCase):
    """Test suite for class plan endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create instructor user
        self.instructor = User.objects.create_user(
            username='instructor1',
            email='instructor@test.com',
            password='testpass123',
            is_instructor=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular1',
            email='regular@test.com',
            password='testpass123',
            is_instructor=False
        )
        
        # Create test choreography
        self.choreography = SavedChoreography.objects.create(
            user=self.instructor,
            title='Test Choreography',
            video_path='test/video.mp4',
            difficulty='beginner',
            duration=30.5
        )
    
    def test_create_class_plan_as_instructor(self):
        """Test instructor can create class plan"""
        self.client.force_authenticate(user=self.instructor)
        
        data = {
            'title': 'Beginner Basics',
            'description': 'Introduction to bachata',
            'difficulty_level': 'beginner',
            'estimated_duration': 60,
            'instructor_notes': 'Focus on basic steps'
        }
        
        response = self.client.post('/api/instructors/class-plans/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Beginner Basics')
        self.assertEqual(response.data['sequence_count'], 0)
    
    def test_create_class_plan_as_regular_user(self):
        """Test regular user cannot create class plan"""
        self.client.force_authenticate(user=self.regular_user)
        
        data = {
            'title': 'Beginner Basics',
            'difficulty_level': 'beginner'
        }
        
        response = self.client.post('/api/instructors/class-plans/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_class_plans(self):
        """Test listing class plans returns only instructor's plans"""
        self.client.force_authenticate(user=self.instructor)
        
        # Create class plans
        ClassPlan.objects.create(
            instructor=self.instructor,
            title='Plan 1',
            difficulty_level='beginner'
        )
        ClassPlan.objects.create(
            instructor=self.instructor,
            title='Plan 2',
            difficulty_level='intermediate'
        )
        
        response = self.client.get('/api/instructors/class-plans/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_filter_by_difficulty(self):
        """Test filtering class plans by difficulty"""
        self.client.force_authenticate(user=self.instructor)
        
        ClassPlan.objects.create(
            instructor=self.instructor,
            title='Beginner Plan',
            difficulty_level='beginner'
        )
        ClassPlan.objects.create(
            instructor=self.instructor,
            title='Advanced Plan',
            difficulty_level='advanced'
        )
        
        response = self.client.get('/api/instructors/class-plans/?difficulty_level=beginner')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Beginner Plan')
    
    def test_add_sequence_to_class_plan(self):
        """Test adding choreography to class plan"""
        self.client.force_authenticate(user=self.instructor)
        
        class_plan = ClassPlan.objects.create(
            instructor=self.instructor,
            title='Test Plan',
            difficulty_level='beginner'
        )
        
        data = {
            'choreography_id': str(self.choreography.id),
            'notes': 'Practice slowly',
            'estimated_time': 10
        }
        
        response = self.client.post(
            f'/api/instructors/class-plans/{class_plan.id}/sequences/',
            data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sequence_order'], 0)
        self.assertEqual(response.data['notes'], 'Practice slowly')
    
    def test_reorder_sequences(self):
        """Test reordering sequences in class plan"""
        self.client.force_authenticate(user=self.instructor)
        
        class_plan = ClassPlan.objects.create(
            instructor=self.instructor,
            title='Test Plan',
            difficulty_level='beginner'
        )
        
        # Create sequences
        seq1 = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=self.choreography,
            sequence_order=0
        )
        seq2 = ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=self.choreography,
            sequence_order=1
        )
        
        # Reorder
        data = {
            'sequence_ids': [str(seq2.id), str(seq1.id)]
        }
        
        response = self.client.post(
            f'/api/instructors/class-plans/{class_plan.id}/reorder-sequences/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sequences'][0]['id'], str(seq2.id))
        self.assertEqual(response.data['sequences'][0]['sequence_order'], 0)
    
    def test_duplicate_class_plan(self):
        """Test duplicating class plan with sequences"""
        self.client.force_authenticate(user=self.instructor)
        
        class_plan = ClassPlan.objects.create(
            instructor=self.instructor,
            title='Original Plan',
            difficulty_level='beginner'
        )
        
        ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=self.choreography,
            sequence_order=0
        )
        
        response = self.client.post(
            f'/api/instructors/class-plans/{class_plan.id}/duplicate/'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Original Plan (Copy)')
        self.assertEqual(len(response.data['sequences']), 1)
    
    def test_class_plan_summary(self):
        """Test generating class plan summary"""
        self.client.force_authenticate(user=self.instructor)
        
        class_plan = ClassPlan.objects.create(
            instructor=self.instructor,
            title='Test Plan',
            difficulty_level='beginner'
        )
        
        ClassPlanSequence.objects.create(
            class_plan=class_plan,
            choreography=self.choreography,
            sequence_order=0,
            estimated_time=10
        )
        
        response = self.client.get(
            f'/api/instructors/class-plans/{class_plan.id}/summary/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_sequences'], 1)
        self.assertEqual(response.data['total_estimated_duration'], 10)
        self.assertEqual(response.data['difficulty_breakdown']['beginner'], 1)
    
    def test_instructor_stats(self):
        """Test instructor statistics endpoint"""
        self.client.force_authenticate(user=self.instructor)
        
        # Create class plans
        plan1 = ClassPlan.objects.create(
            instructor=self.instructor,
            title='Plan 1',
            difficulty_level='beginner'
        )
        plan2 = ClassPlan.objects.create(
            instructor=self.instructor,
            title='Plan 2',
            difficulty_level='intermediate'
        )
        
        # Add sequences
        ClassPlanSequence.objects.create(
            class_plan=plan1,
            choreography=self.choreography,
            sequence_order=0
        )
        ClassPlanSequence.objects.create(
            class_plan=plan2,
            choreography=self.choreography,
            sequence_order=0
        )
        
        response = self.client.get('/api/instructors/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_plans'], 2)
        self.assertEqual(response.data['unique_choreographies'], 1)
        self.assertEqual(response.data['avg_sequences_per_plan'], 1.0)
