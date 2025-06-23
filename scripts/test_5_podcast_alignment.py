#!/usr/bin/env python3
"""
Comprehensive testing of 5 test podcasts - MongoDB and Supabase alignment
"""

import asyncio
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()

# Test episode GUIDs (from the JSON file you showed)
TEST_EPISODES = [
    "1216c2e7-42b8-42ca-92d7-bad784f80af2",  # a16z-podcast
]

class AlignmentTester:
    def __init__(self):
        self.results = {
            "mongodb_status": {},
            "supabase_status": {},
            "alignment_issues": [],
            "test_results": {}
        }
        
    async def init_connections(self):
        """Initialize MongoDB and Supabase connections"""
        # MongoDB
        try:
            self.mongo_client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
            self.mongo_db = self.mongo_client['podinsight']
            
            # Test connection
            await self.mongo_client.admin.command('ping')
            self.results["mongodb_status"]["connected"] = True
            print("✅ MongoDB connected")
        except Exception as e:
            self.results["mongodb_status"]["connected"] = False
            self.results["mongodb_status"]["error"] = str(e)
            print(f"❌ MongoDB connection failed: {e}")
            
        # Supabase
        try:
            self.supabase = create_client(
                os.getenv('SUPABASE_URL'),
                os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            )
            # Test with simple query
            test = self.supabase.table('episodes').select('count', count='exact').limit(1).execute()
            self.results["supabase_status"]["connected"] = True
            print("✅ Supabase connected")
        except Exception as e:
            self.results["supabase_status"]["connected"] = False
            self.results["supabase_status"]["error"] = str(e)
            print(f"❌ Supabase connection failed: {e}")
            
        return self.results["mongodb_status"]["connected"] or self.results["supabase_status"]["connected"]
        
    async def check_mongodb_collections(self):
        """Check what collections exist in MongoDB"""
        print("\n" + "="*60)
        print("MONGODB COLLECTIONS CHECK")
        print("="*60)
        
        if not self.results["mongodb_status"]["connected"]:
            print("❌ MongoDB not connected, skipping collection check")
            return []
        
        try:
            collections = await self.mongo_db.list_collection_names()
            self.results["mongodb_status"]["collections"] = collections
            print(f"Collections found: {collections}")
            
            # Check each collection
            for collection_name in collections:
                collection = self.mongo_db[collection_name]
                count = await collection.count_documents({})
                self.results["mongodb_status"][f"{collection_name}_count"] = count
                print(f"  {collection_name}: {count} documents")
                
            return collections
        except Exception as e:
            print(f"❌ Error checking collections: {e}")
            return []
        
    async def find_test_episodes_mongodb(self):
        """Find test episodes in MongoDB"""
        print("\n" + "="*60)
        print("MONGODB TEST EPISODES")
        print("="*60)
        
        # Check transcript_chunks_768d collection
        if 'transcript_chunks_768d' in self.results["mongodb_status"]["collections"]:
            chunks_collection = self.mongo_db['transcript_chunks_768d']
            
            # Get all unique episode IDs
            all_episodes = await chunks_collection.distinct('episode_id')
            print(f"\nTotal unique episodes in chunks collection: {len(all_episodes)}")
            
            # Show first 5 episodes
            print("\nFirst 5 episode GUIDs:")
            for guid in all_episodes[:5]:
                chunk_count = await chunks_collection.count_documents({'episode_id': guid})
                sample = await chunks_collection.find_one({'episode_id': guid})
                print(f"  {guid}: {chunk_count} chunks, feed: {sample.get('feed_slug', 'unknown')}")
                
            # Check if our test episode exists
            for test_guid in TEST_EPISODES:
                count = await chunks_collection.count_documents({'episode_id': test_guid})
                if count > 0:
                    sample = await chunks_collection.find_one({'episode_id': test_guid})
                    print(f"\n✅ Found test episode {test_guid}:")
                    print(f"   Chunks: {count}")
                    print(f"   Feed: {sample.get('feed_slug')}")
                    print(f"   Title: {sample.get('episode_title', 'No title')}")
                else:
                    print(f"\n❌ Test episode {test_guid} NOT FOUND")
                    
        # Check transcripts collection
        if 'transcripts' in self.results["mongodb_status"]["collections"]:
            transcripts_collection = self.mongo_db['transcripts']
            count = await transcripts_collection.count_documents({})
            print(f"\nTranscripts collection: {count} documents")
            
    async def check_supabase_episodes(self):
        """Check Supabase episodes table"""
        print("\n" + "="*60)
        print("SUPABASE EPISODES CHECK")
        print("="*60)
        
        # Get total count
        count_response = self.supabase.table('episodes').select('count', count='exact').execute()
        total_episodes = count_response.count
        print(f"Total episodes in Supabase: {total_episodes}")
        
        # Get first 5 episodes
        sample_response = self.supabase.table('episodes').select('*').limit(5).execute()
        print("\nFirst 5 episodes:")
        for ep in sample_response.data:
            print(f"  {ep['id']}: {ep.get('podcast_name', 'unknown')} - {ep.get('title', 'No title')[:50]}...")
            
        # Check for test episode
        for test_guid in TEST_EPISODES:
            response = self.supabase.table('episodes').select('*').eq('id', test_guid).execute()
            if response.data:
                ep = response.data[0]
                print(f"\n✅ Found test episode {test_guid} in Supabase:")
                print(f"   Podcast: {ep.get('podcast_name')}")
                print(f"   Title: {ep.get('title')}")
                print(f"   Published: {ep.get('published_at')}")
                print(f"   S3 Stage: {ep.get('s3_stage_prefix')}")
                self.results["test_results"][test_guid] = {"supabase": ep}
            else:
                print(f"\n❌ Test episode {test_guid} NOT FOUND in Supabase")
                
    async def verify_alignment(self):
        """Verify data alignment between MongoDB and Supabase"""
        print("\n" + "="*60)
        print("DATA ALIGNMENT VERIFICATION")
        print("="*60)
        
        chunks_collection = self.mongo_db['transcript_chunks_768d']
        
        for test_guid in TEST_EPISODES:
            print(f"\nChecking {test_guid}...")
            
            # Get from MongoDB
            mongo_chunks = await chunks_collection.find({'episode_id': test_guid}).to_list(None)
            
            # Get from Supabase
            supabase_response = self.supabase.table('episodes').select('*').eq('id', test_guid).execute()
            
            if mongo_chunks and supabase_response.data:
                mongo_sample = mongo_chunks[0]
                supabase_data = supabase_response.data[0]
                
                # Compare feed/podcast names
                mongo_feed = mongo_sample.get('feed_slug', '')
                supabase_podcast = supabase_data.get('podcast_name', '')
                
                # Extract feed slug from S3 path if needed
                s3_prefix = supabase_data.get('s3_stage_prefix', '')
                s3_feed = s3_prefix.split('/')[0] if '/' in s3_prefix else ''
                
                print(f"  MongoDB feed_slug: {mongo_feed}")
                print(f"  Supabase podcast_name: {supabase_podcast}")
                print(f"  S3 prefix feed: {s3_feed}")
                
                # Check topics
                topics_response = self.supabase.table('topic_mentions').select('*').eq('episode_id', test_guid).execute()
                print(f"  Topics in Supabase: {len(topics_response.data)}")
                
                # Check if MongoDB has topic data
                mongo_topics = mongo_sample.get('topics', [])
                print(f"  Topics in MongoDB chunk: {mongo_topics}")
                
            else:
                if not mongo_chunks:
                    print(f"  ❌ Not found in MongoDB")
                if not supabase_response.data:
                    print(f"  ❌ Not found in Supabase")
                    
    async def test_vector_search(self):
        """Test vector search functionality"""
        print("\n" + "="*60)
        print("VECTOR SEARCH TEST")
        print("="*60)
        
        chunks_collection = self.mongo_db['transcript_chunks_768d']
        
        # Check if vector index exists
        indexes = await chunks_collection.list_indexes().to_list(None)
        vector_index = None
        for idx in indexes:
            if 'embedding_768d' in str(idx):
                vector_index = idx
                print(f"✅ Found vector index: {idx['name']}")
                
        if not vector_index:
            print("❌ No vector index found on embedding_768d field")
            
        # Sample a chunk to check embedding
        sample = await chunks_collection.find_one({'episode_id': {'$in': TEST_EPISODES}})
        if sample and 'embedding_768d' in sample:
            embedding_len = len(sample['embedding_768d'])
            print(f"✅ Sample chunk has embedding with {embedding_len} dimensions")
        else:
            print("❌ No embeddings found in sample chunk")
            
    async def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("TEST REPORT SUMMARY")
        print("="*60)
        
        # Save detailed results
        with open('test_5_podcast_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
            
        print("\n✅ Detailed results saved to test_5_podcast_results.json")
        
        # Summary
        if self.results["mongodb_status"]["connected"] and self.results["supabase_status"]["connected"]:
            print("\n✅ Both databases connected successfully")
        else:
            print("\n❌ Database connection issues detected")
            
        print(f"\nMongoDB collections: {self.results['mongodb_status'].get('collections', [])}")
        print(f"Alignment issues found: {len(self.results.get('alignment_issues', []))}")
        
    async def run_all_tests(self):
        """Run all alignment tests"""
        if not await self.init_connections():
            print("❌ Failed to initialize connections")
            return
            
        await self.check_mongodb_collections()
        await self.find_test_episodes_mongodb()
        await self.check_supabase_episodes()
        await self.verify_alignment()
        await self.test_vector_search()
        await self.generate_report()
        
        # Close connections
        self.mongo_client.close()

async def main():
    tester = AlignmentTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())