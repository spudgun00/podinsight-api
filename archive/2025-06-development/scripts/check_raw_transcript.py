import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

# The specific episode
EPISODE_ID = "1216c2e7-42b8-42ca-92d7-bad784f80af2"
FEED_SLUG = "a16z-podcast"

# S3 setup
s3_client = boto3.client('s3')
BUCKET_NAME = 'pod-insights-stage'

# Path to the raw transcript
RAW_PATH = f"{FEED_SLUG}/{EPISODE_ID}/transcripts/a16z-podcast-2025-01-22-rip-to-rpa-how-ai-makes-operations-work_1216c2e7_raw_transcript.json"

print("Downloading raw transcript...")
print(f"Path: s3://{BUCKET_NAME}/{RAW_PATH}")

try:
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=RAW_PATH)
    content = response['Body'].read()
    data = json.loads(content)

    print(f"\nFile size: {len(content):,} bytes")

    # Check structure
    if isinstance(data, dict):
        print(f"Keys in data: {list(data.keys())}")

        if 'segments' in data:
            segments = data['segments']
            print(f"\nTotal segments in raw transcript: {len(segments)}")

            # Analyze segments
            short_segments = 0
            empty_segments = 0
            total_duration = 0

            for seg in segments:
                text = seg.get('text', '').strip()
                if not text:
                    empty_segments += 1
                elif len(text) < 25:
                    short_segments += 1

                # Check duration
                start = seg.get('start', 0)
                end = seg.get('end', 0)
                duration = end - start
                total_duration = max(total_duration, end)

            print(f"Empty segments: {empty_segments}")
            print(f"Short segments (<25 chars): {short_segments}")
            print(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")

            # Show some examples of short segments
            print("\nExamples of short segments:")
            count = 0
            for i, seg in enumerate(segments):
                text = seg.get('text', '').strip()
                if 0 < len(text) < 25:
                    print(f"  Segment {i}: '{text}' ({seg.get('start', 0):.1f}s - {seg.get('end', 0):.1f}s)")
                    count += 1
                    if count >= 5:
                        break

        if 'text' in data:
            full_text = data['text']
            print(f"\nFull text length: {len(full_text):,} characters")
            word_count = len(full_text.split())
            print(f"Word count: {word_count:,}")

    elif isinstance(data, list):
        print(f"\nData is a list with {len(data)} items")

except Exception as e:
    print(f"Error: {e}")
