// Collections Page
// Display and manage user's saved choreographies

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import { useDebounce } from '../hooks/useDebounce';
import { useToast } from '../hooks/useToast';
import { formatDuration } from '../utils/format';
import Container from '../components/layout/Container';
import CollectionCard from '../components/collection/CollectionCard';
import CollectionFilters from '../components/collection/CollectionFilters';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Spinner from '../components/common/Spinner';

function Collections() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  // State for collections data
  const [collections, setCollections] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // State for filters
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('all');
  const [sortBy, setSortBy] = useState('recent');
  const [page, setPage] = useState(1);
  
  // State for edit modal
  const [editingCollection, setEditingCollection] = useState(null);
  const [editForm, setEditForm] = useState({ title: '', difficulty: '', notes: '' });
  const [isSaving, setIsSaving] = useState(false);
  
  // State for delete confirmation
  const [deletingId, setDeletingId] = useState(null);
  
  // Debounce search query
  const debouncedSearch = useDebounce(searchQuery, 500);
  
  // Load collections and stats
  useEffect(() => {
    loadCollections();
    loadStats();
  }, [debouncedSearch, filterDifficulty, sortBy, page]);
  
  const loadCollections = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const params = {
        page,
        search: debouncedSearch,
        difficulty: filterDifficulty !== 'all' ? filterDifficulty : '',
        ordering: getSortOrdering(sortBy)
      };
      
      const data = await api.collections.getAll(params);
      setCollections(data.results || data);
    } catch (err) {
      setError(err.message);
      addToast(err.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };
  
  const loadStats = async () => {
    try {
      const data = await api.collections.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };
  
  // Convert sort option to API ordering parameter
  const getSortOrdering = (sortOption) => {
    const sortMap = {
      recent: '-created_at',
      oldest: 'created_at',
      title: 'title',
      duration: '-duration'
    };
    return sortMap[sortOption] || '-created_at';
  };
  
  // Handle play button
  const handlePlay = (id) => {
    const collection = collections.find(c => c.id === id);
    if (collection && collection.task_id) {
      navigate(`/video/${collection.task_id}`);
    } else {
      addToast('Video not available', 'error');
    }
  };
  
  // Handle edit button
  const handleEdit = (id) => {
    const collection = collections.find(c => c.id === id);
    if (collection) {
      setEditingCollection(collection);
      setEditForm({
        title: collection.title,
        difficulty: collection.difficulty,
        notes: collection.notes || ''
      });
    }
  };
  
  // Handle edit form submission
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    
    if (!editForm.title.trim()) {
      addToast('Title is required', 'error');
      return;
    }
    
    try {
      setIsSaving(true);
      await api.collections.update(editingCollection.id, editForm);
      addToast('Collection updated successfully', 'success');
      setEditingCollection(null);
      loadCollections();
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setIsSaving(false);
    }
  };
  
  // Handle delete button
  const handleDelete = (id) => {
    setDeletingId(id);
  };
  
  // Confirm delete
  const confirmDelete = async () => {
    try {
      await api.collections.delete(deletingId);
      addToast('Collection deleted successfully', 'success');
      setDeletingId(null);
      loadCollections();
      loadStats();
    } catch (err) {
      addToast(err.message, 'error');
    }
  };
  
  // Filter and sort collections (client-side backup)
  const filteredCollections = useMemo(() => {
    let filtered = [...collections];
    
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(c => 
        c.title.toLowerCase().includes(query) ||
        (c.song_title && c.song_title.toLowerCase().includes(query))
      );
    }
    
    // Apply difficulty filter
    if (filterDifficulty !== 'all') {
      filtered = filtered.filter(c => 
        c.difficulty.toLowerCase() === filterDifficulty.toLowerCase()
      );
    }
    
    return filtered;
  }, [collections, searchQuery, filterDifficulty]);
  
  // Empty state
  if (!isLoading && collections.length === 0 && !searchQuery && filterDifficulty === 'all') {
    return (
      <Container>
        <div className="py-12">
          <div className="max-w-md mx-auto text-center">
            <div className="text-6xl mb-4">📚</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              No Collections Yet
            </h2>
            <p className="text-gray-600 mb-6">
              Start creating choreographies to build your collection!
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={() => navigate('/select-song')} className="w-full sm:w-auto">
                🎵 Select Song
              </Button>
              <Button 
                onClick={() => navigate('/describe-choreo')}
                variant="secondary"
                className="w-full sm:w-auto"
              >
                ✨ Describe Choreo
              </Button>
            </div>
          </div>
        </div>
      </Container>
    );
  }
  
  return (
    <Container>
      <div className="py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            My Collections
          </h1>
          <p className="text-gray-600">
            Manage your saved choreographies
          </p>
        </div>
        
        {/* Statistics Panel */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4">
              <div className="text-sm text-purple-600 font-medium mb-1">
                Total Collections
              </div>
              <div className="text-2xl font-bold text-purple-900">
                {stats.total_count || 0}
              </div>
            </div>
            
            <div className="bg-gradient-to-br from-pink-50 to-pink-100 rounded-lg p-4">
              <div className="text-sm text-pink-600 font-medium mb-1">
                Total Duration
              </div>
              <div className="text-2xl font-bold text-pink-900">
                {formatDuration(stats.total_duration || 0)}
              </div>
            </div>
            
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4">
              <div className="text-sm text-blue-600 font-medium mb-1">
                Recent (7 days)
              </div>
              <div className="text-2xl font-bold text-blue-900">
                {stats.recent_count || 0}
              </div>
            </div>
            
            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4">
              <div className="text-sm text-green-600 font-medium mb-1">
                By Difficulty
              </div>
              <div className="text-sm text-green-900">
                B: {stats.by_difficulty?.beginner || 0} • 
                I: {stats.by_difficulty?.intermediate || 0} • 
                A: {stats.by_difficulty?.advanced || 0}
              </div>
            </div>
          </div>
        )}
        
        {/* Filters */}
        <CollectionFilters
          searchQuery={searchQuery}
          filterDifficulty={filterDifficulty}
          sortBy={sortBy}
          onSearchChange={setSearchQuery}
          onFilterChange={setFilterDifficulty}
          onSortChange={setSortBy}
        />
        
        {/* Loading state */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        )}
        
        {/* Error state */}
        {error && !isLoading && (
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={loadCollections} variant="secondary">
              Try Again
            </Button>
          </div>
        )}
        
        {/* Collections grid */}
        {!isLoading && !error && filteredCollections.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCollections.map((collection) => (
              <CollectionCard
                key={collection.id}
                collection={collection}
                onPlay={handlePlay}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
        
        {/* No results state */}
        {!isLoading && !error && filteredCollections.length === 0 && (searchQuery || filterDifficulty !== 'all') && (
          <div className="text-center py-12">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No collections found
            </h3>
            <p className="text-gray-600 mb-4">
              Try adjusting your search or filters
            </p>
            <Button 
              onClick={() => {
                setSearchQuery('');
                setFilterDifficulty('all');
              }}
              variant="secondary"
            >
              Clear Filters
            </Button>
          </div>
        )}
        
        {/* Edit Modal */}
        {editingCollection && (
          <Modal
            isOpen={true}
            onClose={() => setEditingCollection(null)}
            title="Edit Collection"
          >
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <Input
                label="Title"
                value={editForm.title}
                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                placeholder="My Awesome Choreography"
                required
              />
              
              <Select
                label="Difficulty"
                value={editForm.difficulty}
                onChange={(value) => setEditForm({ ...editForm, difficulty: value })}
                options={[
                  { value: 'beginner', label: 'Beginner' },
                  { value: 'intermediate', label: 'Intermediate' },
                  { value: 'advanced', label: 'Advanced' }
                ]}
              />
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes (optional)
                </label>
                <textarea
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="Add notes about this choreography..."
                  value={editForm.notes}
                  onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                  rows={3}
                />
              </div>
              
              <div className="flex gap-2 pt-4">
                <Button
                  type="button"
                  onClick={() => setEditingCollection(null)}
                  variant="secondary"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSaving}
                  className="flex-1"
                >
                  {isSaving ? 'Saving...' : '💾 Save Changes'}
                </Button>
              </div>
            </form>
          </Modal>
        )}
        
        {/* Delete Confirmation Modal */}
        {deletingId && (
          <Modal
            isOpen={true}
            onClose={() => setDeletingId(null)}
            title="Delete Collection"
          >
            <div className="space-y-4">
              <p className="text-gray-700">
                Are you sure you want to delete this collection? This action cannot be undone.
              </p>
              
              <div className="flex gap-2 pt-4">
                <Button
                  onClick={() => setDeletingId(null)}
                  variant="secondary"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={confirmDelete}
                  variant="danger"
                  className="flex-1"
                >
                  🗑️ Delete
                </Button>
              </div>
            </div>
          </Modal>
        )}
      </div>
    </Container>
  );
}

export default Collections;
