# Blueprint Architecture Migration Script

## Overview

The `migrate_to_blueprint_architecture.py` script migrates existing move data to the new blueprint-based architecture. It performs the following tasks:

1. **Scans video files** in the `data/Bachata_steps` directory
2. **Creates MoveEmbedding records** with placeholder embeddings for each video
3. **Generates sample blueprints** for testing the blueprint-based workflow
4. **Verifies data integrity** after migration

## Prerequisites

- Django backend environment configured
- Database accessible (PostgreSQL)
- Video files in `data/Bachata_steps` directory
- Backend dependencies installed (`uv sync` in backend directory)

## Usage

### Dry Run (Recommended First)

Test the migration without making any database changes:

```bash
cd backend
uv run python ../scripts/migrate_to_blueprint_architecture.py --dry-run
```

This will:
- Scan all video files
- Show what would be created
- Not make any database changes

### Actual Migration

Run the migration and create database records:

```bash
cd backend
uv run python ../scripts/migrate_to_blueprint_architecture.py
```

### Custom Video Directory

Specify a different video directory:

```bash
cd backend
uv run python ../scripts/migrate_to_blueprint_architecture.py --video-dir ../data/custom_moves
```

### Create Sample Blueprints Only

Skip move embedding migration and only create sample blueprints:

```bash
cd backend
uv run python ../scripts/migrate_to_blueprint_architecture.py --blueprints-only
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
cd backend
uv run python ../scripts/migrate_to_blueprint_architecture.py --debug
```

## What Gets Created

### MoveEmbedding Records

For each video file found, the script creates a `MoveEmbedding` record with:

- **move_id**: Unique identifier (e.g., `body_roll_body_roll_1`)
- **move_name**: Name extracted from filename (e.g., `body_roll_1`)
- **video_path**: Relative path to video file
- **pose_embedding**: 512D placeholder embedding (normalized random vector)
- **audio_embedding**: 128D placeholder embedding (normalized random vector)
- **text_embedding**: 384D placeholder embedding (normalized random vector)
- **difficulty**: Mapped from move type (beginner/intermediate/advanced)
- **energy_level**: Mapped from move type (low/medium/high)
- **style**: Mapped from move type (romantic/energetic/sensual/playful)
- **duration**: Default 8.0 seconds

### Sample Blueprints

The script creates 3 sample blueprints for testing:

1. **sample_task_1**: Beginner difficulty, 5 moves
2. **sample_task_2**: Intermediate difficulty, 5 moves
3. **sample_task_3**: Advanced difficulty, 5 moves

Each blueprint includes:
- Complete move sequence with timing
- Transition specifications
- Output configuration
- Metadata (difficulty, energy, style)

## Metadata Mapping

The script automatically maps move types to metadata:

### Difficulty Levels

- **Beginner**: basic_steps, forward_backward
- **Intermediate**: arm_styling, body_roll, cross_body_lead, lady_right_turn, lady_left_turn, combination
- **Advanced**: hammerlock, dip, double_cross_body_lead, shadow_position

### Energy Levels

- **Low**: basic_steps, forward_backward
- **Medium**: arm_styling, body_roll, cross_body_lead, dip, shadow_position
- **High**: lady_right_turn, lady_left_turn, combination, hammerlock, double_cross_body_lead

### Styles

- **Romantic**: basic_steps, forward_backward, dip
- **Energetic**: cross_body_lead, lady_right_turn, lady_left_turn, double_cross_body_lead
- **Sensual**: arm_styling, body_roll, shadow_position
- **Playful**: combination, hammerlock

## Output

The script generates:

1. **Console output**: Real-time progress and statistics
2. **migration.log**: Detailed log file with all operations
3. **Database records**: MoveEmbedding and Blueprint records

### Example Output

