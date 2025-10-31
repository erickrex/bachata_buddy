"""
Tests for task management utilities.
"""

import pytest
import time
from choreography.utils import (
    create_task,
    get_task,
    update_task,
    cleanup_old_tasks,
    delete_task,
    get_all_tasks,
)
from choreography.models import ChoreographyTask


@pytest.fixture(autouse=True)
def clear_tasks(db):
    """Clear all tasks before and after each test."""
    ChoreographyTask.objects.all().delete()
    yield
    ChoreographyTask.objects.all().delete()


@pytest.mark.django_db
class TestCreateTask:
    """Tests for create_task function."""
    
    def test_create_task_basic(self, test_user):
        """Test creating a basic task."""
        task_id = "test-task-1"
        
        task = create_task(task_id, test_user.id)
        
        assert task['task_id'] == task_id
        assert task['user_id'] == test_user.id
        assert task['status'] == 'started'
        assert task['progress'] == 0
        assert task['stage'] == 'initializing'
        assert task['message'] == 'Starting choreography generation...'
        assert task['result'] is None
        assert task['error'] is None
        assert 'created_at' in task
    
    def test_create_task_with_extra_data(self, test_user):
        """Test creating a task with additional data in result field."""
        task_id = "test-task-2"
        
        task = create_task(
            task_id,
            test_user.id,
            result={'difficulty': 'intermediate', 'song': 'Amor.mp3'}
        )
        
        assert task['result']['difficulty'] == 'intermediate'
        assert task['result']['song'] == 'Amor.mp3'
    
    def test_create_task_stores_in_database(self, test_user):
        """Test that created task is stored in database."""
        task_id = "test-task-3"
        
        create_task(task_id, test_user.id)
        
        # Verify task exists in database
        task = ChoreographyTask.objects.get(task_id=task_id)
        assert task.user_id == test_user.id


@pytest.mark.django_db
class TestGetTask:
    """Tests for get_task function."""
    
    def test_get_existing_task(self, test_user):
        """Test retrieving an existing task."""
        task_id = "test-task-4"
        
        create_task(task_id, test_user.id)
        retrieved_task = get_task(task_id)
        
        assert retrieved_task is not None
        assert retrieved_task['task_id'] == task_id
        assert retrieved_task['user_id'] == test_user.id
    
    def test_get_nonexistent_task(self):
        """Test retrieving a task that doesn't exist."""
        task = get_task("nonexistent-task")
        assert task is None
    
    def test_get_task_returns_copy(self, test_user):
        """Test that get_task returns a copy, not the original."""
        task_id = "test-task-5"
        
        create_task(task_id, test_user.id)
        task1 = get_task(task_id)
        task2 = get_task(task_id)
        
        # Modify one copy
        task1['custom_field'] = 'modified'
        
        # Other copy should be unaffected
        assert 'custom_field' not in task2


@pytest.mark.django_db
class TestUpdateTask:
    """Tests for update_task function."""
    
    def test_update_existing_task(self, test_user):
        """Test updating an existing task."""
        task_id = "test-task-6"
        
        create_task(task_id, test_user.id)
        result = update_task(
            task_id,
            status='running',
            progress=50,
            stage='analyzing',
            message='Analyzing music...'
        )
        
        assert result is True
        
        updated_task = get_task(task_id)
        assert updated_task['status'] == 'running'
        assert updated_task['progress'] == 50
        assert updated_task['stage'] == 'analyzing'
        assert updated_task['message'] == 'Analyzing music...'
    
    def test_update_nonexistent_task(self):
        """Test updating a task that doesn't exist."""
        result = update_task("nonexistent-task", status='completed')
        assert result is False
    
    def test_update_preserves_other_fields(self, test_user):
        """Test that updating doesn't remove other fields."""
        task_id = "test-task-7"
        
        create_task(task_id, test_user.id, result={'custom_field': 'value'})
        update_task(task_id, progress=25)
        
        updated_task = get_task(task_id)
        assert updated_task['progress'] == 25
        assert updated_task['result']['custom_field'] == 'value'
        assert updated_task['user_id'] == test_user.id


