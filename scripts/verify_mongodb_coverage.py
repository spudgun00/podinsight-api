import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import statistics
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.podinsight
collection = db.transcript_chunks_768d

async def get_initial_stats():
    """Get overall statistics from MongoDB"""
    print("=" * 60)
    print("MONGODB INITIAL STATISTICS")
    print("=" * 60)
    
    # Total documents
    total_chunks = await collection.count_documents({})
    print(f"Total chunks: {total_chunks:,}")
    
    # Unique episodes
    pipeline = [
        {"$group": {"_id": "$episode_id"}},
        {"$count": "total_episodes"}
    ]
    result = await collection.aggregate(pipeline).to_list(None)
    total_episodes = result[0]['total_episodes'] if result else 0
    print(f"Total unique episodes: {total_episodes:,}")
    print(f"Average chunks per episode: {total_chunks / total_episodes:.1f}")
    
    # Chunks per episode distribution
    pipeline = [
        {"$group": {
            "_id": "$episode_id",
            "chunk_count": {"$sum": 1},
            "feed_slug": {"$first": "$feed_slug"}
        }},
        {"$sort": {"chunk_count": 1}}
    ]
    
    episodes = await collection.aggregate(pipeline).to_list(None)
    
    # Find episodes with low chunk counts
    low_chunk_episodes = [e for e in episodes if e['chunk_count'] < 200]
    high_chunk_episodes = [e for e in episodes if e['chunk_count'] > 1000]
    
    print(f"\nEpisodes with < 200 chunks: {len(low_chunk_episodes)}")
    print(f"Episodes with > 1000 chunks: {len(high_chunk_episodes)}")
    
    # Show some examples
    print("\nLowest chunk counts:")
    for ep in episodes[:10]:
        print(f"  {ep['feed_slug']} / {ep['_id'][:12]}... : {ep['chunk_count']} chunks")
    
    print("\nHighest chunk counts:")
    for ep in episodes[-10:]:
        print(f"  {ep['feed_slug']} / {ep['_id'][:12]}... : {ep['chunk_count']} chunks")
    
    # Look for the specific 182 chunk episode
    episode_182 = [e for e in episodes if e['chunk_count'] == 182]
    if episode_182:
        print(f"\nFound episode with exactly 182 chunks:")
        for ep in episode_182:
            print(f"  {ep['feed_slug']} / {ep['_id']} : {ep['chunk_count']} chunks")
    
    return episodes

