# Sample Songs Directory

This directory contains audio files for local development and testing of the song template workflow.

## Purpose

The song template workflow allows users to select from pre-existing songs and generate choreography videos. During local development, audio files are stored in this directory. In production, they are stored in Google Cloud Storage (GCS).

## Adding Sample Audio Files

To test the song template workflow locally, you need to add MP3 audio files to this directory.

### Required Files

Based on the fixtures in `backend/fixtures/songs.json`, the following files are expected:

1. `bachata-rosa.mp3` - Bachata Rosa by Juan Luis Guerra
2. `obsesion.mp3` - Obsesión by Aventura
3. `dile-al-amor.mp3` - Dile al Amor by Aventura
4. `propuesta-indecente.mp3` - Propuesta Indecente by Romeo Santos
5. `me-enamora.mp3` - Me Enamora by Toby Love

### How to Add Files

1. **Option 1: Use Your Own Audio Files**
   - Place any bachata MP3 files in this directory
   - Update the fixture file paths to match your filenames
   - Load the fixtures: `python manage.py loaddata songs`

2. **Option 2: Download Sample Songs**
   - Download bachata songs from legal sources (YouTube Audio Library, Free Music Archive, etc.)
   - Rename them to match the fixture filenames above
   - Place them in this directory

3. **Option 3: Use Placeholder Files**
   - For testing without actual audio, you can create empty placeholder files:
     ```bash
     touch bachata-rosa.mp3 obsesion.mp3 dile-al-amor.mp3 propuesta-indecente.mp3 me-enamora.mp3
     ```
   - Note: The choreography generation will fail without valid audio, but you can test the API endpoints

## Loading Sample Data

After adding audio files, load the song fixtures into the database:

```bash
cd backend
python manage.py loaddata songs
```

This will create 5 song records in the database pointing to the audio files in this directory.

## File Format Requirements

- **Format**: MP3 (recommended)
- **Bitrate**: 128kbps or higher
- **Sample Rate**: 44.1kHz or 48kHz
- **Duration**: 3-5 minutes typical for bachata songs

## Testing the Workflow

Once you've loaded the fixtures, you can test the song template workflow:

1. **List songs**: `GET /api/choreography/songs/`
2. **Get song details**: `GET /api/choreography/songs/1/`
3. **Generate choreography**: `POST /api/choreography/generate-from-song/`
   ```json
   {
     "song_id": 1,
     "difficulty": "beginner"
   }
   ```

## Production Deployment

In production, audio files are stored in Google Cloud Storage. The `audio_path` field in the Song model supports both formats:

- **Local**: `songs/bachata-rosa.mp3`
- **GCS**: `gs://bachata-buddy-bucket/songs/bachata-rosa.mp3`

When deploying to production, update the song records to use GCS paths.

## .gitignore

Audio files in this directory are ignored by git (see `.gitignore`). This prevents large binary files from being committed to the repository.
