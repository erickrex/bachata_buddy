"""
Tests for backup and restore scripts.

Tests embedding backup/restore functionality with numpy serialization.
"""

import pytest
import json
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import shutil

# Import the functions we need to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestBackupEmbeddings:
    """Test backup_embeddings.py functionality."""
    
    def test_convert_numpy_to_list_array(self):
        """Test converting numpy array to list."""
        from scripts.backup_embeddings import convert_numpy_to_list
        
        arr = np.array([1.0, 2.0, 3.0])
        result = convert_numpy_to_list(arr)
        
        assert isinstance(result, list)
        assert result == [1.0, 2.0, 3.0]
    
    def test_convert_numpy_to_list_dict(self):
        """Test converting dict with numpy arrays."""
        from scripts.backup_embeddings import convert_numpy_to_list
        
        data = {
            'embedding': np.array([1.0, 2.0]),
            'score': np.float32(0.85),
            'name': 'test'
        }
        
        result = convert_numpy_to_list(data)
        
        assert isinstance(result, dict)
        assert isinstance(result['embedding'], list)
        assert isinstance(result['score'], float)
        assert result['name'] == 'test'
    
    def test_convert_numpy_to_list_nested(self):
        """Test converting nested structures."""
        from scripts.backup_embeddings import convert_numpy_to_list
        
        data = {
            'moves': [
                {'embedding': np.array([1.0, 2.0]), 'id': 1},
                {'embedding': np.array([3.0, 4.0]), 'id': 2}
            ],
            'metadata': {
                'scores': np.array([0.8, 0.9])
            }
        }
        
        result = convert_numpy_to_list(data)
        
        assert isinstance(result['moves'][0]['embedding'], list)
        assert isinstance(result['moves'][1]['embedding'], list)
        assert isinstance(result['metadata']['scores'], list)
    
    def test_convert_numpy_to_list_numpy_types(self):
        """Test converting numpy scalar types."""
        from scripts.backup_embeddings import convert_numpy_to_list
        
        data = {
            'int': np.int64(42),
            'float': np.float32(3.14),
            'bool': np.bool_(True)
        }
        
        result = convert_numpy_to_list(data)
        
        assert isinstance(result['int'], int)
        assert isinstance(result['float'], float)
        assert isinstance(result['bool'], bool)
    
    @patch('scripts.backup_embeddings.ElasticsearchService')
    @patch('scripts.backup_embeddings.EnvironmentConfig')
    def test_backup_embeddings_success(self, mock_config, mock_es_class):
        """Test successful backup."""
        from scripts.backup_embeddings import backup_embeddings
        
        # Setup mocks
        mock_es = Mock()
        mock_es.get_all_embeddings.return_value = [
            {
                'clip_id': 'test_1',
                'audio_embedding': np.array([1.0, 2.0]),
                'text_embedding': np.array([3.0, 4.0])
            }
        ]
        mock_es.index_name = 'test_index'
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = Path(f.name)
        
        try:
            count = backup_embeddings(mock_es, temp_path)
            
            assert count == 1
            assert temp_path.exists()
            
            # Verify file contents
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert 'backup_date' in data
            assert data['index_name'] == 'test_index'
            assert data['count'] == 1
            assert len(data['embeddings']) == 1
            assert isinstance(data['embeddings'][0]['audio_embedding'], list)
        
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    @patch('scripts.backup_embeddings.ElasticsearchService')
    def test_backup_embeddings_empty(self, mock_es_class):
        """Test backup with no embeddings."""
        from scripts.backup_embeddings import backup_embeddings
        
        mock_es = Mock()
        mock_es.get_all_embeddings.return_value = []
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = Path(f.name)
        
        try:
            count = backup_embeddings(mock_es, temp_path)
            assert count == 0
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestRestoreEmbeddings:
    """Test restore_embeddings.py functionality."""
    
    @patch('scripts.restore_embeddings.ElasticsearchService')
    def test_restore_embeddings_success(self, mock_es_class):
        """Test successful restore."""
        from scripts.restore_embeddings import restore_embeddings
        
        # Setup mock
        mock_es = Mock()
        mock_es.index_embeddings.return_value = True
        
        # Create temp backup file
        backup_data = {
            'backup_date': '2025-10-21T00:00:00',
            'index_name': 'test_index',
            'count': 2,
            'embeddings': [
                {
                    'clip_id': 'test_1',
                    'audio_embedding': [1.0, 2.0],
                    'text_embedding': [3.0, 4.0]
                },
                {
                    'clip_id': 'test_2',
                    'audio_embedding': [5.0, 6.0],
                    'text_embedding': [7.0, 8.0]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(backup_data, f)
            temp_path = Path(f.name)
        
        try:
            count = restore_embeddings(mock_es, temp_path)
            
            assert count == 2
            # Verify index_embeddings was called
            assert mock_es.index_embeddings.called
        
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_restore_embeddings_file_not_found(self):
        """Test restore with non-existent file."""
        from scripts.restore_embeddings import restore_embeddings
        
        mock_es = Mock()
        fake_path = Path('/nonexistent/backup.json')
        
        with pytest.raises(FileNotFoundError):
            restore_embeddings(mock_es, fake_path)
    
    @patch('scripts.restore_embeddings.ElasticsearchService')
    def test_restore_embeddings_invalid_json(self, mock_es_class):
        """Test restore with invalid JSON."""
        from scripts.restore_embeddings import restore_embeddings
        
        mock_es = Mock()
        
        # Create temp file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('invalid json {')
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(json.JSONDecodeError):
                restore_embeddings(mock_es, temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestBackupRestoreIntegration:
    """Integration tests for backup and restore."""
    
    @patch('scripts.backup_embeddings.ElasticsearchService')
    @patch('scripts.restore_embeddings.ElasticsearchService')
    def test_backup_and_restore_roundtrip(self, mock_restore_es, mock_backup_es):
        """Test full backup and restore cycle."""
        from scripts.backup_embeddings import backup_embeddings
        from scripts.restore_embeddings import restore_embeddings
        
        # Setup backup mock
        original_embeddings = [
            {
                'clip_id': 'test_1',
                'audio_embedding': np.random.rand(128),
                'lead_embedding': np.random.rand(512),
                'follow_embedding': np.random.rand(512),
                'interaction_embedding': np.random.rand(256),
                'text_embedding': np.random.rand(384),
                'quality_score': 0.85
            }
        ]
        
        mock_backup_es_instance = Mock()
        mock_backup_es_instance.get_all_embeddings.return_value = original_embeddings
        mock_backup_es_instance.index_name = 'test_index'
        
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp())
        backup_path = temp_dir / 'backup.json'
        
        try:
            # Backup
            backup_count = backup_embeddings(mock_backup_es_instance, backup_path)
            assert backup_count == 1
            assert backup_path.exists()
            
            # Verify backup file is valid JSON
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            assert backup_data['count'] == 1
            assert len(backup_data['embeddings']) == 1
            
            # Verify numpy arrays were converted to lists
            emb = backup_data['embeddings'][0]
            assert isinstance(emb['audio_embedding'], list)
            assert isinstance(emb['lead_embedding'], list)
            assert len(emb['audio_embedding']) == 128
            assert len(emb['lead_embedding']) == 512
            
            # Setup restore mock
            mock_restore_es_instance = Mock()
            mock_restore_es_instance.index_embeddings.return_value = True
            
            # Restore
            restore_count = restore_embeddings(mock_restore_es_instance, backup_path)
            assert restore_count == 1
            
            # Verify restore was called with correct data
            assert mock_restore_es_instance.index_embeddings.called
        
        finally:
            # Cleanup
            shutil.rmtree(temp_dir)
    
    def test_numpy_serialization_all_types(self):
        """Test that all numpy types can be serialized."""
        from scripts.backup_embeddings import convert_numpy_to_list
        
        data = {
            'int8': np.int8(1),
            'int16': np.int16(2),
            'int32': np.int32(3),
            'int64': np.int64(4),
            'float16': np.float16(1.5),
            'float32': np.float32(2.5),
            'float64': np.float64(3.5),
            'bool': np.bool_(True),
            'array_1d': np.array([1, 2, 3]),
            'array_2d': np.array([[1, 2], [3, 4]]),
            'array_3d': np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        }
        
        result = convert_numpy_to_list(data)
        
        # All should be converted to Python types
        assert isinstance(result['int8'], int)
        assert isinstance(result['float32'], float)
        assert isinstance(result['bool'], bool)
        assert isinstance(result['array_1d'], list)
        assert isinstance(result['array_2d'], list)
        assert isinstance(result['array_3d'], list)
        
        # Verify can be JSON serialized
        json_str = json.dumps(result)
        assert json_str is not None
