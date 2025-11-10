// SelectSong Page
// Song selection with search, filters, and pagination

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDebounce } from '../hooks/useDebounce';
import { useToast } from '../hooks/useToast';
import { api } from '../utils/api';
import SongCard from '../components/generation/SongCard';
import ParameterForm from '../components/generation/ParameterForm';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Spinner from '../components/common/Spinner';
import Card from '../components/common/Card';

function SelectSong() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  
  // State management
  const [songs, setSongs] = useState([]);
  const [selectedSong, setSelectedSong] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showParameterForm, setShowParameterForm] = useState(false);
  
  // Filter and search state
  const [searchQuery, setSearchQuery] = useState('');
  const [genre, setGenre] = useState('');
  const [bpmMin, setBpmMin] = useState('');
  const [bpmMax, setBpmMax] = useState('');
  const [sortBy, setSortBy] = useState('title');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Debounce search query
  const debouncedSearch = useDebounce(searchQuery, 500);
  
  // Fetch songs from API
  useEffect(() => {
    const fetchSongs = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        const params = {
          page,
          page_size: 20,
          ordering: sortBy
        };
        
        // Add search query if present
        if (debouncedSearch) {
          params.search = debouncedSearch;
        }
        
        // Add genre filter if selected
        if (genre) {
          params.genre = genre;
        }
        
        // Add BPM range filters if set
        if (bpmMin) {
          params.bpm_min = bpmMin;
        }
        if (bpmMax) {
          params.bpm_max = bpmMax;
        }
        
        const response = await api.songs.getAll(params);
        
        // Handle paginated response
        if (response.results) {
          setSongs(response.results);
          setTotalPages(Math.ceil(response.count / 20));
        } else {
          // Handle non-paginated response
          setSongs(response);
          setTotalPages(1);
        }
      } catch (err) {
        const errorMessage = err.message || 'Failed to load songs';
        setError(errorMessage);
        setSongs([]);
        addToast(errorMessage, 'error');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchSongs();
  }, [debouncedSearch, genre, bpmMin, bpmMax, sortBy, page]);
  
  // Handle song selection
  const handleSongSelect = (song) => {
    setSelectedSong(song);
    setShowParameterForm(true);
    // Scroll to top to show parameter form
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  
  // Handle cancel - go back to song selection
  const handleCancel = () => {
    setSelectedSong(null);
    setShowParameterForm(false);
  };
  
  // Handle form submission - generate choreography
  const handleSubmit = async (parameters) => {
    try {
      // Call API to generate choreography from song
      const response = await api.generation.fromSong(
        parameters.songId,
        parameters.difficulty,
        parameters.energyLevel,
        parameters.style
      );
      
      // Navigate to progress page with task_id
      if (response.task_id) {
        addToast('Choreography generation started!', 'success');
        navigate(`/progress/${response.task_id}`);
      } else {
        throw new Error('No task ID received from server');
      }
    } catch (err) {
      console.error('Generation failed:', err);
      const errorMessage = err.message || 'Failed to start choreography generation. Please try again.';
      addToast(errorMessage, 'error');
    }
  };
  
  // Handle clear filters
  const handleClearFilters = () => {
    setSearchQuery('');
    setGenre('');
    setBpmMin('');
    setBpmMax('');
    setSortBy('title');
    setPage(1);
  };
  
  // Genre options (these should match backend choices)
  const genreOptions = [
    { value: '', label: 'All Genres' },
    { value: 'traditional', label: 'Traditional' },
    { value: 'modern', label: 'Modern' },
    { value: 'sensual', label: 'Sensual' },
    { value: 'urban', label: 'Urban' }
  ];
  
  // Sort options
  const sortOptions = [
    { value: 'title', label: 'Title (A-Z)' },
    { value: '-title', label: 'Title (Z-A)' },
    { value: 'artist', label: 'Artist (A-Z)' },
    { value: '-artist', label: 'Artist (Z-A)' },
    { value: 'bpm', label: 'BPM (Low to High)' },
    { value: '-bpm', label: 'BPM (High to Low)' }
  ];
  
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {showParameterForm ? 'Configure Choreography' : 'Select a Song'}
          </h1>
          <p className="text-gray-600">
            {showParameterForm 
              ? 'Set your preferences for the choreography generation'
              : 'Choose a song from our library to generate your choreography'
            }
          </p>
        </div>
        
        {/* Parameter Form - shown when song is selected */}
        {showParameterForm && selectedSong && (
          <ParameterForm
            selectedSong={selectedSong}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
          />
        )}
        
        {/* Search and Filters - hidden when parameter form is shown */}
        {!showParameterForm && (
          <Card className="p-6 mb-6">
          <div className="space-y-4">
            {/* Search Input */}
            <div>
              <Input
                type="search"
                placeholder="Search by title or artist..."
                value={searchQuery}
                onChange={setSearchQuery}
                className="w-full"
              />
            </div>
            
            {/* Filters Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Genre Filter */}
              <Select
                label="Genre"
                value={genre}
                onChange={setGenre}
                options={genreOptions}
              />
              
              {/* BPM Min */}
              <Input
                type="number"
                label="Min BPM"
                placeholder="e.g., 120"
                value={bpmMin}
                onChange={setBpmMin}
                min="0"
                max="250"
              />
              
              {/* BPM Max */}
              <Input
                type="number"
                label="Max BPM"
                placeholder="e.g., 180"
                value={bpmMax}
                onChange={setBpmMax}
                min="0"
                max="250"
              />
              
              {/* Sort By */}
              <Select
                label="Sort By"
                value={sortBy}
                onChange={setSortBy}
                options={sortOptions}
              />
            </div>
            
            {/* Clear Filters Button */}
            {(searchQuery || genre || bpmMin || bpmMax || sortBy !== 'title') && (
              <div className="flex justify-end">
                <button
                  onClick={handleClearFilters}
                  className="text-sm text-purple-600 hover:text-purple-700 font-medium"
                >
                  Clear all filters
                </button>
              </div>
            )}
          </div>
        </Card>
        )}
        
        {/* Loading State */}
        {!showParameterForm && isLoading && (
          <div className="flex justify-center items-center py-12">
            <Spinner size="lg" />
          </div>
        )}
        
        {/* Error State */}
        {!showParameterForm && error && !isLoading && (
          <Card className="p-8 text-center">
            <div className="text-red-600 mb-4">
              <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-lg font-semibold">Error Loading Songs</p>
            </div>
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="text-purple-600 hover:text-purple-700 font-medium"
            >
              Try Again
            </button>
          </Card>
        )}
        
        {/* Empty State */}
        {!showParameterForm && !isLoading && !error && songs.length === 0 && (
          <Card className="p-8 text-center">
            <div className="text-gray-400 mb-4">
              <svg className="w-16 h-16 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
              <p className="text-lg font-semibold text-gray-600">No Songs Found</p>
            </div>
            <p className="text-gray-500 mb-4">
              Try adjusting your search or filters to find more songs
            </p>
            {(searchQuery || genre || bpmMin || bpmMax) && (
              <button
                onClick={handleClearFilters}
                className="text-purple-600 hover:text-purple-700 font-medium"
              >
                Clear Filters
              </button>
            )}
          </Card>
        )}
        
        {/* Songs Grid */}
        {!showParameterForm && !isLoading && !error && songs.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
              {songs.map((song) => (
                <SongCard
                  key={song.id}
                  song={song}
                  onSelect={handleSongSelect}
                />
              ))}
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                
                <span className="px-4 py-2 text-gray-600">
                  Page {page} of {totalPages}
                </span>
                
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default SelectSong;
