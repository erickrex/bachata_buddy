#!/usr/bin/env python3
"""
Database initialization script for the Bachata Choreography Generator.

This script initializes the SQLite database and creates all necessary tables.
It can be run standalone or imported as a module.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import init_database, get_database_info
from app.models.database_models import User, SavedChoreography, ClassPlan, ClassPlanSequence


def main():
    """Initialize the database and display information."""
    print("Initializing Bachata Choreography Generator database...")
    
    try:
        # Initialize the database (create tables)
        init_database()
        print("✅ Database initialized successfully!")
        
        # Display database information
        db_info = get_database_info()
        print(f"\n📊 Database Information:")
        print(f"   Path: {db_info['database_path']}")
        print(f"   Exists: {db_info['database_exists']}")
        print(f"   Size: {db_info['database_size_mb']} MB")
        
        # Display table information
        print(f"\n📋 Created Tables:")
        print(f"   - users (authentication and user management)")
        print(f"   - saved_choreographies (user's saved choreographies)")
        print(f"   - class_plans (instructor class planning)")
        print(f"   - class_plan_sequences (choreography sequences in class plans)")
        
        print(f"\n🎉 Database is ready for use!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()