#!/usr/bin/env python3
"""
Populate duration_seconds field in episode_metadata collection.

This script calculates the duration of each episode by finding the last
transcript chunk's end_time and updates the episode_metadata collection.

Usage:
    python scripts/populate_duration_seconds.py                    # Run on all episodes
    python scripts/populate_duration_seconds.py --limit 5          # Test on 5 episodes
    python scripts/populate_duration_seconds.py --dry-run          # Preview without updating
    python scripts/populate_duration_seconds.py --limit 5 --dry-run  # Preview 5 episodes
"""

import os
import sys
import asyncio
import argparse
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient

# Try to load dotenv if available (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use existing environment variables

# MongoDB configuration
MONGODB_URI = os.environ.get("MONGODB_URI")
DATABASE_NAME = "podinsight"
METADATA_COLLECTION = "episode_metadata"
CHUNKS_COLLECTION = "transcript_chunks_768d"

# Timeout for MongoDB operations (30 seconds)
SERVER_SELECTION_TIMEOUT_MS = 30000


class DurationMigration:
    """Handles the migration of duration_seconds field"""

    def __init__(self, dry_run: bool = False, limit: Optional[int] = None):
        self.dry_run = dry_run
        self.limit = limit
        self.client: Optional[AsyncIOMotorClient] = None

        # Statistics
        self.total_episodes = 0
        self.updated = 0
        self.skipped = 0
        self.errors = 0
        self.error_episodes = []

    async def connect(self):
        """Connect to MongoDB"""
        if not MONGODB_URI:
            raise ValueError("MONGODB_URI environment variable not set")

        print(f"🔌 Connecting to MongoDB...")
        self.client = AsyncIOMotorClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS
        )

        # Test connection
        await self.client.admin.command('ping')
        print(f"✅ Connected to MongoDB\n")

    async def get_duration_for_episode(self, episode_id: str) -> Optional[int]:
        """
        Calculate duration for an episode by getting the last chunk's end_time.
        Returns None if no chunks found.
        """
        db = self.client[DATABASE_NAME]
        chunks_collection = db[CHUNKS_COLLECTION]

        # Get the last chunk (highest chunk_index)
        last_chunk = await chunks_collection.find_one(
            {"episode_id": episode_id},
            sort=[("chunk_index", -1)]  # -1 = descending order
        )

        if last_chunk and "end_time" in last_chunk:
            # Convert to int (same as transcript endpoint does)
            return int(last_chunk["end_time"])

        return None

    async def update_episode_duration(self, episode_id: str, duration: int) -> bool:
        """
        Update the duration_seconds field for an episode.
        Returns True if successful, False otherwise.
        """
        if self.dry_run:
            return True  # Don't actually update in dry-run mode

        db = self.client[DATABASE_NAME]
        metadata_collection = db[METADATA_COLLECTION]

        result = await metadata_collection.update_one(
            {"episode_id": episode_id},
            {"$set": {"duration_seconds": duration}}
        )

        return result.modified_count > 0

    async def run_migration(self):
        """Main migration logic"""
        await self.connect()

        db = self.client[DATABASE_NAME]
        metadata_collection = db[METADATA_COLLECTION]

        # Build query
        query = {}

        # Get episodes
        cursor = metadata_collection.find(query)
        if self.limit:
            cursor = cursor.limit(self.limit)

        episodes = await cursor.to_list(length=None)
        self.total_episodes = len(episodes)

        # Print header
        mode = "DRY RUN" if self.dry_run else "LIVE MIGRATION"
        print(f"{'='*60}")
        print(f"  {mode}")
        print(f"{'='*60}")
        print(f"Total episodes to process: {self.total_episodes}\n")

        if self.total_episodes == 0:
            print("⚠️  No episodes found to process")
            return

        # Process each episode
        for i, episode in enumerate(episodes, 1):
            episode_id = episode.get("episode_id")

            # Get episode title from nested structure (same as transcript endpoint)
            raw_entry = episode.get("raw_entry_original_feed", {})
            episode_title = raw_entry.get("episode_title", "Unknown") if raw_entry else "Unknown"
            if not episode_title or episode_title == "None":
                episode_title = "Unknown"

            # Show progress
            progress = f"[{i}/{self.total_episodes}]"

            try:
                # Get duration from transcript chunks
                duration = await self.get_duration_for_episode(episode_id)

                if duration is None:
                    # No chunks found
                    self.errors += 1
                    self.error_episodes.append(episode_id)
                    print(f"❌ {progress} No chunks found: {episode_id[:8]}... ({episode_title[:40]})")
                    continue

                # Check if already has duration
                existing_duration = episode.get("duration_seconds")
                if existing_duration and existing_duration > 0:
                    self.skipped += 1
                    print(f"⏭️  {progress} Already has duration ({existing_duration}s): {episode_id[:8]}...")
                    continue

                # Update episode with duration
                if self.dry_run:
                    self.updated += 1
                    print(f"✨ {progress} Would update: {episode_id[:8]}... → {duration}s ({episode_title[:40]})")
                else:
                    success = await self.update_episode_duration(episode_id, duration)
                    if success:
                        self.updated += 1
                        print(f"✅ {progress} Updated: {episode_id[:8]}... → {duration}s ({episode_title[:40]})")
                    else:
                        self.errors += 1
                        self.error_episodes.append(episode_id)
                        print(f"❌ {progress} Update failed: {episode_id[:8]}...")

            except Exception as e:
                self.errors += 1
                self.error_episodes.append(episode_id)
                print(f"❌ {progress} Error: {episode_id[:8]}... - {str(e)}")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print migration summary"""
        print(f"\n{'='*60}")
        print(f"  MIGRATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total episodes processed:  {self.total_episodes}")
        print(f"✅ Updated:                {self.updated}")
        print(f"⏭️  Skipped (already set):  {self.skipped}")
        print(f"❌ Errors/No chunks:       {self.errors}")

        if self.error_episodes:
            print(f"\n⚠️  Episodes with errors:")
            for ep_id in self.error_episodes[:10]:  # Show first 10
                print(f"   - {ep_id}")
            if len(self.error_episodes) > 10:
                print(f"   ... and {len(self.error_episodes) - 10} more")

        if self.dry_run:
            print(f"\n💡 This was a DRY RUN - no changes were made")
            print(f"   Run without --dry-run to apply changes")
        else:
            print(f"\n🎉 Migration complete!")

        print(f"{'='*60}\n")

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Populate duration_seconds field in episode_metadata"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without updating database"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of episodes to process (for testing)"
    )

    args = parser.parse_args()

    # Create and run migration
    migration = DurationMigration(dry_run=args.dry_run, limit=args.limit)

    try:
        await migration.run_migration()
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await migration.close()


if __name__ == "__main__":
    asyncio.run(main())
