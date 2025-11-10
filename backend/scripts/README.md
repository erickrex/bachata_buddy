# Backend Scripts

This directory contains utility scripts for the backend API migration.

## Database Connection Scripts

### connect_cloud_sql.py

Connects to the existing Cloud SQL database (read-only) and documents the schema.

**Purpose:**
- Document existing database schema from monolithic app
- Identify tables, columns, and relationships
- Test read access to key tables
- Generate schema documentation for migration

**Usage:**

```bash
# From backend directory
cd backend

# Run the script with uv
uv run scripts/connect_cloud_sql.py
```

**Prerequisites:**

1. **Cloud SQL Proxy** (recommended for secure connection):
   ```bash
   # Install Cloud SQL Proxy
   curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64
   chmod +x cloud-sql-proxy
   
   # Start proxy (replace with your connection name)
   ./cloud-sql-proxy bachata-buddy:us-central1:bachata-db --port 5432
   ```

2. **Environment Variables** (in `bachata_buddy/.env`):
   ```bash
   DB_NAME=bachata_vibes
   DB_USER=postgres
   DB_PASSWORD=your-password
   DB_HOST=localhost  # or 127.0.0.1 if using Cloud SQL Proxy
   DB_PORT=5432
   ```

3. **Database Credentials**:
   - Get credentials from Google Cloud Console
   - Or ask team member with access

**Output:**

The script will:
1. Connect to the database in READ-ONLY mode
2. List all tables in the database
3. Document key tables for migration:
   - choreography_choreographytask
   - choreography_savedchoreography
   - auth_user / users_user
4. Show column details, constraints, foreign keys, and indexes
5. Test reading recent records from key tables

**Next Steps:**

After running this script:
1. Review the schema documentation output
2. Document findings in `backend/EXISTING_SCHEMA.md`
3. Create model mapping in `backend/MODEL_REUSE_STRATEGY.md`
4. Proceed to task 0.2: Create Model Mapping Strategy

## Troubleshooting

### Connection Refused

If you get "connection refused" error:
- Make sure Cloud SQL Proxy is running
- Check DB_HOST and DB_PORT in .env file
- Verify database credentials

### Permission Denied

If you get "permission denied" error:
- Verify database user has SELECT permissions
- Check that user can connect from your IP address
- Ensure Cloud SQL instance allows connections

### Table Not Found

If tables are not found:
- Verify you're connecting to the correct database
- Check that migrations have been run on the database
- Confirm table names match Django model Meta.db_table settings
