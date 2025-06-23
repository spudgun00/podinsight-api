import os
import asyncio
import json
import boto3
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# The specific episode we found with 182 chunks
EPISODE_ID = "1216c2e7-42b8-42ca-92d7-bad784f80af2"
FEED_SLUG = "a16z-podcast"

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.podinsight
collection = db.transcript_chunks_768d

# S3 setup
s3_client = boto3.client('s3')
BUCKET_NAME = 'pod-insights-stage'

async def analyze_mongodb_chunks():
    """Analyze the chunks we have in MongoDB"""
    print("=" * 60)
    print(f"ANALYZING EPISODE: {FEED_SLUG} / {EPISODE_ID}")
    print("=" * 60)
    
    # Get all chunks for this episode
    chunks = await collection.find(
        {"episode_id": EPISODE_ID}
    ).sort("start_time", 1).to_list(None)
    
    print(f"\nMONGODB ANALYSIS:")
    print(f"Total chunks in MongoDB: {len(chunks)}")
    
    if not chunks:
        print("ERROR: No chunks found!")
        return None
    
    # Timing analysis
    first_start = chunks[0]['start_time']
    last_end = chunks[-1]['end_time']
    total_duration = last_end - first_start
    
    print(f"First chunk starts at: {first_start:.1f}s")
    print(f"Last chunk ends at: {last_end:.1f}s")
    print(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    
    # Calculate gaps
    gaps = []
    total_gap_time = 0
    
    for i in range(1, len(chunks)):
        prev_end = chunks[i-1]['end_time']
        curr_start = chunks[i]['start_time']
        gap = curr_start - prev_end
        
        if gap > 0.1:  # More than 100ms gap
            gaps.append({
                'index': i,
                'gap_seconds': gap,
                'prev_end': prev_end,
                'curr_start': curr_start
            })
            total_gap_time += gap
    
    print(f"\nGAP ANALYSIS:")
    print(f"Total gaps found: {len(gaps)}")
    print(f"Total gap duration: {total_gap_time:.1f}s")
    
    # Show largest gaps
    if gaps:
        gaps_sorted = sorted(gaps, key=lambda x: x['gap_seconds'], reverse=True)
        print("\nLargest gaps:")
        for gap in gaps_sorted[:5]:
            print(f"  Gap of {gap['gap_seconds']:.1f}s between chunks {gap['index']-1} and {gap['index']}")
            print(f"    From {gap['prev_end']:.1f}s to {gap['curr_start']:.1f}s")
    
    # Calculate coverage
    chunk_duration = sum(c['end_time'] - c['start_time'] for c in chunks)
    coverage = (chunk_duration / total_duration * 100) if total_duration > 0 else 0
    
    print(f"\nCOVERAGE:")
    print(f"Total chunk duration: {chunk_duration:.1f}s")
    print(f"Coverage: {coverage:.1f}%")
    
    return chunks

async def download_s3_transcript():
    """Download the original transcript from S3"""
    print("\n" + "="*60)
    print("DOWNLOADING S3 TRANSCRIPT")
    print("="*60)
    
    # Try different possible paths
    possible_paths = [
        f"{FEED_SLUG}/{EPISODE_ID}/segments/{EPISODE_ID}.json",
        f"{FEED_SLUG}/{EPISODE_ID}/segments/{EPISODE_ID}_full.json",
        f"{FEED_SLUG}/{EPISODE_ID}/transcripts/a16z-podcast-2025-01-22-rip-to-rpa-how-ai-makes-operations-work_1216c2e7_raw_transcript.json"
    ]
    
    for s3_path in possible_paths:
        try:
            print(f"Trying: s3://{BUCKET_NAME}/{s3_path}")
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_path)
            content = response['Body'].read()
            data = json.loads(content)
            
            print(f"✅ Found transcript at: {s3_path}")
            print(f"File size: {len(content):,} bytes")
            
            # Analyze the transcript structure
            if isinstance(data, list):
                print(f"Transcript has {len(data)} segments")
                return data
            elif isinstance(data, dict) and 'segments' in data:
                segments = data['segments']
                print(f"Transcript has {len(segments)} segments")
                return segments
            else:
                print("Unexpected transcript format")
                return None
                
        except s3_client.exceptions.NoSuchKey:
            print(f"  Not found")
        except Exception as e:
            print(f"  Error: {e}")
    
    return None

def analyze_s3_segments(segments):
    """Analyze the original S3 segments"""
    print("\n" + "="*60)
    print("S3 TRANSCRIPT ANALYSIS")
    print("="*60)
    
    print(f"Total segments in S3: {len(segments)}")
    
    if not segments:
        return
    
    # Timing analysis
    first_start = segments[0].get('start', 0)
    last_end = segments[-1].get('end', 0)
    total_duration = last_end - first_start
    
    print(f"First segment starts at: {first_start:.1f}s")
    print(f"Last segment ends at: {last_end:.1f}s")
    print(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    
    # Segment length analysis
    segment_lengths = []
    short_segments = 0
    empty_segments = 0
    
    for seg in segments:
        text = seg.get('text', '').strip()
        if not text:
            empty_segments += 1
        elif len(text) < 25:
            short_segments += 1
        segment_lengths.append(len(text))
    
    print(f"\nSEGMENT STATISTICS:")
    print(f"Empty segments: {empty_segments}")
    print(f"Short segments (<25 chars): {short_segments}")
    print(f"Average segment length: {sum(segment_lengths)/len(segment_lengths):.1f} chars")
    
    # Sample some segments
    print("\nSAMPLE SEGMENTS:")
    for i in [0, 100, 200, 500, 1000]:
        if i < len(segments):
            seg = segments[i]
            text = seg.get('text', '')[:80]
            print(f"  Segment {i}: {seg.get('start', 0):.1f}s - {seg.get('end', 0):.1f}s")
            print(f"    Text: {text}...")

async def main():
    # Analyze MongoDB chunks
    chunks = await analyze_mongodb_chunks()
    
    if not chunks:
        print("\nNo chunks found in MongoDB!")
        return
    
    # Download and analyze S3 transcript
    segments = await download_s3_transcript()
    
    if segments:
        analyze_s3_segments(segments)
        
        # Compare
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        print(f"S3 segments: {len(segments)}")
        print(f"MongoDB chunks: {len(chunks)}")
        print(f"Reduction: {(1 - len(chunks)/len(segments)) * 100:.1f}%")
        
        # Check if this matches the 1082 -> 182 pattern
        if len(segments) > 1000 and len(chunks) < 200:
            print("\n⚠️  THIS MATCHES THE PATTERN!")
            print(f"Original segments: {len(segments)} -> Indexed chunks: {len(chunks)}")
            print("This confirms the 83% reduction issue!")
    else:
        print("\nCould not download S3 transcript for comparison")

if __name__ == "__main__":
    asyncio.run(main())