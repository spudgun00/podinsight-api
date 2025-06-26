#!/usr/bin/env python3
"""
Check what tables exist in the Supabase database and their structures
"""

import os
from supabase import create_client

# Get Supabase credentials from environment
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
    exit(1)

supabase = create_client(url, key)

print("Checking database tables...")

# Common table names to check
table_names = [
    'episodes', 'topic_mentions', 'transcripts', 'podcasts', 'feeds',
    'episode_metadata', 'podcast_metadata', 'segments', 'entities',
    'public.episodes', 'public.topic_mentions'
]

existing_tables = []
table_structures = {}

for table in table_names:
    try:
        # Try to get schema info by selecting one record
        response = supabase.table(table).select("*").limit(1).execute()

        if response.data is not None:  # Table exists (even if empty)
            existing_tables.append(table)

            if len(response.data) > 0:
                # Get column names and types from first record
                sample = response.data[0]
                table_structures[table] = {
                    'columns': list(sample.keys()),
                    'sample_record': sample,
                    'record_count': 'has_data'
                }
            else:
                # Table exists but is empty
                table_structures[table] = {
                    'columns': [],
                    'sample_record': None,
                    'record_count': 0
                }

            print(f"✅ Found table: {table}")

    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg or '42P01' in error_msg:
            print(f"❌ Table {table} does not exist")
        else:
            print(f"❌ Error checking {table}: {error_msg[:100]}...")

print(f"\n\nFOUND {len(existing_tables)} TABLES:")
print("="*50)

for table in existing_tables:
    print(f"\nTable: {table}")
    structure = table_structures.get(table, {})

    if structure.get('columns'):
        print(f"  Columns ({len(structure['columns'])}): {', '.join(structure['columns'])}")

        # Show title-related fields
        title_fields = [col for col in structure['columns'] if 'title' in col.lower() or 'name' in col.lower()]
        if title_fields:
            print(f"  Title/Name fields: {title_fields}")

            # Show sample values for title fields
            sample = structure.get('sample_record', {})
            if sample:
                for field in title_fields:
                    value = sample.get(field, 'N/A')
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"    {field}: {value}")
    else:
        print(f"  Empty table or no accessible columns")

# Check if topic_mentions has episode reference data
if 'topic_mentions' in existing_tables:
    print(f"\n\nTOPIC_MENTIONS ANALYSIS:")
    print("-" * 30)

    try:
        response = supabase.table("topic_mentions").select("*").limit(3).execute()
        if response.data:
            print(f"Sample topic mentions:")
            for i, mention in enumerate(response.data[:3], 1):
                print(f"\n{i}. Topic Mention:")
                for key, value in mention.items():
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    print(f"   {key}: {value}")
    except Exception as e:
        print(f"Error analyzing topic_mentions: {e}")

print("\nDone!")
