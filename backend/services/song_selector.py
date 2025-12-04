"""
Song Selector Service

Intelligently selects songs for choreography generation based on:
- User's natural language description
- Choreography parameters (difficulty, energy, style)
- Song metadata (BPM, genre)
"""

import logging
from typing import Optional, Dict, Any
from apps.choreography.models import Song

logger = logging.getLogger(__name__)


class SongSelector:
    """
    Selects appropriate songs for choreography generation.
    
    Uses rule-based matching with BPM, keywords, and metadata.
    Can be enhanced with text embeddings in the future.
    """
    
    # BPM ranges for energy levels
    # Adjusted based on actual song library (115-134 BPM)
    BPM_RANGES = {
        'low': (110, 120),     # Slow, romantic songs (115-123 BPM)
        'medium': (120, 130),  # Standard bachata tempo (123-124 BPM)
        'high': (130, 140)     # Fast, energetic songs (132-134 BPM)
    }
    
    # Keywords for style matching
    STYLE_KEYWORDS = {
        'romantic': ['romantic', 'love', 'slow', 'intimate', 'close', 'sensual'],
        'energetic': ['energetic', 'fast', 'upbeat', 'party', 'fun', 'lively'],
        'sensual': ['sensual', 'sexy', 'body', 'close', 'intimate'],
        'playful': ['playful', 'fun', 'happy', 'joyful', 'light']
    }
    
    def select_song_for_choreography(
        self,
        query: str,
        difficulty: str,
        energy_level: str,
        style: str
    ) -> Song:
        """
        Select appropriate song based on choreography parameters.
        
        Args:
            query: User's natural language description
            difficulty: beginner, intermediate, advanced
            energy_level: low, medium, high
            style: romantic, energetic, sensual, playful
        
        Returns:
            Selected Song object
        
        Raises:
            ValueError: If no songs available
        """
        logger.info(
            f"Selecting song for choreography",
            extra={
                'query': query[:50],
                'difficulty': difficulty,
                'energy_level': energy_level,
                'style': style
            }
        )
        
        # Start with all bachata songs (case-insensitive contains)
        songs = Song.objects.filter(genre__icontains='bachata')
        
        if not songs.exists():
            # Try any genre
            songs = Song.objects.all()
            if not songs.exists():
                raise ValueError("No songs available in database")
        
        # Strategy 1: Filter by BPM based on energy level
        bpm_filtered = self._filter_by_bpm(songs, energy_level)
        if bpm_filtered.exists():
            songs = bpm_filtered
            logger.debug(f"Filtered to {songs.count()} songs by BPM")
        
        # Strategy 2: Score songs by keyword matching
        scored_songs = self._score_songs_by_keywords(
            songs,
            query,
            style
        )
        
        # Select best match
        if scored_songs:
            best_song = scored_songs[0]['song']
            best_score = scored_songs[0]['score']
            logger.info(
                f"Selected song: {best_song.title} by {best_song.artist}",
                extra={
                    'song_id': best_song.id,
                    'bpm': best_song.bpm,
                    'score': best_score
                }
            )
            return best_song
        
        # Fallback: return first song
        song = songs.first()
        logger.warning(
            f"No scored matches, using fallback: {song.title}",
            extra={'song_id': song.id}
        )
        return song
    
    def _filter_by_bpm(self, songs, energy_level: str):
        """
        Filter songs by BPM range based on energy level.
        
        Args:
            songs: QuerySet of songs
            energy_level: low, medium, high
        
        Returns:
            Filtered QuerySet
        """
        if energy_level not in self.BPM_RANGES:
            return songs
        
        min_bpm, max_bpm = self.BPM_RANGES[energy_level]
        
        # Filter songs with BPM in range
        filtered = songs.filter(
            bpm__isnull=False,
            bpm__gte=min_bpm,
            bpm__lte=max_bpm
        )
        
        logger.debug(
            f"BPM filter: {energy_level} ({min_bpm}-{max_bpm} BPM)",
            extra={
                'original_count': songs.count(),
                'filtered_count': filtered.count()
            }
        )
        
        return filtered
    
    def _score_songs_by_keywords(
        self,
        songs,
        query: str,
        style: str
    ) -> list:
        """
        Score songs by keyword matching in title and artist.
        
        Args:
            songs: QuerySet of songs
            query: User's query
            style: Choreography style
        
        Returns:
            List of dicts with 'song' and 'score', sorted by score descending
        """
        query_lower = query.lower()
        style_keywords = self.STYLE_KEYWORDS.get(style, [])
        
        scored = []
        
        for song in songs:
            score = 0
            song_text = f"{song.title} {song.artist}".lower()
            
            # Score by style keywords in song metadata
            for keyword in style_keywords:
                if keyword in song_text:
                    score += 2
                if keyword in query_lower:
                    score += 1
            
            # Score by query keywords in song metadata
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 3 and word in song_text:
                    score += 1
            
            # Prefer songs with BPM data
            if song.bpm:
                score += 0.5
            
            scored.append({
                'song': song,
                'score': score
            })
        
        # Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)
        
        logger.debug(
            f"Scored {len(scored)} songs",
            extra={
                'top_3': [
                    {
                        'title': s['song'].title,
                        'score': s['score']
                    }
                    for s in scored[:3]
                ]
            }
        )
        
        return scored
    
    def get_song_by_id(self, song_id: int) -> Song:
        """
        Get song by ID.
        
        Args:
            song_id: Song ID
        
        Returns:
            Song object
        
        Raises:
            Song.DoesNotExist: If song not found
        """
        return Song.objects.get(id=song_id)
    
    def list_songs_by_criteria(
        self,
        genre: Optional[str] = None,
        min_bpm: Optional[int] = None,
        max_bpm: Optional[int] = None
    ) -> list:
        """
        List songs matching criteria.
        
        Args:
            genre: Filter by genre
            min_bpm: Minimum BPM
            max_bpm: Maximum BPM
        
        Returns:
            List of Song objects
        """
        songs = Song.objects.all()
        
        if genre:
            songs = songs.filter(genre=genre)
        
        if min_bpm:
            songs = songs.filter(bpm__gte=min_bpm)
        
        if max_bpm:
            songs = songs.filter(bpm__lte=max_bpm)
        
        return list(songs)


class SongSelectionError(Exception):
    """Raised when song selection fails."""
    pass
