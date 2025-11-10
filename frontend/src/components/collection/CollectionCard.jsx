import Button from '../common/Button';
import { formatDuration } from '../../utils/format';

function CollectionCard({ collection, onPlay, onEdit, onDelete }) {
  const getDifficultyColor = (difficulty) => {
    const colors = {
      beginner: 'bg-green-100 text-green-800',
      intermediate: 'bg-yellow-100 text-yellow-800',
      advanced: 'bg-red-100 text-red-800'
    };
    return colors[difficulty] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {collection.title}
          </h3>
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getDifficultyColor(collection.difficulty)}`}>
            {collection.difficulty}
          </span>
        </div>
      </div>

      {/* Info */}
      <div className="space-y-2 mb-4">
        {collection.music_info?.song && (
          <p className="text-sm text-gray-600">
            🎵 {collection.music_info.song}
            {collection.music_info.artist && ` - ${collection.music_info.artist}`}
          </p>
        )}
        <p className="text-sm text-gray-600">
          ⏱️ {formatDuration(collection.duration)}
        </p>
        <p className="text-xs text-gray-500">
          Created {new Date(collection.created_at).toLocaleDateString()}
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Button
          onClick={() => onPlay(collection.id)}
          variant="primary"
          size="sm"
          className="flex-1"
        >
          ▶️ Play
        </Button>
        <Button
          onClick={() => onEdit(collection.id)}
          variant="secondary"
          size="sm"
        >
          ✏️
        </Button>
        <Button
          onClick={() => onDelete(collection.id)}
          variant="secondary"
          size="sm"
        >
          🗑️
        </Button>
      </div>
    </div>
  );
}

export default CollectionCard;
