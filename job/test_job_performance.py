"""
Test job performance metrics

This test monitors and measures performance of the video processing job:
1. Job execution time
2. Memory usage
3. CPU usage (if available)
4. Database query performance
5. Processing stage durations

Usage:
    # Start all required services
    docker-compose --profile microservices up -d
    
    # Wait for services to be healthy
    sleep 30
    
    # Run the performance test
    cd bachata_buddy
    uv run python job/test_job_performance.py
"""
import os
import sys
import time
import json
import uuid
import logging
import subprocess
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import database functions directly to avoid loading heavy dependencies
try:
    from services.database import (
        test_connection,
        get_task_status,
        close_connection_pool,
        get_db_cursor
    )
except ImportError as e:
    # If services module has heavy dependencies, import database module directly
    import importlib.util
    db_path = os.path.join(os.path.dirname(__file__), 'src', 'services', 'database.py')
    spec = importlib.util.spec_from_file_location("database", db_path)
    database = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database)
    
    test_connection = database.test_connection
    get_task_status = database.get_task_status
    close_connection_pool = database.close_connection_pool
    get_db_cursor = database.get_db_cursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor performance metrics during job execution"""
    
    def __init__(self):
        self.metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'job_execution': {},
            'database': {},
            'stages': {},
            'system': {}
        }
        self.start_time = None
        self.process = None
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        
        # Get system baseline
        self.metrics['system']['baseline'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_mb': psutil.virtual_memory().available / 1024 / 1024,
        }
        
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring and calculate totals"""
        if self.start_time:
            self.metrics['job_execution']['total_duration_seconds'] = time.time() - self.start_time
        
        # Get system final state
        self.metrics['system']['final'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_mb': psutil.virtual_memory().available / 1024 / 1024,
        }
        
        logger.info("Performance monitoring stopped")
    
    def measure_database_query(self, query: str, params: tuple = None) -> float:
        """
        Measure database query execution time
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query execution time in milliseconds
        """
        start = time.time()
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(query, params)
                cursor.fetchall()
            
            duration_ms = (time.time() - start) * 1000
            return duration_ms
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return -1
    
    def monitor_job_execution(self, task_id: str, audio_file: str, timeout: int = 300) -> bool:
        """
        Monitor job execution and collect performance metrics
        
        Args:
            task_id: Task ID to monitor
            audio_file: Path to audio file
            timeout: Maximum time to wait for job completion (seconds)
            
        Returns:
            True if job completed successfully, False otherwise
        """
        print("\n" + "=" * 80)
        print("Monitoring Job Execution Performance")
        print("=" * 80)
        print(f"Task ID: {task_id}")
        print(f"Audio file: {audio_file}")
        print(f"Timeout: {timeout}s")
        print("=" * 80)
        
        # Detect working directory
        if os.path.exists('/workspace/bachata_buddy'):
            cwd = '/workspace/bachata_buddy'
        elif os.path.exists('bachata_buddy'):
            cwd = 'bachata_buddy'
        else:
            cwd = '.'
        
        # Build docker-compose command
        cmd = [
            'docker-compose', '--profile', 'job', 'run', '--rm',
            '-e', f'TASK_ID={task_id}',
            '-e', 'USER_ID=1',
            '-e', f'AUDIO_INPUT={audio_file}',
            '-e', 'DIFFICULTY=intermediate',
            '-e', 'ENERGY_LEVEL=medium',
            '-e', 'STYLE=romantic',
            'job'
        ]
        
        print(f"\nStarting job execution...")
        print(f"Command: {' '.join(cmd)}")
        
        # Start job execution
        job_start_time = time.time()
        
        try:
            # Run job in subprocess
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            self.process = process
            
            # Monitor job progress
            last_stage = None
            stage_start_times = {}
            
            print("\nMonitoring job progress...")
            print("-" * 80)
            
            # Poll for status updates
            poll_interval = 2  # seconds
            elapsed = 0
            
            while elapsed < timeout:
                # Check if process is still running
                if process.poll() is not None:
                    # Process finished
                    break
                
                # Query task status
                try:
                    with get_db_cursor() as cursor:
                        query = """
                            SELECT status, progress, stage, message, updated_at
                            FROM choreography_tasks
                            WHERE task_id = %s
                        """
                        cursor.execute(query, (task_id,))
                        row = cursor.fetchone()
                        
                        if row:
                            status, progress, stage, message, updated_at = row
                            
                            # Track stage transitions
                            if stage != last_stage:
                                current_time = time.time()
                                
                                # Record previous stage duration
                                if last_stage and last_stage in stage_start_times:
                                    stage_duration = current_time - stage_start_times[last_stage]
                                    self.metrics['stages'][last_stage] = {
                                        'duration_seconds': stage_duration,
                                        'duration_ms': stage_duration * 1000
                                    }
                                    print(f"  ✅ {last_stage}: {stage_duration:.2f}s")
                                
                                # Start timing new stage
                                stage_start_times[stage] = current_time
                                last_stage = stage
                                
                                print(f"\n  Stage: {stage} ({progress}%)")
                                print(f"  Message: {message}")
                            
                            # Check if completed or failed
                            if status in ['completed', 'failed']:
                                # Record final stage duration
                                if stage in stage_start_times:
                                    stage_duration = time.time() - stage_start_times[stage]
                                    self.metrics['stages'][stage] = {
                                        'duration_seconds': stage_duration,
                                        'duration_ms': stage_duration * 1000
                                    }
                                    print(f"  ✅ {stage}: {stage_duration:.2f}s")
                                
                                break
                
                except Exception as e:
                    logger.error(f"Error querying task status: {e}")
                
                # Wait before next poll
                time.sleep(poll_interval)
                elapsed += poll_interval
            
            # Wait for process to finish
            try:
                stdout, _ = process.communicate(timeout=10)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, _ = process.communicate()
                exit_code = -1
            
            # Calculate total job execution time
            job_duration = time.time() - job_start_time
            
            self.metrics['job_execution'] = {
                'duration_seconds': job_duration,
                'duration_ms': job_duration * 1000,
                'exit_code': exit_code,
                'success': exit_code == 0,
                'timeout': elapsed >= timeout
            }
            
            print("-" * 80)
            print(f"\nJob execution completed in {job_duration:.2f}s")
            print(f"Exit code: {exit_code}")
            
            return exit_code == 0
            
        except Exception as e:
            logger.error(f"Error monitoring job execution: {e}")
            print(f"\n❌ Error: {e}")
            return False
    
    def measure_database_performance(self, task_id: str):
        """Measure database query performance"""
        print("\n" + "=" * 80)
        print("Measuring Database Query Performance")
        print("=" * 80)
        
        queries = {
            'select_task_by_id': (
                "SELECT * FROM choreography_tasks WHERE task_id = %s",
                (task_id,)
            ),
            'select_task_status': (
                "SELECT status, progress, stage FROM choreography_tasks WHERE task_id = %s",
                (task_id,)
            ),
            'select_user_tasks': (
                "SELECT * FROM choreography_tasks WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
                (1,)
            ),
        }
        
        for query_name, (query, params) in queries.items():
            duration_ms = self.measure_database_query(query, params)
            
            if duration_ms >= 0:
                self.metrics['database'][query_name] = {
                    'duration_ms': duration_ms,
                    'query': query
                }
                
                status = "✅" if duration_ms < 100 else "⚠️" if duration_ms < 500 else "❌"
                print(f"  {status} {query_name}: {duration_ms:.2f}ms")
            else:
                print(f"  ❌ {query_name}: FAILED")
    
    def save_results(self, output_file: str = 'job_performance_results.json'):
        """Save performance metrics to JSON file"""
        try:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(self.metrics, f, indent=2)
            
            print(f"\n✅ Performance metrics saved to {output_path}")
            logger.info(f"Performance metrics saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving performance metrics: {e}")
            print(f"\n❌ Error saving metrics: {e}")
    
    def print_summary(self):
        """Print performance summary"""
        print("\n" + "=" * 80)
        print("Performance Summary")
        print("=" * 80)
        
        # Job execution
        if 'duration_seconds' in self.metrics['job_execution']:
            duration = self.metrics['job_execution']['duration_seconds']
            success = self.metrics['job_execution']['success']
            
            status = "✅" if success else "❌"
            print(f"\n{status} Job Execution:")
            print(f"  Duration: {duration:.2f}s ({duration/60:.2f} minutes)")
            print(f"  Success: {success}")
            
            # Performance rating
            if duration < 60:
                rating = "Excellent"
            elif duration < 120:
                rating = "Good"
            elif duration < 180:
                rating = "Acceptable"
            else:
                rating = "Needs Optimization"
            
            print(f"  Rating: {rating}")
        
        # Stage durations
        if self.metrics['stages']:
            print(f"\nStage Durations:")
            total_stage_time = 0
            
            for stage, data in self.metrics['stages'].items():
                duration = data['duration_seconds']
                total_stage_time += duration
                print(f"  • {stage}: {duration:.2f}s")
            
            print(f"  Total: {total_stage_time:.2f}s")
        
        # Database performance
        if self.metrics['database']:
            print(f"\nDatabase Query Performance:")
            
            for query_name, data in self.metrics['database'].items():
                duration_ms = data['duration_ms']
                
                if duration_ms < 100:
                    status = "✅ Excellent"
                elif duration_ms < 500:
                    status = "⚠️  Acceptable"
                else:
                    status = "❌ Slow"
                
                print(f"  {status} {query_name}: {duration_ms:.2f}ms")
        
        # System resources
        if 'baseline' in self.metrics['system'] and 'final' in self.metrics['system']:
            baseline = self.metrics['system']['baseline']
            final = self.metrics['system']['final']
            
            print(f"\nSystem Resources:")
            print(f"  CPU Usage:")
            print(f"    Baseline: {baseline['cpu_percent']:.1f}%")
            print(f"    Final: {final['cpu_percent']:.1f}%")
            print(f"    Change: {final['cpu_percent'] - baseline['cpu_percent']:+.1f}%")
            
            print(f"  Memory Usage:")
            print(f"    Baseline: {baseline['memory_percent']:.1f}%")
            print(f"    Final: {final['memory_percent']:.1f}%")
            print(f"    Change: {final['memory_percent'] - baseline['memory_percent']:+.1f}%")
        
        print("=" * 80)


