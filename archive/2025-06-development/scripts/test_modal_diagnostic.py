#!/usr/bin/env python3
"""
EMERGENCY Modal.com Diagnostic Testing
Identifies why search is returning zero results
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class ModalDiagnosticTester:
    def __init__(self):
        self.modal_url = os.getenv('MODAL_EMBEDDING_URL', 'https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run')
        self.api_base = "https://podinsight-api.vercel.app"
        self.results = {}

    async def test_modal_endpoint_health(self):
        """Test if Modal endpoint is responsive"""
        print("🔍 Testing Modal.com endpoint health...")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                # Test basic health/info endpoint
                async with session.get(f"{self.modal_url}/docs") as response:
                    status = response.status
                    print(f"   Modal docs endpoint: {status}")

                    if status == 200:
                        print("   ✅ Modal endpoint is accessible")
                        self.results["modal_accessible"] = True
                    else:
                        print(f"   ❌ Modal endpoint returned {status}")
                        self.results["modal_accessible"] = False
                        return False

        except Exception as e:
            print(f"   ❌ Modal endpoint error: {e}")
            self.results["modal_accessible"] = False
            return False

        return True

    async def test_modal_embedding_generation(self):
        """Test if Modal can generate embeddings"""
        print("\n🧪 Testing Modal embedding generation...")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                test_text = "venture capital startup funding"

                # Test single embedding
                embedding_data = {"text": test_text}

                start_time = time.time()
                async with session.post(f"{self.modal_url}/embed", json=embedding_data) as response:
                    response_time = time.time() - start_time
                    status = response.status

                    print(f"   Modal embedding request: {status} ({response_time:.3f}s)")

                    if status == 200:
                        data = await response.json()
                        embedding = data.get('embedding', [])

                        print(f"   ✅ Generated {len(embedding)}D embedding")
                        print(f"   Sample values: {embedding[:3] if embedding else 'None'}")

                        self.results["modal_embedding"] = {
                            "success": True,
                            "dimensions": len(embedding),
                            "response_time": response_time,
                            "sample_values": embedding[:5] if embedding else []
                        }

                        return embedding
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Modal embedding failed: {error_text}")
                        self.results["modal_embedding"] = {"success": False, "error": error_text}
                        return None

        except Exception as e:
            print(f"   ❌ Modal embedding error: {e}")
            self.results["modal_embedding"] = {"success": False, "error": str(e)}
            return None

    async def test_api_search_pipeline(self):
        """Test the complete search pipeline"""
        print("\n🔗 Testing API search pipeline...")

        try:
            async with aiohttp.ClientSession() as session:
                # Wait for rate limit reset
                await asyncio.sleep(2)

                search_data = {"query": "artificial intelligence", "limit": 3}

                start_time = time.time()
                async with session.post(f"{self.api_base}/api/search", json=search_data) as response:
                    response_time = time.time() - start_time
                    status = response.status

                    print(f"   API search request: {status} ({response_time:.3f}s)")

                    if status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        search_type = data.get('search_type', 'unknown')
                        total_results = data.get('total_results', 0)

                        print(f"   Search type: {search_type}")
                        print(f"   Results returned: {len(results)}")
                        print(f"   Total available: {total_results}")

                        if results:
                            result = results[0]
                            print(f"   First result: {result.get('episode_title', 'No title')[:50]}...")
                            print(f"   Similarity score: {result.get('similarity_score', 0)}")

                        self.results["api_search"] = {
                            "success": True,
                            "search_type": search_type,
                            "results_count": len(results),
                            "total_results": total_results,
                            "response_time": response_time
                        }

                        return len(results) > 0
                    else:
                        error_text = await response.text()
                        print(f"   ❌ API search failed: {error_text}")
                        self.results["api_search"] = {"success": False, "error": error_text}
                        return False

        except Exception as e:
            print(f"   ❌ API search error: {e}")
            self.results["api_search"] = {"success": False, "error": str(e)}
            return False

    async def test_direct_modal_via_api(self):
        """Test if the API is correctly calling Modal"""
        print("\n🔄 Testing API → Modal integration...")

        # Check if the embeddings_768d_modal.py file exists and is configured correctly
        try:
            with open('api/embeddings_768d_modal.py', 'r') as f:
                content = f.read()

                if 'MODAL_EMBEDDING_URL' in content:
                    print("   ✅ Modal URL configuration found in API")
                else:
                    print("   ❌ Modal URL configuration missing in API")

                if 'podinsighthq--podinsight-embeddings-api' in content:
                    print("   ✅ Correct Modal endpoint URL found")
                else:
                    print("   ⚠️  Modal endpoint URL might be incorrect")

        except FileNotFoundError:
            print("   ❌ embeddings_768d_modal.py file not found")

        # Test the API's embedding endpoint directly
        try:
            async with aiohttp.ClientSession() as session:
                await asyncio.sleep(2)  # Rate limit

                async with session.get(f"{self.api_base}/api/debug/mongodb") as response:
                    if response.status == 200:
                        data = await response.json()
                        test_searches = data.get('test_searches', {})

                        print(f"   MongoDB debug test searches:")
                        for query, result in test_searches.items():
                            print(f"     '{query}': {result.get('count', 0)} results")

                        if all(r.get('count', 0) == 0 for r in test_searches.values()):
                            print("   ❌ All MongoDB test searches return 0 results")
                            print("   🔍 This suggests vector search or embedding issue")

        except Exception as e:
            print(f"   ❌ Error testing API integration: {e}")

    async def investigate_search_chain(self):
        """Investigate the complete search chain"""
        print("\n🕵️ Investigating search chain issues...")

        # Test each component in the search chain
        components = {
            "Modal endpoint": await self.test_modal_endpoint_health(),
            "Modal embedding generation": await self.test_modal_embedding_generation() is not None,
            "API search pipeline": await self.test_api_search_pipeline(),
        }

        print(f"\n📊 Component Status:")
        for component, status in components.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {component}")

        # Identify the broken link
        if not components["Modal endpoint"]:
            print(f"\n🚨 ROOT CAUSE: Modal.com endpoint is not accessible")
            print(f"   - Check Modal deployment status")
            print(f"   - Verify Modal URL: {self.modal_url}")
        elif not components["Modal embedding generation"]:
            print(f"\n🚨 ROOT CAUSE: Modal can't generate embeddings")
            print(f"   - Check Instructor-XL model loading")
            print(f"   - Verify GPU resources on Modal")
        elif not components["API search pipeline"]:
            print(f"\n🚨 ROOT CAUSE: API search pipeline broken")
            print(f"   - Check MongoDB vector search index")
            print(f"   - Verify embedding storage in MongoDB")
            print(f"   - Check API → Modal integration")
        else:
            print(f"\n🤔 All components appear working but search returns 0 results")
            print(f"   - Check MongoDB collection contents")
            print(f"   - Verify vector search index configuration")
            print(f"   - Check embedding dimensions match (768D)")

    async def generate_diagnostic_report(self):
        """Generate comprehensive diagnostic report"""
        print(f"\n" + "="*60)
        print(f"🚨 MODAL DIAGNOSTIC REPORT")
        print(f"="*60)

        print(f"\nTimestamp: {datetime.now().isoformat()}")
        print(f"Modal URL: {self.modal_url}")
        print(f"API Base: {self.api_base}")

        # Overall status
        modal_ok = self.results.get("modal_embedding", {}).get("success", False)
        search_ok = self.results.get("api_search", {}).get("results_count", 0) > 0

        if modal_ok and search_ok:
            print(f"\n✅ STATUS: HEALTHY - Modal and search working")
        elif modal_ok and not search_ok:
            print(f"\n⚠️  STATUS: MODAL OK, SEARCH BROKEN - Check MongoDB/vector index")
        elif not modal_ok:
            print(f"\n❌ STATUS: MODAL BROKEN - Fix Modal deployment first")
        else:
            print(f"\n❓ STATUS: UNKNOWN - Need deeper investigation")

        print(f"\n📋 NEXT ACTIONS:")
        if not modal_ok:
            print(f"   1. Fix Modal.com deployment and Instructor-XL model")
            print(f"   2. Verify Modal endpoint accessibility")
            print(f"   3. Test embedding generation manually")
        else:
            print(f"   1. Check MongoDB vector search index")
            print(f"   2. Verify 768D embeddings are stored")
            print(f"   3. Test vector search queries directly")

        # Save detailed results
        with open('modal_diagnostic_report.json', 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "modal_url": self.modal_url,
                "api_base": self.api_base,
                "results": self.results,
                "summary": {
                    "modal_working": modal_ok,
                    "search_working": search_ok,
                    "overall_status": "healthy" if modal_ok and search_ok else "broken"
                }
            }, f, indent=2, default=str)

        print(f"\n💾 Detailed report saved to modal_diagnostic_report.json")

    async def run_full_diagnostics(self):
        """Run complete diagnostic suite"""
        print("🚨 EMERGENCY MODAL DIAGNOSTICS")
        print("Investigating why search returns 0 results...")
        print("="*60)

        # Run all diagnostic tests
        await self.investigate_search_chain()
        await self.test_direct_modal_via_api()
        await self.generate_diagnostic_report()

async def main():
    tester = ModalDiagnosticTester()
    await tester.run_full_diagnostics()

if __name__ == "__main__":
    asyncio.run(main())
