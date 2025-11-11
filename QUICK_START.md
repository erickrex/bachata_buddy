# 🚀 Quick Start - Run the App and Create Videos

Your containers are already running! Here's how to use the app:

## ✅ Current Status

```bash
✓ API Backend:  http://localhost:8001
✓ Frontend:     http://localhost:5173
✓ Database:     PostgreSQL on port 5432
✓ Embeddings:   149 moves loaded in database
```

## 🎬 Create Your First Video

### Option 1: Use the Web Interface (Easiest)

1. **Open the app in your browser:**
   ```
   http://localhost:5173
   ```

2. **Login or create an account:**
   - Click "Sign Up" if you don't have an account
   - Or login with existing credentials

3. **Generate a choreography:**
   - Click "Generate Choreography" or "Create New"
   - Choose a song from the dropdown
   - Select difficulty (beginner/intermediate/advanced)
   - Select energy level (low/medium/high)
   - Select style (romantic/energetic/sensual/playful)
   - Click "Generate"

4. **Wait for video generation:**
   - Progress bar will show status
   - Takes about 40-50 seconds
   - Video will auto-save to your collection

5. **Watch your video:**
   - Click on the generated choreography
   - Video player will show your custom bachata routine!

### Option 2: Use the API Directly

```bash
# 1. Get authentication token
curl -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Save the access token from response

# 2. Generate choreography from song
curl -X POST http://localhost:8001/api/choreography/generate-from-song/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": 1,
    "difficulty": "intermediate",
    "energy_level": "medium",
    "style": "romantic"
  }'

# 3. Check task status (use task_id from response)
curl http://localhost:8001/api/choreography/task-status/TASK_ID/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 4. When complete, video will be at:
# http://localhost:8001/media/choreographies/user_X/TASK_ID.mp4
```

### Option 3: Use Natural Language (AI-Powered)

```bash
curl -X POST http://localhost:8001/api/choreography/generate-with-ai/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a romantic intermediate bachata with smooth flowing moves"
  }'
```

## 📊 Check Your Collections

```bash
# List all your choreographies
curl http://localhost:8001/api/collections/choreographies/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Get specific choreography
curl http://localhost:8001/api/collections/choreographies/CHOREO_ID/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🎵 Available Songs

Check what songs are available:

```bash
curl http://localhost:8001/api/choreography/songs/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Or check the `data/songs/` directory:
```bash
ls -la data/songs/
```

## 🔧 Useful Commands

### Check if everything is running:
```bash
docker-compose ps
```

### View API logs:
```bash
docker-compose logs -f api
```

### View frontend logs:
```bash
docker-compose logs -f frontend
```

### Restart services:
```bash
docker-compose restart api
docker-compose restart frontend
```

### Stop everything:
```bash
docker-compose down
```

### Start everything:
```bash
docker-compose up -d
```

## 🐛 Troubleshooting

### "No embeddings found" error
```bash
# Load embeddings into database
docker-compose exec api python load_embeddings_from_json.py
```

### "Song not found" error
```bash
# Check available songs
ls -la data/songs/

# Make sure songs are in the database
docker-compose exec api python manage.py shell -c "
from apps.choreography.models import Song
print(f'Songs in DB: {Song.objects.count()}')
for song in Song.objects.all():
    print(f'  - {song.title} by {song.artist}')
"
```

### Frontend not loading
```bash
# Restart frontend
docker-compose restart frontend

# Check logs
docker-compose logs frontend
```

### API not responding
```bash
# Restart API
docker-compose restart api

# Check logs
docker-compose logs api
```

### Database connection issues
```bash
# Restart database
docker-compose restart db

# Check database is healthy
docker-compose ps db
```

## 📹 Video Output

Generated videos are saved to:
```
data/output/user_YOUR_USER_ID/TASK_ID.mp4
```

Or accessible via:
```
http://localhost:8001/media/choreographies/user_YOUR_USER_ID/TASK_ID.mp4
```

## 🎯 Next Steps

1. **Add more songs**: Place MP3 files in `data/songs/` and add them to the database
2. **Customize moves**: Edit `data/bachata_annotations.json` to adjust move metadata
3. **Regenerate embeddings**: If you change videos, run `generate_embeddings_to_json.py`
4. **Explore the API**: Visit http://localhost:8001/api/docs/ for full API documentation

## 💡 Tips

- **Video quality**: Videos are generated at 1280x720, 24fps, ~51MB per video
- **Generation time**: Expect 40-50 seconds per choreography
- **Move variety**: 149 unique moves across 16 categories
- **Difficulty levels**: System automatically matches moves to your selected difficulty
- **Energy matching**: Moves are selected to match the song's energy curve

Enjoy creating bachata choreographies! 💃🕺
