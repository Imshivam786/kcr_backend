# create_db.py
"""
Script to create the PostgreSQL database and tables if they don't exist
Run this before starting the application for the first time
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine
from config import settings
from models.database import Base

def create_database():
    """Create the database if it doesn't exist"""
    # Connect to PostgreSQL server (to 'postgres' database)
    try:
        print(f"Connecting to PostgreSQL at {settings.DATABASE_HOST}:{settings.DATABASE_PORT}...")
        conn = psycopg2.connect(
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            f"SELECT 1 FROM pg_database WHERE datname = '{settings.DATABASE_NAME}'"
        )
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE {settings.DATABASE_NAME}')
            print(f"✓ Database '{settings.DATABASE_NAME}' created successfully")
        else:
            print(f"✓ Database '{settings.DATABASE_NAME}' already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        raise

def create_tables():
    """Create all tables defined in SQLAlchemy models"""
    try:
        print(f"\nCreating tables in database '{settings.DATABASE_NAME}'...")
        
        # Create engine connected to our database
        engine = create_engine(settings.DATABASE_URL, echo=True)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("\n✓ All tables created successfully!")
        
        # Print created tables
        print("\nCreated tables:")
        for table in Base.metadata.tables.keys():
            print(f"  - {table}")
        
        engine.dispose()
        
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        raise

def verify_setup():
    """Verify database and tables were created"""
    try:
        print("\nVerifying database setup...")
        conn = psycopg2.connect(
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME
        )
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"\n✓ Verification successful! Found {len(tables)} table(s):")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\n⚠ No tables found in the database")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error during verification: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("PostgreSQL Database Setup for Kannada OCR Application")
    print("=" * 60)
    
    # Step 1: Create database
    create_database()
    
    # Step 2: Create tables
    create_tables()
    
    # Step 3: Verify setup
    verify_setup()
    
    print("\n" + "=" * 60)
    print("Database setup complete! You can now start your application.")
    print("=" * 60)