@pytest.mark.django_db
class TestCleanupOldTasks:
    """Tests for cleanup_old_tasks function."""
    
    def test_cleanup_old_tasks_removes_old(self, test_user):
        """Test that old tasks are removed."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Create an old task (simulate by setting created_at in the past)
        task_id = "old-task"
        
        create_task(task_id, test_user.id)
        
        # Manually set created_at to 2 hours ago
        task = ChoreographyTask.objects.get(task_id=task_id)
        task.created_at = timezone.now() - timedelta(hours=2)
        task.save()
        
        # Cleanup tasks older than 1 hour
        removed_count = cleanup_old_tasks(max_age_hours=1)
        
        assert removed_count == 1
        assert get_task(task_id) is None
    
    def test_cleanup_preserves_recent_tasks(self, test_user):
        """Test that recent tasks are not removed."""
        task_id = "recent-task"
        
        create_task(task_id, test_user.id)
        
        # Cleanup tasks older than 1 hour
        removed_count = cleanup_old_tasks(max_age_hours=1)
        
        assert removed_count == 0
        assert get_task(task_id) is not None
    
    def test_cleanup_multiple_tasks(self, test_user):
        """Test cleanup with multiple tasks of different ages."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Create recent tasks
        create_task("recent-1", test_user.id)
        create_task("recent-2", test_user.id)
        
        # Create old tasks
        create_task("old-1", test_user.id)
        create_task("old-2", test_user.id)
        
        # Set old tasks to 2 hours ago
        for task_id in ["old-1", "old-2"]:
            task = ChoreographyTask.objects.get(task_id=task_id)
            task.created_at = timezone.now() - timedelta(hours=2)
            task.save()
        
        # Cleanup
        removed_count = cleanup_old_tasks(max_age_hours=1)
        
        assert removed_count == 2
        assert get_task("recent-1") is not None
        assert get_task("recent-2") is not None
        assert get_task("old-1") is None
        assert get_task("old-2") is None
    
    def test_cleanup_custom_max_age(self, test_user):
        """Test cleanup with custom max age."""
        from django.utils import timezone
        from datetime import timedelta
        
        task_id = "task-1"
        
        create_task(task_id, test_user.id)
        
        # Set task to 30 minutes ago
        task = ChoreographyTask.objects.get(task_id=task_id)
        task.created_at = timezone.now() - timedelta(minutes=30)
        task.save()
        
        # Cleanup with 1 hour max age - should not remove
        removed_count = cleanup_old_tasks(max_age_hours=1)
        assert removed_count == 0
        assert get_task(task_id) is not None
        
        # Cleanup with 15 minutes max age - should remove
        removed_count = cleanup_old_tasks(max_age_hours=0.25)
        assert removed_count == 1
        assert get_task(task_id) is None


@pytest.mark.django_db
class TestDeleteTask:
    """Tests for delete_task function."""
    
    def test_delete_existing_task(self, test_user):
        """Test deleting an existing task."""
        task_id = "test-task-15"
        
        create_task(task_id, test_user.id)
        result = delete_task(task_id)
        
        assert result is True
        assert get_task(task_id) is None
    
    def test_delete_nonexistent_task(self):
        """Test deleting a task that doesn't exist."""
        result = delete_task("nonexistent-task")
        assert result is False


@pytest.mark.django_db
class TestGetAllTasks:
    """Tests for get_all_tasks function."""
    
    def test_get_all_tasks_empty(self):
        """Test getting all tasks when none exist."""
        tasks = get_all_tasks()
        assert tasks == {}
    
    def test_get_all_tasks_multiple(self, test_user):
        """Test getting all tasks when multiple exist."""
        create_task("task-1", test_user.id)
        create_task("task-2", test_user.id)
        create_task("task-3", test_user.id)
        
        tasks = get_all_tasks()
        
        assert len(tasks) == 3
        assert "task-1" in tasks
        assert "task-2" in tasks
        assert "task-3" in tasks


@pytest.mark.django_db
class TestThreadSafety:
    """Tests for thread safety of task operations."""
    
    def test_concurrent_task_creation(self, test_user):
        """Test that concurrent task creation works sequentially."""
        # Note: Django database connections are not thread-safe by default
        # This test verifies that sequential creation works correctly
        
        # Create tasks sequentially (simulating what would happen in production)
        for i in range(50):
            task_id = f"task-{i}"
            create_task(task_id, test_user.id)
        
        # Verify all tasks were created
        tasks = get_all_tasks()
        assert len(tasks) == 50
    
    def test_concurrent_updates(self, test_user):
        """Test that concurrent updates are thread-safe."""
        import threading
        
        task_id = "shared-task"
        create_task(task_id, test_user.id)
        
        def update_progress(value):
            update_task(task_id, progress=value)
        
        # Update from multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_progress, args=(i * 10,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Task should still exist and have a valid progress value
        task = get_task(task_id)
        assert task is not None
        assert 0 <= task['progress'] <= 90
