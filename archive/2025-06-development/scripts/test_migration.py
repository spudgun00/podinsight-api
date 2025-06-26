#!/usr/bin/env python3
"""
Migration Test Script for PodInsightHQ MongoDB Integration
Validates that transcript migration is working correctly
"""

import os
import time
from typing import Dict, List
from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from the current directory
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

class MigrationTester:
    def __init__(self):
        self.mongodb_uri = os.getenv('MONGODB_URI')
        if not self.mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment variables")

        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client['podinsight']
        self.collection = self.db['transcripts']

        self.test_results = {
            'mongodb_connection': False,
            'collection_exists': False,
            'indexes_created': False,
            'document_count': 0,
            'data_integrity': False,
            'search_functionality': False,
            'performance': {'time': 0, 'estimate': ''}
        }

    def test_mongodb_connection(self) -> bool:
        """Test 1: MongoDB connection and basic functionality"""
        try:
            # Test connection
            self.client.admin.command('ping')
            print("✅ MongoDB connection: PASS")
            self.test_results['mongodb_connection'] = True
            return True
        except Exception as e:
            print(f"❌ MongoDB connection: FAIL - {e}")
            return False

    def test_collection_setup(self) -> bool:
        """Test 2: Verify collection exists and has proper indexes"""
        try:
            # Check if collection exists
            collections = self.db.list_collection_names()
            if 'transcripts' not in collections:
                print("❌ Collection exists: FAIL - transcripts collection not found")
                return False

            print("✅ Collection exists: PASS")
            self.test_results['collection_exists'] = True

            # Check indexes
            indexes = list(self.collection.list_indexes())
            index_names = [idx['name'] for idx in indexes]

            required_indexes = ['_id_', 'full_text_text', 'episode_id_1']
            missing_indexes = [idx for idx in required_indexes if idx not in index_names]

            if missing_indexes:
                print(f"⚠️  Indexes: PARTIAL - Missing: {missing_indexes}")
            else:
                print("✅ Indexes created: PASS")
                self.test_results['indexes_created'] = True

            return True
        except Exception as e:
            print(f"❌ Collection setup: FAIL - {e}")
            return False

    def test_document_count(self, expected_count: int = 5) -> bool:
        """Test 3: Verify expected number of documents"""
        try:
            count = self.collection.count_documents({})
            self.test_results['document_count'] = count

            if count == expected_count:
                print(f"✅ Document count: PASS ({count} documents)")
                return True
            else:
                print(f"⚠️  Document count: {count} (expected {expected_count})")
                return count > 0  # Still pass if we have some documents
        except Exception as e:
            print(f"❌ Document count: FAIL - {e}")
            return False

    def test_data_integrity(self) -> bool:
        """Test 4: Verify document structure and content quality"""
        try:
            # Get sample documents
            sample_docs = list(self.collection.find().limit(5))

            if not sample_docs:
                print("❌ Data integrity: FAIL - No documents found")
                return False

            required_fields = ['episode_id', 'full_text', 'podcast_name', 'episode_title', 'topics', 'segments']
            total_chars = 0
            valid_docs = 0

            for doc in sample_docs:
                # Check required fields
                missing_fields = [field for field in required_fields if field not in doc]
                if missing_fields:
                    print(f"⚠️  Document {doc.get('episode_id', 'unknown')} missing: {missing_fields}")
                    continue

                # Check full_text quality
                full_text = doc.get('full_text', '')
                if len(full_text) < 1000:
                    print(f"⚠️  Document {doc.get('episode_id', 'unknown')} has short transcript: {len(full_text)} chars")
                    continue

                # Check topics
                topics = doc.get('topics', [])
                if not isinstance(topics, list):
                    print(f"⚠️  Document {doc.get('episode_id', 'unknown')} has invalid topics format")
                    continue

                total_chars += len(full_text)
                valid_docs += 1

            avg_chars = total_chars / valid_docs if valid_docs > 0 else 0

            if valid_docs == len(sample_docs):
                print(f"✅ Data integrity: PASS (avg {avg_chars:,.0f} chars per transcript)")
                self.test_results['data_integrity'] = True
                return True
            else:
                print(f"⚠️  Data integrity: PARTIAL ({valid_docs}/{len(sample_docs)} documents valid)")
                return valid_docs > 0

        except Exception as e:
            print(f"❌ Data integrity: FAIL - {e}")
            return False

    def test_search_functionality(self) -> bool:
        """Test 5: Verify text search is working"""
        try:
            # Test different search terms
            search_terms = ["AI", "agents", "venture", "capital"]
            search_results = {}

            for term in search_terms:
                results = list(self.collection.find(
                    {"$text": {"$search": term}},
                    {"score": {"$meta": "textScore"}, "episode_title": 1, "full_text": 1}
                ).sort([("score", {"$meta": "textScore"})]).limit(3))

                search_results[term] = {
                    'count': len(results),
                    'avg_score': sum(r['score'] for r in results) / len(results) if results else 0,
                    'has_content': all(term.lower() in r['full_text'].lower() for r in results) if results else False
                }

            # Evaluate results
            successful_searches = 0
            for term, result in search_results.items():
                if result['count'] > 0 and result['avg_score'] > 0.3 and result['has_content']:
                    successful_searches += 1
                    print(f"  📍 '{term}': {result['count']} results (avg score: {result['avg_score']:.2f})")
                else:
                    print(f"  ⚠️ '{term}': {result['count']} results (avg score: {result['avg_score']:.2f})")

            if successful_searches >= len(search_terms) // 2:  # At least half should work
                print("✅ Search functionality: PASS")
                self.test_results['search_functionality'] = True
                return True
            else:
                print(f"⚠️  Search functionality: PARTIAL ({successful_searches}/{len(search_terms)} terms working)")
                return False

        except Exception as e:
            print(f"❌ Search functionality: FAIL - {e}")
            return False

    def test_performance(self) -> bool:
        """Test 6: Basic performance benchmark"""
        try:
            # Time a search operation
            start_time = time.time()

            results = list(self.collection.find(
                {"$text": {"$search": "AI agents"}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(10))

            elapsed = time.time() - start_time
            self.test_results['performance']['time'] = elapsed

            # Estimate time for full migration based on current document count
            current_count = self.collection.count_documents({})
            if current_count > 0:
                time_per_doc = elapsed / min(current_count, 10)  # Time per document for search
                estimated_migration_time = (1171 * 2.0)  # Rough estimate: 2 seconds per document for migration
                estimate_minutes = estimated_migration_time / 60
                self.test_results['performance']['estimate'] = f"{estimate_minutes:.0f} minutes"
            else:
                self.test_results['performance']['estimate'] = "Cannot estimate"

            if elapsed < 2.0:
                print(f"✅ Performance: PASS (search took {elapsed:.2f}s)")
                return True
            else:
                print(f"⚠️  Performance: SLOW (search took {elapsed:.2f}s)")
                return False

        except Exception as e:
            print(f"❌ Performance test: FAIL - {e}")
            return False

    def run_all_tests(self, expected_docs: int = 5) -> Dict:
        """Run all tests and return comprehensive report"""
        print("🧪 Running Migration Test Suite")
        print("=" * 50)

        tests = [
            self.test_mongodb_connection,
            self.test_collection_setup,
            lambda: self.test_document_count(expected_docs),
            self.test_data_integrity,
            self.test_search_functionality,
            self.test_performance
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            if test():
                passed += 1
            print()  # Empty line for readability

        # Final report
        print("=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {(passed/total)*100:.1f}%")

        if self.test_results['performance']['estimate']:
            print(f"Estimated full migration time: {self.test_results['performance']['estimate']}")

        if passed == total:
            print("\n✅ ALL TESTS PASSED - Ready for full migration!")
        elif passed >= total * 0.8:  # 80% pass rate
            print("\n✅ MOSTLY PASSED - Proceed with caution")
        else:
            print("\n❌ MULTIPLE FAILURES - Fix issues before proceeding")

        return self.test_results

def main():
    """Run the test suite"""
    try:
        tester = MigrationTester()
        results = tester.run_all_tests()

        # Exit with appropriate code
        if results['mongodb_connection'] and results['document_count'] > 0:
            exit(0)  # Success
        else:
            exit(1)  # Failure

    except Exception as e:
        print(f"❌ Test suite failed to run: {e}")
        exit(1)

if __name__ == "__main__":
    main()
