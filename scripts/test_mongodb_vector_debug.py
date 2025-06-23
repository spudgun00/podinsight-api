#!/usr/bin/env python3
"""
MongoDB Vector Search Debug
Direct investigation of vector search issues
"""

import asyncio
import aiohttp
import json
from datetime import datetime

class MongoDBVectorDebugger:
    def __init__(self):
        self.api_base = "https://podinsight-api.vercel.app"
        self.findings = {}
        
    async def test_mongodb_collections(self):
        """Test what collections exist and their contents"""
        print("🔍 Testing MongoDB collections...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/api/debug/mongodb") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        print(f"   MongoDB connected: {data.get('connection') == 'connected'}")
                        print(f"   Database: {data.get('database_name', 'unknown')}")
                        print(f"   Collection: {data.get('collection_name', 'unknown')}")
                        
                        # Check test searches
                        test_searches = data.get('test_searches', {})
                        print(f"\n   Test Search Results:")
                        for query, result in test_searches.items():
                            count = result.get('count', 0)
                            score = result.get('score', 0)
                            print(f"     '{query}': {count} results (score: {score})")
                            
                        self.findings["mongodb_debug"] = data
                        
                        # Check if this is using vector search or text search
                        if data.get('collection_name') == 'transcripts':
                            print(f"\n   ⚠️  Using 'transcripts' collection (text search)")
                            print(f"   Should be using 'transcript_chunks_768d' for vector search")
                        elif data.get('collection_name') == 'transcript_chunks_768d':
                            print(f"\n   ✅ Using 'transcript_chunks_768d' collection (vector search)")
                        else:
                            print(f"\n   ❓ Unknown collection being used")
                            
                    else:
                        print(f"   ❌ MongoDB debug failed: {response.status}")
                        
        except Exception as e:
            print(f"   ❌ Error: {e}")

    async def test_search_with_debug(self):
        """Test search with detailed debugging"""
        print(f"\n🔍 Testing search with debug information...")
        
        test_queries = [
            "venture capital",
            "AI startup", 
            "blockchain technology",
            "bitcoin"
        ]
        
        for query in test_queries[:2]:  # Test 2 queries to avoid rate limits
            try:
                await asyncio.sleep(2)  # Rate limit safety
                
                async with aiohttp.ClientSession() as session:
                    search_data = {"query": query, "limit": 5}
                    
                    async with session.post(f"{self.api_base}/api/search", json=search_data) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            print(f"\n   Query: '{query}'")
                            print(f"   Search type: {data.get('search_type', 'unknown')}")
                            print(f"   Results: {len(data.get('results', []))}")
                            print(f"   Total: {data.get('total_results', 0)}")
                            print(f"   Response time: {data.get('response_time_ms', 0)}ms")
                            
                            # Check for error messages
                            if 'error' in data:
                                print(f"   ❌ Error: {data['error']}")
                            if 'debug' in data:
                                print(f"   🔍 Debug: {data['debug']}")
                                
                        elif response.status == 429:
                            print(f"   ⚠️  Rate limited for '{query}'")
                            break
                        else:
                            print(f"   ❌ Search failed for '{query}': {response.status}")
                            
            except Exception as e:
                print(f"   ❌ Error testing '{query}': {e}")

    async def investigate_vector_search_path(self):
        """Investigate which search path is being used"""
        print(f"\n🕵️ Investigating search path...")
        
        # Check search_lightweight_768d.py to see search logic
        try:
            with open('api/search_lightweight_768d.py', 'r') as f:
                content = f.read()
                
                print(f"   📄 Analyzing search_lightweight_768d.py...")
                
                if 'mongodb_vector_search' in content:
                    print(f"   ✅ Found MongoDB vector search import")
                else:
                    print(f"   ❌ No MongoDB vector search import found")
                    
                if 'get_vector_search_handler' in content:
                    print(f"   ✅ Found vector search handler call")
                else:
                    print(f"   ❌ No vector search handler call found")
                    
                if 'vectorSearch' in content or '$vectorSearch' in content:
                    print(f"   ✅ Found vector search aggregation pipeline")
                else:
                    print(f"   ❌ No vector search pipeline found")
                    
                # Check for fallback logic
                if 'text search' in content.lower() or 'text_search' in content:
                    print(f"   ℹ️  Text search fallback detected")
                    
        except FileNotFoundError:
            print(f"   ❌ search_lightweight_768d.py not found")
            
        # Check mongodb_vector_search.py
        try:
            with open('api/mongodb_vector_search.py', 'r') as f:
                content = f.read()
                
                print(f"\n   📄 Analyzing mongodb_vector_search.py...")
                
                if 'transcript_chunks_768d' in content:
                    print(f"   ✅ Found transcript_chunks_768d collection reference")
                else:
                    print(f"   ❌ No transcript_chunks_768d collection reference")
                    
                if 'embedding_768d' in content:
                    print(f"   ✅ Found embedding_768d field reference")
                else:
                    print(f"   ❌ No embedding_768d field reference")
                    
                if 'vector_index' in content:
                    print(f"   ✅ Found vector_index reference")
                else:
                    print(f"   ❌ No vector_index reference")
                    
        except FileNotFoundError:
            print(f"   ❌ mongodb_vector_search.py not found")

    async def check_embedding_integration(self):
        """Check if embeddings are being properly integrated"""
        print(f"\n🔗 Checking embedding integration...")
        
        # Check embeddings_768d_modal.py
        try:
            with open('api/embeddings_768d_modal.py', 'r') as f:
                content = f.read()
                
                print(f"   📄 Analyzing embeddings_768d_modal.py...")
                
                if 'MODAL_EMBEDDING_URL' in content:
                    print(f"   ✅ Modal URL configuration found")
                else:
                    print(f"   ❌ No Modal URL configuration")
                    
                if 'encode_query' in content:
                    print(f"   ✅ Query encoding function found")
                else:
                    print(f"   ❌ No query encoding function")
                    
                # Extract Modal URL from content
                lines = content.split('\n')
                for line in lines:
                    if 'MODAL_EMBEDDING_URL' in line and 'https://' in line:
                        print(f"   📍 Modal URL: {line.strip()}")
                        break
                        
        except FileNotFoundError:
            print(f"   ❌ embeddings_768d_modal.py not found")

    async def generate_debug_report(self):
        """Generate debug report with recommendations"""
        print(f"\n" + "="*60)
        print(f"🔧 MONGODB VECTOR SEARCH DEBUG REPORT")
        print(f"="*60)
        
        print(f"\nTimestamp: {datetime.now().isoformat()}")
        
        # Analyze findings
        mongodb_data = self.findings.get("mongodb_debug", {})
        collection = mongodb_data.get("collection_name", "unknown")
        
        print(f"\n📊 FINDINGS:")
        print(f"   MongoDB Collection: {collection}")
        print(f"   Search Results: All queries return 0 results")
        
        if collection == "transcripts":
            print(f"\n🚨 LIKELY ISSUE: Using wrong collection!")
            print(f"   Currently using: 'transcripts' (text search collection)")
            print(f"   Should use: 'transcript_chunks_768d' (vector search collection)")
            print(f"\n🔧 SOLUTION:")
            print(f"   1. Update mongodb_search.py to use transcript_chunks_768d")
            print(f"   2. Ensure vector search index exists on embedding_768d field")
            print(f"   3. Verify 768D embeddings are stored in collection")
            
        elif collection == "transcript_chunks_768d":
            print(f"\n🤔 COLLECTION CORRECT, but still 0 results")
            print(f"\n🔧 POSSIBLE ISSUES:")
            print(f"   1. Vector search index missing or misconfigured")
            print(f"   2. No embeddings stored in collection")
            print(f"   3. Vector search query syntax error")
            print(f"   4. Embedding dimension mismatch")
            
        else:
            print(f"\n❓ UNKNOWN COLLECTION: {collection}")
            print(f"   Need to identify which collection is being used")
            
        print(f"\n🎯 NEXT ACTIONS:")
        print(f"   1. Check which collection the search handler is using")
        print(f"   2. Verify transcript_chunks_768d has data and embeddings")
        print(f"   3. Check vector search index configuration")
        print(f"   4. Test direct MongoDB vector search query")
        
        # Save findings
        with open('mongodb_vector_debug_report.json', 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "collection_used": collection,
                "findings": self.findings,
                "issue": "search_returns_zero_results",
                "likely_cause": "wrong_collection" if collection == "transcripts" else "vector_search_config"
            }, f, indent=2, default=str)
            
        print(f"\n💾 Debug report saved to mongodb_vector_debug_report.json")

    async def run_full_debug(self):
        """Run complete MongoDB vector search debugging"""
        print("🔧 MONGODB VECTOR SEARCH DEBUGGING")
        print("Investigating zero search results...")
        print("="*60)
        
        await self.test_mongodb_collections()
        await self.test_search_with_debug()
        await self.investigate_vector_search_path()
        await self.check_embedding_integration()
        await self.generate_debug_report()

async def main():
    debugger = MongoDBVectorDebugger()
    await debugger.run_full_debug()

if __name__ == "__main__":
    asyncio.run(main())