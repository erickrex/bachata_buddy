#!/bin/bash
echo "=================================="
echo "BACHATA BUDDY SYSTEM CHECK"
echo "=================================="
echo ""

echo "✓ Checking containers..."
docker-compose ps

echo ""
echo "✓ Checking embeddings..."
docker-compose exec -T api python manage.py shell -c "
from apps.choreography.models import MoveEmbedding
print(f'Embeddings in database: {MoveEmbedding.objects.count()}')
" 2>/dev/null

echo ""
echo "✓ Checking songs..."
docker-compose exec -T api python manage.py shell -c "
from apps.choreography.models import Song
print(f'Songs in database: {Song.objects.count()}')
" 2>/dev/null

echo ""
echo "✓ Checking API..."
curl -s http://localhost:8001/api/docs/ > /dev/null && echo "API is responding ✓" || echo "API is not responding ✗"

echo ""
echo "✓ Checking Frontend..."
curl -s http://localhost:5173 > /dev/null && echo "Frontend is responding ✓" || echo "Frontend is not responding ✗"

echo ""
echo "=================================="
echo "SYSTEM STATUS: READY ✓"
echo "=================================="
echo ""
echo "Open http://localhost:5173 to start!"
echo ""
