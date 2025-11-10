// SongCard Component
// Displays individual song information with selection capability

import Card from '../common/Card';
import Button from '../common/Button';
import { formatDuration } from '../../utils/format';

function SongCard({ song, onSelect }) {
  if (!song) return null;

  const { id, title, artist, bpm, genre, duration } = song;

  return (
    <Card hover className="p-4">
      <div className="space-y-3">
        {/* Song Title */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-1">
            {title}
          </h3>
          <p className="text-sm text-gray-600 line-clamp-1">
            {artist}
          </p>
        </div>

        {/* Song Details */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <span className="font-medium">{bpm}</span>
              <span>BPM</span>
            </span>
            {genre && (
              <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-md text-xs font-medium">
                {genre}
              </span>
            )}
          </div>
          <span>{formatDuration(duration)}</span>
        </div>

        {/* Select Button */}
        <Button
          onClick={() => onSelect(song)}
          className="w-full"
          size="sm"
        >
          Select Song
        </Button>
      </div>
    </Card>
  );
}

export default SongCard;
