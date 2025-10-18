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
    _active_tasks,
    _task_lock
)


@pytest.fixture(autouse=True)
def clear_tasks():
    """Clear all tasks before and after each test."""
    with _task_lock:
        _active_tasks.clear()
    yield
    with _task_lock:
        _active_tasks.clear()


class TestCreateTask:
    """Tests for create_task function."""
    
    def test_create_task_basic(self):
        """Test creating a basic task."""
        task_id = "test-task-1"
        user_id = 1
        
        task = create_task(task_id, user_id)
        
        assert task['task_id'] == task_id
        assert task['user_id'] == user_id
        assert task['status'] == 'started'
        assert task['progress'] == 0
        assert task['stage'] == 'initializing'
        assert task['message'] == 'Starting choreography generation...'
        assert task['result'] is None
        assert task['error'] is None
        assert 'created_at' in task
        assert isinstance(task['created_at'], float)
    
    def test_create_task_with_extra_data(self):
        """Test creating a task with additional data."""
        task_id = "test-task-2"
        user_id = 2
        
        task = create_task(
            task_id,
            user_id,
            difficulty='intermediate',
            song='Amor.mp3'
        )
        
        assert task['difficulty'] == 'intermediate'
        assert task['song'] == 'Amor.mp3'
    
    def test_create_task_stores_in_memory(self):
        """Test that created task is stored in memory."""
        task_id = "test-task-3"
        user_id = 3
        
        create_task(task_id, user_id)
        
        with _task_lock:
            assert task_id in _active_tasks
            assert _active_tasks[task_id]['user_id'] == user_id


class TestGetTask:
    """Tests for get_task function."""
    
    def test_get_existing_task(self):
        """Test retrieving an existing task."""
        task_id = "test-task-4"
        user_id = 4
        
        create_task(task_id, user_id)
        retrieved_task = get_task(task_id)
        
        assert retrieved_task is not None
        assert retrieved_task['task_id'] == task_id
        assert retrieved_task['user_id'] == user_id
    
    def test_get_nonexistent_task(self):
        """Test retrieving a task that doesn't exist."""
        task = get_task("nonexistent-task")
        assert task is None
    
    def test_get_task_returns_copy(self):
        """Test that get_task returns a copy, not the original."""
        task_id = "test-task-5"
        user_id = 5
        
        create_task(task_id, user_id)
        task1 = get_task(task_id)
        task2 = get_task(task_id)
        
        # Modify one copy
        task1['custom_field'] = 'modified'
        
        # Other copy should be unaffected
        assert 'custom_field' not in task2


class TestUpdateTask:
    """Tests for update_task function."""
    
    def test_update_existing_task(self):
        """Test updating an existing task."""
        task_id = "test-task-6"
        user_id = 6
        
        create_task(task_id, user_id)
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
    
    def test_update_preserves_other_fields(self):
        """Test that updating doesn't remove other fields."""
        task_id = "test-task-7"
        user_id = 7
        
        create_task(task_id, user_id, custom_field='value')
        update_task(task_id, progress=25)
        
        updated_task = get_task(task_id)
        assert updated_task['progress'] == 25
        assert updated_task['custom_field'] == 'value'
        assert updated_task['user_id'] == user_id


class TestCleanupOldTasks:
    """Tests for cleanup_old_tasks function."""
    
    def test_cleanup_old_tasks_removes_old(self):
        """Test that old tasks are removed."""
        # Create an old task (simulate by setting created_at in the past)
        task_id = "old-task"
        user_id = 8
        
        create_task(task_id, user_id)
        
        # Manually set created_at to 2 hours ago
        with _task_lock:
            _active_tasks[task_id]['created_at'] = time.time() - (2 * 3600)
        
        # Cleanup tasks older than 1 hour
        removed_count = cleanup_old_tasks(max_age_hours=1)
        
        assert removed_count == 1
        assert get_task(task_id) is None
    
    def test_cleanup_preserves_recent_tasks(self):
        """Test that recent tasks are not removed."""
        task_id = "recent-task"
        user_id = 9
        
        create_task(task_id, user_id)
        
        # Cleanup tasks older than 1 hour
        removed_count = cleanup_old_tasks(max_age_hours=1)
        
        assert removed_count == 0
        assert get_task(task_id) is not None
    
    def test_cleanup_multiple_tasks(self):
        """Test cleanup with multiple tasks of different ages."""
        # Create recent tasks
        create_task("recent-1", 10)
        create_task("recent-2", 11)
        
        # Create old tasks
        create_task("old-1", 12)
        create_task("old-2", 13)
        
        # Set old tasks to 2 hours ago
        with _task_lock:
            _active_tasks["old-1"]['created_at'] = time.time() - (2 * 3600)
            _active_tasks["old-2"]['created_at'] = time.time() - (2 * 3600)
        
        # Cleanup
        removed_count = cleanup_old_tasks(max_age_hours=1)
        
        assert removed_count == 2
        assert get_task("recent-1") is not None
        assert get_task("recent-2") is not None
        assert get_task("old-1") is None
        assert get_task("old-2") is None
    
    def test_cleanup_custom_max_age(self):
        """Test cleanup with custom max age."""
        task_id = "task-1"
        user_id = 14
        
        create_task(task_id, user_id)
        
        # Set task to 30 minutes ago
        with _task_lock:
            _active_tasks[task_id]['created_at'] = time.time() - (0.5 * 3600)
        
        # Cleanup with 1 hour max age - should not remove
        removed_count = cleanup_old_tasks(max_age_hours=1)
        assert removed_count == 0
        assert get_task(task_id) is not None
        
        # Cleanup with 15 minutes max age - should remove
        removed_count = cleanup_old_tasks(max_age_hours=0.25)
        assert removed_count == 1
        assert get_task(task_id) is None


class TestDeleteTask:
    """Tests for delete_task function."""
    
    def test_delete_existing_task(self):
        """Test deleting an existing task."""
        task_id = "test-task-15"
        user_id = 15
        
        create_task(task_id, user_id)
        result = delete_task(task_id)
        
        assert result is True
        assert get_task(task_id) is None
    
    def test_delete_nonexistent_task(self):
        """Test deleting a task that doesn't exist."""
        result = delete_task("nonexistent-task")
        assert result is False


class TestGetAllTasks:
    """Tests for get_all_tasks function."""
    
    def test_get_all_tasks_empty(self):
        """Test getting all tasks when none exist."""
        tasks = get_all_tasks()
        assert tasks == {}
    
    def test_get_all_tasks_multiple(self):
        """Test getting all tasks when multiple exist."""
        create_task("task-1", 16)
        create_task("task-2", 17)
        create_task("task-3", 18)
        
        tasks = get_all_tasks()
        
        assert len(tasks) == 3
        assert "task-1" in tasks
        assert "task-2" in tasks
        assert "task-3" in tasks


class TestThreadSafety:
    """Tests for thread safety of task operations."""
    
    def test_concurrent_task_creation(self):
        """Test that concurrent task creation is thread-safe."""
        import threading
        
        def create_tasks(start_id, count):
            for i in range(count):
                task_id = f"task-{start_id + i}"
                create_task(task_id, start_id + i)
        
        # Create tasks from multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_tasks, args=(i * 10, 10))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all tasks were created
        tasks = get_all_tasks()
        assert len(tasks) == 50
    
    def test_concurrent_updates(self):
        """Test that concurrent updates are thread-safe."""
        import threading
        
        task_id = "shared-task"
        create_task(task_id, 100)
        
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
