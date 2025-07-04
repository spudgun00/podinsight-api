#!/usr/bin/env python3
"""
Get all Supabase tables and their schemas
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from supabase import create_client

def get_all_tables():
    # Create Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        print("❌ Supabase configuration not found in environment")
        return

    client = create_client(url, key)

    print("🔍 Getting all Supabase tables...\n")

    # Query information_schema to get all tables
    try:
        # Get table list using a simple query trick
        # Try to query common table names
        tables_to_check = ['episodes', 'podcasts', 'transcripts', 'transcript_chunks', 
                          'embeddings', 'metadata', 'chunks', 'segments', 'entities',
                          'kpis', 'sentiment', 'topics', 'guests', 'hosts', 'audio_clips']
        
        found_tables = []
        
        for table_name in tables_to_check:
            try:
                result = client.table(table_name).select("*").limit(1).execute()
                if result.data is not None:
                    found_tables.append(table_name)
                    print(f"✅ Found table: {table_name}")
                    
                    # Get sample data
                    if result.data:
                        print(f"   Columns: {list(result.data[0].keys())}")
                        print(f"   Sample row:")
                        for key, value in result.data[0].items():
                            if isinstance(value, str) and len(str(value)) > 100:
                                print(f"     - {key}: {str(value)[:100]}...")
                            else:
                                print(f"     - {key}: {value}")
                    print()
            except Exception as e:
                # Table doesn't exist
                pass
        
        print(f"\n📊 Summary: Found {len(found_tables)} tables")
        print(f"Tables: {', '.join(found_tables)}")
        
        # For each found table, get more details
        print("\n\n=== DETAILED TABLE INFORMATION ===")
        for table in found_tables:
            print(f"\n📋 Table: {table}")
            print("-" * 50)
            
            # Get count
            count_result = client.table(table).select("*", count="exact").execute()
            print(f"Total rows: {count_result.count}")
            
            # Get 2 sample rows
            samples = client.table(table).select("*").limit(2).execute()
            if samples.data:
                print(f"\nSample documents:")
                for i, doc in enumerate(samples.data):
                    print(f"\nRow {i+1}:")
                    for key, value in doc.items():
                        if isinstance(value, str) and len(str(value)) > 80:
                            print(f"  {key}: {str(value)[:80]}...")
                        elif isinstance(value, list) and len(value) > 3:
                            print(f"  {key}: [{value[0]}, {value[1]}, ... {len(value)} items]")
                        else:
                            print(f"  {key}: {value}")
                            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_all_tables()