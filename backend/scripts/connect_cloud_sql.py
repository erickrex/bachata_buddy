#!/usr/bin/env python3
"""
Connect to existing Cloud SQL database (read-only) and document schema.

This script connects to the existing Cloud SQL database used by the monolithic app
and documents all tables, columns, and relationships needed for the migration.

Usage:
    python connect_cloud_sql.py

Requirements:
    - Cloud SQL Proxy running locally OR direct connection to Cloud SQL
    - Database credentials in environment variables
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(env_path)


def get_db_connection():
    """
    Get database connection to existing Cloud SQL database.
    
    Returns:
        psycopg2 connection object
    """
    db_config = {
        'dbname': os.environ.get('DB_NAME', 'bachata_vibes'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD'),
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432'),
    }
    
    print(f"Connecting to database: {db_config['dbname']}")
    print(f"Host: {db_config['host']}:{db_config['port']}")
    print(f"User: {db_config['user']}")
    
    try:
        conn = psycopg2.connect(**db_config)
        print("✅ Successfully connected to Cloud SQL database!")
        return conn
    except psycopg2.Error as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


def get_all_tables(conn):
    """Get list of all tables in the database."""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        return [row['table_name'] for row in cursor.fetchall()]


def get_table_columns(conn, table_name):
    """Get detailed column information for a table."""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        return cursor.fetchall()


def get_table_constraints(conn, table_name):
    """Get constraints (primary keys, foreign keys, unique) for a table."""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # Primary keys
        cursor.execute("""
            SELECT 
                kcu.column_name,
                tc.constraint_type
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'public'
            AND tc.table_name = %s
            AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE');
        """, (table_name,))
        constraints = cursor.fetchall()
        
        # Foreign keys
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON rc.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            AND tc.table_name = %s;
        """, (table_name,))
        foreign_keys = cursor.fetchall()
        
        return constraints, foreign_keys


