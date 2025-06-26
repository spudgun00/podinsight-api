import os
import asyncio
import json
import boto3
import random
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.podinsight
collection = db.transcript_chunks_768d

# S3 setup
s3_client = boto3.client('s3')
BUCKET_NAME = 'pod-insights-stage'

async def get_episodes_to_check():
    """Get a diverse sample of episodes to check"""
    print("Selecting episodes for comprehensive check...")

    # Get episodes with different chunk counts
    pipeline = [
        {"$group": {
            "_id": "$episode_id",
            "chunk_count": {"$sum": 1},
            "feed_slug": {"$first": "$feed_slug"}
        }},
        {"$sort": {"chunk_count": 1}}
    ]

    all_episodes = await collection.aggregate(pipeline).to_list(None)

    # Select episodes from different ranges
    selected = []

    # Very low chunk count (potential problem episodes)
    low_chunks = [e for e in all_episodes if 50 < e['chunk_count'] < 200]
    if low_chunks:
        selected.extend(random.sample(low_chunks, min(3, len(low_chunks))))

    # Around 182 (the specific count we're investigating)
    around_182 = [e for e in all_episodes if 170 < e['chunk_count'] < 190]
    if around_182:
        selected.extend(random.sample(around_182, min(3, len(around_182))))

    # Medium chunk count
    medium = [e for e in all_episodes if 400 < e['chunk_count'] < 600]
    if medium:
        selected.extend(random.sample(medium, min(2, len(medium))))

    # High chunk count
    high = [e for e in all_episodes if 1000 < e['chunk_count'] < 2000]
    if high:
        selected.extend(random.sample(high, min(2, len(high))))

    return selected

async def analyze_episode(episode):
    """Comprehensive analysis of a single episode"""
    episode_id = episode['_id']
    feed_slug = episode['feed_slug']

    print(f"\n{'='*70}")
    print(f"ANALYZING: {feed_slug} / {episode_id}")
    print(f"{'='*70}")

    # Get MongoDB chunks
    chunks = await collection.find(
        {"episode_id": episode_id}
    ).sort("start_time", 1).to_list(None)

    print(f"\nMongoDB chunks: {len(chunks)}")

    if not chunks:
        return None

    # Calculate coverage
    first_start = chunks[0]['start_time']
    last_end = chunks[-1]['end_time']
    total_duration = last_end - first_start
    chunk_duration = sum(c['end_time'] - c['start_time'] for c in chunks)
    coverage = (chunk_duration / total_duration * 100) if total_duration > 0 else 0

    # Find gaps
    gaps = []
    for i in range(1, len(chunks)):
        gap = chunks[i]['start_time'] - chunks[i-1]['end_time']
        if gap > 0.1:
            gaps.append(gap)

    print(f"Duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"Coverage: {coverage:.1f}%")
    print(f"Gaps: {len(gaps)} (largest: {max(gaps):.1f}s)" if gaps else "Gaps: 0")

    # Try to find S3 source
    s3_segments = await find_s3_segments(feed_slug, episode_id)

    result = {
        'episode_id': episode_id,
        'feed_slug': feed_slug,
        'mongodb_chunks': len(chunks),
        's3_segments': s3_segments,
        'coverage': coverage,
        'duration': total_duration,
        'gaps': len(gaps)
    }

    if s3_segments:
        reduction = ((s3_segments - len(chunks)) / s3_segments * 100) if s3_segments > 0 else 0
        result['reduction'] = reduction

        print(f"\nCOMPARISON:")
        print(f"S3 segments: {s3_segments}")
        print(f"MongoDB chunks: {len(chunks)}")
        print(f"Difference: {reduction:.1f}% {'reduction' if reduction > 0 else 'increase'}")

        if reduction > 50:
            print("⚠️  SIGNIFICANT REDUCTION DETECTED!")

    return result

async def find_s3_segments(feed_slug, episode_id):
    """Try to find and count segments in S3"""
    # Common patterns for segment files
    patterns = [
        f"{feed_slug}/{episode_id}/segments/{episode_id}.json",
        f"{feed_slug}/{episode_id}/segments/{episode_id}_full.json",
    ]

    for s3_key in patterns:
        try:
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            content = response['Body'].read()
            data = json.loads(content)

            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict) and 'segments' in data:
                return len(data['segments'])

        except:
            continue

    # Also check raw transcript
    try:
        # List files to find raw transcript
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=f"{feed_slug}/{episode_id}/transcripts/",
            MaxKeys=10
        )

        if 'Contents' in response:
            for obj in response['Contents']:
                if 'raw_transcript.json' in obj['Key']:
                    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                    content = response['Body'].read()
                    data = json.loads(content)

                    if isinstance(data, dict) and 'segments' in data:
                        return len(data['segments'])
    except:
        pass

    return None

async def main():
    print("="*70)
    print("COMPREHENSIVE COVERAGE VERIFICATION")
    print("="*70)

    # Get episodes to check
    episodes = await get_episodes_to_check()
    print(f"\nSelected {len(episodes)} episodes for analysis")

    # Analyze each episode
    results = []
    problems = []

    for episode in episodes:
        result = await analyze_episode(episode)
        if result:
            results.append(result)

            # Check for problems
            if result.get('reduction', 0) > 50:
                problems.append(result)

    # Summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)

    print(f"\nTotal episodes analyzed: {len(results)}")

    # Coverage stats
    coverages = [r['coverage'] for r in results]
    print(f"\nCoverage statistics:")
    print(f"  Average: {sum(coverages)/len(coverages):.1f}%")
    print(f"  Min: {min(coverages):.1f}%")
    print(f"  Max: {max(coverages):.1f}%")

    # Reduction stats
    reductions = [r.get('reduction', 0) for r in results if 'reduction' in r]
    if reductions:
        print(f"\nReduction statistics (where S3 data found):")
        print(f"  Average: {sum(reductions)/len(reductions):.1f}%")
        print(f"  Max reduction: {max(reductions):.1f}%")

    # Problem episodes
    if problems:
        print(f"\n⚠️  EPISODES WITH >50% REDUCTION:")
        for p in problems:
            print(f"  {p['feed_slug']} / {p['episode_id']}")
            print(f"    S3: {p['s3_segments']} → MongoDB: {p['mongodb_chunks']} ({p['reduction']:.1f}% loss)")
    else:
        print(f"\n✅ NO EPISODES FOUND WITH SIGNIFICANT REDUCTION")

    # Look for the mythical 1082 → 182 pattern
    print(f"\n🔍 SEARCHING FOR 1082 → 182 PATTERN:")
    found_pattern = False
    for r in results:
        if r.get('s3_segments', 0) > 1000 and r['mongodb_chunks'] < 200:
            print(f"  FOUND: {r['feed_slug']} / {r['episode_id']}")
            print(f"    S3: {r['s3_segments']} → MongoDB: {r['mongodb_chunks']}")
            found_pattern = True

    if not found_pattern:
        print("  No episodes found with this pattern")

if __name__ == "__main__":
    asyncio.run(main())