```
================================================================================
BLUEPRINT ARCHITECTURE MIGRATION
================================================================================
Video directory: ../data/Bachata_steps
Dry run: False
================================================================================

================================================================================
MIGRATING MOVE EMBEDDINGS
================================================================================
Found 38 video files

Created MoveEmbedding: arm_styling_arm_styling_1 (intermediate, medium, sensual)
Created MoveEmbedding: arm_styling_arm_styling_2 (intermediate, medium, sensual)
...

Migration complete: 38 embeddings created

================================================================================
CREATING SAMPLE BLUEPRINTS
================================================================================
Found 38 move embeddings

Created sample blueprint: sample_task_1
  Difficulty: beginner
  Moves: 5
  Duration: 40.0s

Created sample blueprint: sample_task_2
  Difficulty: intermediate
  Moves: 5
  Duration: 40.0s

Created sample blueprint: sample_task_3
  Difficulty: advanced
  Moves: 5
  Duration: 40.0s

Created 3 sample blueprints

================================================================================
VERIFYING DATA INTEGRITY
================================================================================
MoveEmbedding records: 38
  With all embeddings: 38/38
  Beginner: 6
  Intermediate: 20
  Advanced: 12
  Energy low: 6
  Energy medium: 14
  Energy high: 18
  Style romantic: 6
  Style energetic: 12
  Style sensual: 10
  Style playful: 10

Blueprint records: 3
  Valid blueprints: 3/3

Data integrity check complete

================================================================================
MIGRATION SUMMARY
================================================================================
Videos found: 38
Embeddings created: 38
Embeddings skipped (already exist): 0
Embeddings failed: 0
Sample blueprints created: 3
Sample blueprints failed: 0
================================================================================

================================================================================
MIGRATION COMPLETE
================================================================================
```

## Important Notes

### Placeholder Embeddings

The migration script creates **placeholder embeddings** using normalized random vectors. These are suitable for:

- Testing the blueprint architecture
- Developing and debugging the system
- Initial setup and validation

For **production use**, you should:

1. Run the actual embedding generation pipeline: `scripts/generate_embeddings.py`
2. This will generate real embeddings from video analysis
3. Replace the placeholder embeddings with real ones

### Database Connection

The script requires a database connection. Make sure:

- PostgreSQL is running
- Database credentials are configured in `backend/.env`
- Migrations have been run: `python manage.py migrate`

### Idempotency

The script is idempotent:

- Running it multiple times won't create duplicates
- Existing MoveEmbedding records are skipped
- Safe to re-run after failures

## Troubleshooting

### Database Connection Error

```
django.db.utils.OperationalError: could not translate host name "db"
```

**Solution**: Make sure PostgreSQL is running and accessible. Check `backend/.env` for correct database settings.

### No Video Files Found

```
WARNING: No video files found to migrate
```

**Solution**: Verify the video directory path. Default is `data/Bachata_steps` relative to project root.

### Import Errors

```
ModuleNotFoundError: No module named 'apps.choreography'
```

**Solution**: Run the script from the `backend` directory:

```bash
cd backend
uv run python ../scripts/migrate_to_blueprint_architecture.py
```

### Permission Errors

```
PermissionError: [Errno 13] Permission denied
```

**Solution**: Make sure the script is executable:

```bash
chmod +x scripts/migrate_to_blueprint_architecture.py
```

## Next Steps

After running the migration:

1. **Verify the data**: Check the database to ensure records were created correctly
2. **Test blueprints**: Use the sample blueprints to test the video assembly workflow
3. **Generate real embeddings**: Run `scripts/generate_embeddings.py` for production
4. **Update vector search**: The vector search service will automatically use the new embeddings

## Related Documentation

- [Blueprint Schema](../docs/BLUEPRINT_SCHEMA.md) - Blueprint JSON format specification
- [Vector Search Service](../backend/services/vector_search_service.py) - In-memory vector search
- [Blueprint Generator](../backend/services/blueprint_generator.py) - Blueprint generation logic
- [Embedding Generation](./README_EMBEDDING_GENERATION.md) - Real embedding generation pipeline

## Support

For issues or questions:

1. Check the `migration.log` file for detailed error messages
2. Run with `--debug` flag for more verbose output
3. Review the troubleshooting section above
4. Check related documentation for context