def get_table_indexes(conn, table_name):
    """Get indexes for a table."""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename = %s;
        """, (table_name,))
        return cursor.fetchall()


def get_table_row_count(conn, table_name):
    """Get approximate row count for a table."""
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        return cursor.fetchone()[0]


def document_schema(conn):
    """Document the complete database schema."""
    print("\n" + "="*80)
    print("DATABASE SCHEMA DOCUMENTATION")
    print("="*80)
    
    tables = get_all_tables(conn)
    print(f"\nFound {len(tables)} tables in database")
    
    # Focus on key tables for migration
    key_tables = [
        'choreography_choreographytask',
        'choreography_savedchoreography',
        'auth_user',
        'users_user',
    ]
    
    print("\n" + "-"*80)
    print("KEY TABLES FOR MIGRATION")
    print("-"*80)
    
    for table_name in tables:
        if any(key in table_name for key in ['choreography', 'user', 'auth']):
            print(f"\n📋 Table: {table_name}")
            print("-" * 80)
            
            # Get row count
            try:
                row_count = get_table_row_count(conn, table_name)
                print(f"   Rows: {row_count}")
            except Exception as e:
                print(f"   Rows: Unable to count ({e})")
            
            # Get columns
            columns = get_table_columns(conn, table_name)
            print(f"\n   Columns ({len(columns)}):")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"      - {col['column_name']}: {col['data_type']}{max_len} {nullable}{default}")
            
            # Get constraints
            constraints, foreign_keys = get_table_constraints(conn, table_name)
            if constraints:
                print(f"\n   Constraints:")
                for constraint in constraints:
                    print(f"      - {constraint['constraint_type']}: {constraint['column_name']}")
            
            if foreign_keys:
                print(f"\n   Foreign Keys:")
                for fk in foreign_keys:
                    print(f"      - {fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
                    print(f"        ON UPDATE {fk['update_rule']}, ON DELETE {fk['delete_rule']}")
            
            # Get indexes
            indexes = get_table_indexes(conn, table_name)
            if indexes:
                print(f"\n   Indexes ({len(indexes)}):")
                for idx in indexes:
                    print(f"      - {idx['indexname']}")
    
    print("\n" + "="*80)
    print("ALL TABLES IN DATABASE")
    print("="*80)
    for table_name in tables:
        try:
            row_count = get_table_row_count(conn, table_name)
            print(f"   - {table_name} ({row_count} rows)")
        except Exception as e:
            print(f"   - {table_name} (unable to count rows)")


def test_read_choreography_tasks(conn):
    """Test reading from choreography_tasks table."""
    print("\n" + "="*80)
    print("TEST: Reading ChoreographyTask records")
    print("="*80)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Try different possible table names
            possible_names = [
                'choreography_choreographytask',
                'choreography_tasks',
                'choreographytask'
            ]
            
            table_found = False
            for table_name in possible_names:
                try:
                    cursor.execute(f"""
                        SELECT task_id, status, created_at, updated_at
                        FROM {table_name}
                        ORDER BY created_at DESC
                        LIMIT 5;
                    """)
                    tasks = cursor.fetchall()
                    table_found = True
                    print(f"\n✅ Found table: {table_name}")
                    print(f"   Recent tasks ({len(tasks)}):")
                    for task in tasks:
                        print(f"      - {task['task_id']}: {task['status']} (created: {task['created_at']})")
                    break
                except psycopg2.Error:
                    continue
            
            if not table_found:
                print("⚠️  Could not find choreography tasks table")
                print("   Tried: " + ", ".join(possible_names))
    
    except Exception as e:
        print(f"❌ Error reading choreography tasks: {e}")


def test_read_saved_choreographies(conn):
    """Test reading from saved_choreographies table."""
    print("\n" + "="*80)
    print("TEST: Reading SavedChoreography records")
    print("="*80)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Try different possible table names
            possible_names = [
                'choreography_savedchoreography',
                'saved_choreographies',
                'savedchoreography'
            ]
            
            table_found = False
            for table_name in possible_names:
                try:
                    cursor.execute(f"""
                        SELECT id, title, difficulty, created_at
                        FROM {table_name}
                        ORDER BY created_at DESC
                        LIMIT 5;
                    """)
                    choreographies = cursor.fetchall()
                    table_found = True
                    print(f"\n✅ Found table: {table_name}")
                    print(f"   Recent choreographies ({len(choreographies)}):")
                    for choreo in choreographies:
                        print(f"      - {choreo['title']}: {choreo['difficulty']} (created: {choreo['created_at']})")
                    break
                except psycopg2.Error:
                    continue
            
            if not table_found:
                print("⚠️  Could not find saved choreographies table")
                print("   Tried: " + ", ".join(possible_names))
    
    except Exception as e:
        print(f"❌ Error reading saved choreographies: {e}")


def main():
    """Main function."""
    print("="*80)
    print("CLOUD SQL DATABASE CONNECTION TEST (READ-ONLY)")
    print("="*80)
    print("\nThis script connects to the existing Cloud SQL database")
    print("and documents the schema for the microservices migration.")
    print("\nNOTE: This is a READ-ONLY operation. No data will be modified.")
    print("="*80)
    
    # Get database connection
    conn = get_db_connection()
    
    try:
        # Set connection to read-only mode
        conn.set_session(readonly=True, autocommit=True)
        print("✅ Connection set to READ-ONLY mode")
        
        # Document schema
        document_schema(conn)
        
        # Test reading key tables
        test_read_choreography_tasks(conn)
        test_read_saved_choreographies(conn)
        
        print("\n" + "="*80)
        print("✅ DATABASE CONNECTION TEST COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nNext steps:")
        print("1. Review the schema documentation above")
        print("2. Document findings in backend/EXISTING_SCHEMA.md")
        print("3. Create model mapping in backend/MODEL_REUSE_STRATEGY.md")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error during schema documentation: {e}")
        sys.exit(1)
    
    finally:
        conn.close()
        print("\n✅ Database connection closed")


if __name__ == '__main__':
    main()
