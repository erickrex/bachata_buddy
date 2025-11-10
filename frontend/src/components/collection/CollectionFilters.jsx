import Input from '../common/Input';
import Select from '../common/Select';

function CollectionFilters({ 
  searchQuery, 
  filterDifficulty, 
  sortBy, 
  onSearchChange, 
  onFilterChange, 
  onSortChange 
}) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Search */}
        <Input
          label="Search"
          type="text"
          value={searchQuery}
          onChange={onSearchChange}
          placeholder="Search by title or song..."
        />

        {/* Difficulty Filter */}
        <Select
          label="Difficulty"
          value={filterDifficulty}
          onChange={onFilterChange}
          options={[
            { value: 'all', label: 'All Difficulties' },
            { value: 'beginner', label: 'Beginner' },
            { value: 'intermediate', label: 'Intermediate' },
            { value: 'advanced', label: 'Advanced' }
          ]}
        />

        {/* Sort */}
        <Select
          label="Sort By"
          value={sortBy}
          onChange={onSortChange}
          options={[
            { value: 'recent', label: 'Most Recent' },
            { value: 'oldest', label: 'Oldest First' },
            { value: 'title', label: 'Title (A-Z)' },
            { value: 'duration', label: 'Duration' }
          ]}
        />
      </div>
    </div>
  );
}

export default CollectionFilters;
