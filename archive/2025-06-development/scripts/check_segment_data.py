#!/usr/bin/env python3
"""
Check what data came from segment files
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.podinsight

print('🔍 CHECKING WHAT CAME FROM SEGMENT FILES')
print('=' * 60)

# The chunks collection was created from segment files
chunk = db.transcript_chunks_768d.find_one()

print('\nFields in transcript_chunks_768d (from segment files):')
for field in sorted(chunk.keys()):
    if field not in ['embedding_768d', '_id']:
        value = chunk[field]
        if isinstance(value, str) and len(value) > 50:
            value = value[:50] + '...'
        print(f'  - {field}: {value}')

print('\n❌ No GUID field found!')

print('\n📁 S3 STRUCTURE REMINDER:')
print('According to S3_BUCKET_STRUCTURE_CORRECTED.md:')
print('  - Segments stored as: segments/<guid>.json')
print('  - Embeddings stored as: embeddings/<guid>.npy')
print('  - Both use GUID as filename!')

print('\n🤔 THE ISSUE:')
print('1. S3 files are named with GUIDs: segments/1216c2e7-42b8-42ca-92d7-bad784f80af2.json')
print('2. But the GUID wasn\'t stored INSIDE the MongoDB documents')
print('3. Instead, new random episode_ids were generated')

print('\n💡 WHAT THIS MEANS:')
print('- The segment FILES have GUIDs (in their filenames)')
print('- The segment CONTENT doesn\'t include the GUID')
print('- When ETL read the files, it didn\'t preserve the filename GUID')
print('- This is why we have random episode_ids instead of the original GUIDs')

# Let's verify by checking if episode_ids look like GUIDs
print('\n🔍 Checking episode_id format:')
sample_ids = list(db.transcript_chunks_768d.distinct('episode_id')[:5])
for id in sample_ids:
    print(f'  {id} (looks like a GUID)')

# Check if the episode_ids in chunks match S3 GUIDs
print('\n🔍 Checking if these match S3 GUIDs:')
print('  If ETL had preserved S3 filenames as episode_ids:')
print('  - episode_id would be: 1216c2e7-42b8-42ca-92d7-bad784f80af2')
print('  - Actual episode_id is: ' + chunk['episode_id'])
print('  - THEY DON\'T MATCH! ETL generated new IDs')

client.close()