def create_test_task_in_db() -> Optional[str]:
    """Create a test task in the database"""
    task_id = str(uuid.uuid4())
    
    try:
        with get_db_cursor() as cursor:
            query = """
                INSERT INTO choreography_tasks (
                    task_id,
                    user_id,
                    status,
                    progress,
                    stage,
                    message,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            cursor.execute(
                query,
                (task_id, 1, 'started', 0, 'initializing', 'Task created for performance testing')
            )
            
            logger.info(f"Test task created: {task_id}")
            return task_id
            
    except Exception as e:
        logger.error(f"Failed to create test task: {e}")
        return None


def cleanup_test_task(task_id: str):
    """Clean up test task from database"""
    try:
        with get_db_cursor() as cursor:
            query = "DELETE FROM choreography_tasks WHERE task_id = %s"
            cursor.execute(query, (task_id,))
            logger.info(f"Test task deleted: {task_id}")
    except Exception as e:
        logger.error(f"Failed to delete test task: {e}")


def find_audio_file() -> Optional[str]:
    """Find a test audio file"""
    possible_paths = [
        '/app/data/songs/test.mp3',
        'data/songs/test.mp3',
        'bachata_buddy/data/songs/test.mp3',
        '/workspace/bachata_buddy/data/songs/test.mp3',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def main():
    """Run performance monitoring test"""
    print("\n" + "=" * 80)
    print("Job Performance Monitoring Test")
    print("=" * 80)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"DB_HOST: {os.environ.get('DB_HOST', 'localhost')}")
    print(f"DB_NAME: {os.environ.get('DB_NAME', 'bachata_vibes')}")
    print("=" * 80)
    
    monitor = PerformanceMonitor()
    test_task_id = None
    
    try:
        # Test database connection
        print("\n" + "=" * 80)
        print("Prerequisite: Database Connection")
        print("=" * 80)
        
        if not test_connection():
            print("❌ Database connection failed. Cannot proceed with tests.")
            print("\nPlease ensure:")
            print("  1. Database is running: docker-compose up -d db")
            print("  2. Database is healthy: docker-compose ps db")
            print("  3. Environment variables are set correctly")
            return 1
        
        print("✅ Database connection successful")
        
        # Find audio file
        audio_file = find_audio_file()
        if not audio_file:
            print("\n❌ No test audio file found.")
            print("\nPlease ensure test.mp3 exists in data/songs/")
            return 1
        
        print(f"✅ Audio file found: {audio_file}")
        
        # Create test task
        print("\n" + "=" * 80)
        print("Setup: Creating Test Task")
        print("=" * 80)
        
        test_task_id = create_test_task_in_db()
        
        if not test_task_id:
            print("\n❌ Failed to create test task. Cannot proceed with tests.")
            return 1
        
        print(f"✅ Test task created: {test_task_id}")
        
        # Start performance monitoring
        monitor.start_monitoring()
        
        # Monitor job execution
        success = monitor.monitor_job_execution(test_task_id, audio_file, timeout=300)
        
        # Stop performance monitoring
        monitor.stop_monitoring()
        
        # Measure database performance
        monitor.measure_database_performance(test_task_id)
        
        # Print summary
        monitor.print_summary()
        
        # Save results
        monitor.save_results('job/job_performance_results.json')
        
        # Final result
        print("\n" + "=" * 80)
        if success:
            print("✅ Performance monitoring completed successfully")
            print("\nKey Metrics:")
            if 'duration_seconds' in monitor.metrics['job_execution']:
                duration = monitor.metrics['job_execution']['duration_seconds']
                print(f"  • Job execution time: {duration:.2f}s ({duration/60:.2f} minutes)")
            
            if monitor.metrics['stages']:
                print(f"  • Stages monitored: {len(monitor.metrics['stages'])}")
            
            if monitor.metrics['database']:
                avg_query_time = sum(d['duration_ms'] for d in monitor.metrics['database'].values()) / len(monitor.metrics['database'])
                print(f"  • Average database query time: {avg_query_time:.2f}ms")
            
            print("\nNext steps:")
            print("  • Review job_performance_results.json for detailed metrics")
            print("  • Compare with baseline performance")
            print("  • Identify optimization opportunities")
        else:
            print("❌ Performance monitoring failed")
            print("\nPlease review the output above for errors.")
        
        print("=" * 80)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if test_task_id:
            cleanup_test_task(test_task_id)
        
        # Close connection pool
        close_connection_pool()


if __name__ == '__main__':
    sys.exit(main())