async def analyze_episode_coverage(episode_id, feed_slug):
    """Analyze coverage for a specific episode"""
    print(f"\n{'='*60}")
    print(f"ANALYZING EPISODE: {feed_slug} / {episode_id}")
    print(f"{'='*60}")
    
    # Get all chunks for this episode, sorted by start_time
    chunks = await collection.find(
        {"episode_id": episode_id}
    ).sort("start_time", 1).to_list(None)
    
    if not chunks:
        print("No chunks found!")
        return None
    
    print(f"Total chunks: {len(chunks)}")
    
    # Calculate gaps
    gaps = []
    total_gap_time = 0
    
    for i in range(1, len(chunks)):
        prev_end = chunks[i-1].get('end_time', 0)
        curr_start = chunks[i].get('start_time', 0)
        gap = curr_start - prev_end
        
        if gap > 0.1:  # More than 100ms gap
            gaps.append({
                'index': i,
                'gap_seconds': gap,
                'between': f"{prev_end:.1f}s - {curr_start:.1f}s"
            })
            total_gap_time += gap
    
    # Calculate coverage
    first_chunk_start = chunks[0].get('start_time', 0)
    last_chunk_end = chunks[-1].get('end_time', 0)
    total_duration = last_chunk_end - first_chunk_start
    
    # Sum up actual chunk durations
    total_chunk_duration = sum(
        chunk.get('end_time', 0) - chunk.get('start_time', 0) 
        for chunk in chunks
    )
    
    coverage_percent = (total_chunk_duration / total_duration * 100) if total_duration > 0 else 0
    
    print(f"\nTiming Analysis:")
    print(f"  First chunk starts at: {first_chunk_start:.1f}s")
    print(f"  Last chunk ends at: {last_chunk_end:.1f}s")
    print(f"  Total episode duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"  Total chunk duration: {total_chunk_duration:.1f}s")
    print(f"  Total gap duration: {total_gap_time:.1f}s")
    print(f"  Coverage: {coverage_percent:.1f}%")
    
    print(f"\nGaps found: {len(gaps)}")
    if gaps:
        # Show largest gaps
        gaps_sorted = sorted(gaps, key=lambda x: x['gap_seconds'], reverse=True)
        print("\nLargest gaps:")
        for gap in gaps_sorted[:10]:
            print(f"  Gap of {gap['gap_seconds']:.1f}s between chunks {gap['index']-1} and {gap['index']} ({gap['between']})")
    
    # Analyze chunk durations
    chunk_durations = [
        chunk.get('end_time', 0) - chunk.get('start_time', 0) 
        for chunk in chunks
    ]
    
    print(f"\nChunk Duration Statistics:")
    print(f"  Average: {statistics.mean(chunk_durations):.1f}s")
    print(f"  Median: {statistics.median(chunk_durations):.1f}s")
    print(f"  Min: {min(chunk_durations):.1f}s")
    print(f"  Max: {max(chunk_durations):.1f}s")
    
    # Sample some chunk texts
    print(f"\nSample chunk texts:")
    for i in [0, len(chunks)//4, len(chunks)//2, -1]:
        if 0 <= i < len(chunks):
            chunk = chunks[i]
            text = chunk.get('text', '')[:100]
            print(f"  Chunk {i}: {chunk.get('start_time', 0):.1f}s - {chunk.get('end_time', 0):.1f}s")
            print(f"    Text: {text}...")
    
    return {
        'episode_id': episode_id,
        'feed_slug': feed_slug,
        'chunk_count': len(chunks),
        'total_duration': total_duration,
        'coverage_percent': coverage_percent,
        'gap_count': len(gaps),
        'total_gap_time': total_gap_time,
        'avg_chunk_duration': statistics.mean(chunk_durations) if chunk_durations else 0
    }

async def find_original_pattern():
    """Look for episodes that might have the 1082 -> 182 pattern"""
    print("\n" + "="*60)
    print("SEARCHING FOR 1082 -> 182 PATTERN")
    print("="*60)
    
    # Look for episodes with around 182 chunks (±10%)
    pipeline = [
        {"$group": {
            "_id": "$episode_id",
            "chunk_count": {"$sum": 1},
            "feed_slug": {"$first": "$feed_slug"},
            "total_duration": {"$sum": {"$subtract": ["$end_time", "$start_time"]}}
        }},
        {"$match": {
            "chunk_count": {"$gte": 160, "$lte": 200}
        }}
    ]
    
    candidates = await collection.aggregate(pipeline).to_list(None)
    
    print(f"Found {len(candidates)} episodes with 160-200 chunks")
    
    # For each candidate, estimate what the original segment count might have been
    for candidate in candidates[:5]:
        episode_id = candidate['_id']
        chunk_count = candidate['chunk_count']
        duration = candidate['total_duration']
        
        # If chunks are ~3 seconds each, original segments might have been ~0.5 seconds
        estimated_original = chunk_count * 6  # Rough estimate
        
        print(f"\nCandidate: {candidate['feed_slug']} / {episode_id}")
        print(f"  Chunks: {chunk_count}")
        print(f"  Total duration: {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"  Avg chunk: {duration/chunk_count:.1f}s")
        print(f"  Could have been ~{estimated_original} original segments?")
        
        # Analyze this episode
        await analyze_episode_coverage(episode_id, candidate['feed_slug'])

async def main():
    """Run comprehensive coverage analysis"""
    # Get initial stats
    episodes = await get_initial_stats()
    
    # Analyze specific episodes with different chunk counts
    print("\n" + "="*60)
    print("DETAILED EPISODE ANALYSIS")
    print("="*60)
    
    # Pick episodes with different chunk counts
    test_episodes = []
    
    # Low chunk count episodes
    low_chunks = [e for e in episodes if 150 < e['chunk_count'] < 200]
    if low_chunks:
        test_episodes.extend(low_chunks[:2])
    
    # Medium chunk count
    medium_chunks = [e for e in episodes if 500 < e['chunk_count'] < 700]
    if medium_chunks:
        test_episodes.extend(medium_chunks[:2])
    
    # High chunk count
    high_chunks = [e for e in episodes if e['chunk_count'] > 1000]
    if high_chunks:
        test_episodes.extend(high_chunks[:2])
    
    # Analyze each test episode
    coverage_results = []
    for ep in test_episodes:
        result = await analyze_episode_coverage(ep['_id'], ep['feed_slug'])
        if result:
            coverage_results.append(result)
    
    # Look for the original pattern
    await find_original_pattern()
    
    # Summary
    print("\n" + "="*60)
    print("COVERAGE SUMMARY")
    print("="*60)
    
    if coverage_results:
        avg_coverage = statistics.mean(r['coverage_percent'] for r in coverage_results)
        avg_gaps = statistics.mean(r['gap_count'] for r in coverage_results)
        
        print(f"Average coverage: {avg_coverage:.1f}%")
        print(f"Average gaps per episode: {avg_gaps:.1f}")
        
        # Find worst coverage
        worst = min(coverage_results, key=lambda x: x['coverage_percent'])
        print(f"\nWorst coverage: {worst['feed_slug']} / {worst['episode_id']}")
        print(f"  Coverage: {worst['coverage_percent']:.1f}%")
        print(f"  Chunks: {worst['chunk_count']}")
        print(f"  Gaps: {worst['gap_count']}")

if __name__ == "__main__":
    asyncio.run(main())