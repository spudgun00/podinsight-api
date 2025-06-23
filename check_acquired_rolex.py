import os
import asyncio
import json
import boto3
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.podinsight
collection = db.transcript_chunks_768d

# S3 setup
s3_client = boto3.client('s3')
BUCKET_NAME = 'pod-insights-stage'

# The specific "Rolex episode" mentioned in reports
ROLEX_EPISODE_ID = "94dbf581-80c1-49e4-a4ba-36fbbdad3c2a"

async def check_specific_episodes():
    """Check specific episodes that were mentioned in reports"""
    
    print("="*70)
    print("CHECKING SPECIFIC EPISODES FROM REPORTS")
    print("="*70)
    
    # 1. Check the Rolex episode (Acquired podcast)
    print(f"\n1. ROLEX EPISODE (Acquired): {ROLEX_EPISODE_ID}")
    
    # Get MongoDB chunks
    chunks = await collection.find(
        {"episode_id": ROLEX_EPISODE_ID}
    ).sort("start_time", 1).to_list(None)
    
    if chunks:
        print(f"   MongoDB chunks: {len(chunks)}")
        duration = chunks[-1]['end_time'] - chunks[0]['start_time']
        print(f"   Duration: {duration/60:.1f} minutes")
    else:
        print("   ❌ Not found in MongoDB")
    
    # Check S3
    try:
        s3_key = f"acquired/{ROLEX_EPISODE_ID}/segments/{ROLEX_EPISODE_ID}.json"
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        content = response['Body'].read()
        data = json.loads(content)
        segments = len(data) if isinstance(data, list) else len(data.get('segments', []))
        print(f"   S3 segments: {segments}")
        print(f"   ✅ MATCH: Both have {segments} segments" if segments == len(chunks) else f"   ❌ MISMATCH!")
    except:
        print("   S3 data not found")
    
    # 2. Look for any episodes with exactly 1082 segments in S3
    print("\n2. SEARCHING FOR EPISODES WITH ~1082 SEGMENTS...")
    
    # Get a sample of Acquired episodes
    acquired_episodes = await collection.aggregate([
        {"$match": {"feed_slug": "acquired"}},
        {"$group": {"_id": "$episode_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]).to_list(10)
    
    for ep in acquired_episodes:
        episode_id = ep['_id']
        mongodb_count = ep['count']
        
        # Check S3
        try:
            s3_key = f"acquired/{episode_id}/segments/{episode_id}.json"
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            content = response['Body'].read()
            data = json.loads(content)
            s3_count = len(data) if isinstance(data, list) else len(data.get('segments', []))
            
            print(f"   Episode {episode_id[:8]}...: MongoDB={mongodb_count}, S3={s3_count}")
            
            if s3_count > 1000 and mongodb_count < 200:
                print(f"   ⚠️  FOUND PATTERN: {s3_count} → {mongodb_count}")
                
        except:
            pass
    
    # 3. Check random high-segment episodes
    print("\n3. CHECKING HIGH-SEGMENT EPISODES...")
    
    high_segment_episodes = await collection.aggregate([
        {"$group": {"_id": "$episode_id", "count": {"$sum": 1}, "feed": {"$first": "$feed_slug"}}},
        {"$match": {"count": {"$gt": 3000}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]).to_list(None)
    
    for ep in high_segment_episodes:
        episode_id = ep['_id']
        feed = ep['feed']
        count = ep['count']
        print(f"   {feed} / {episode_id[:8]}...: {count} chunks in MongoDB")

async def main():
    await check_specific_episodes()
    
    # Final verification
    print("\n" + "="*70)
    print("FINAL VERIFICATION")
    print("="*70)
    
    # Count total episodes and chunks
    total_chunks = await collection.count_documents({})
    unique_episodes = await collection.distinct("episode_id")
    
    print(f"\nMongoDB Statistics:")
    print(f"  Total chunks: {total_chunks:,}")
    print(f"  Unique episodes: {len(unique_episodes):,}")
    print(f"  Average chunks per episode: {total_chunks/len(unique_episodes):.1f}")
    
    # Check for any episodes with suspiciously low chunk counts given their duration
    print("\n4. CHECKING FOR DURATION/CHUNK MISMATCHES...")
    
    pipeline = [
        {"$group": {
            "_id": "$episode_id",
            "chunk_count": {"$sum": 1},
            "total_duration": {"$max": "$end_time"},
            "feed": {"$first": "$feed_slug"}
        }},
        {"$addFields": {
            "chunks_per_minute": {"$divide": ["$chunk_count", {"$divide": ["$total_duration", 60]}]}
        }},
        {"$match": {
            "total_duration": {"$gt": 600},  # At least 10 minutes
            "chunks_per_minute": {"$lt": 1}   # Less than 1 chunk per minute (suspicious)
        }},
        {"$limit": 10}
    ]
    
    suspicious = await collection.aggregate(pipeline).to_list(None)
    
    if suspicious:
        print("\n⚠️  Episodes with suspiciously low chunk density:")
        for s in suspicious:
            print(f"   {s['feed']} / {s['_id'][:8]}...")
            print(f"     Duration: {s['total_duration']/60:.1f} min")
            print(f"     Chunks: {s['chunk_count']}")
            print(f"     Density: {s['chunks_per_minute']:.2f} chunks/min")
    else:
        print("   ✅ No episodes found with suspiciously low chunk density")

if __name__ == "__main__":
    asyncio.run(main())