#!/usr/bin/env python3
"""Test Unicode and emoji handling for Modal.com embedding endpoint"""

import requests
import json
import time
from typing import Dict, Any

# Modal endpoint
ENDPOINT = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

def test_unicode_query(test_name: str, query: str) -> Dict[str, Any]:
    """Test a single Unicode/emoji query"""
    print(f"\n🧪 Testing: {test_name}")
    print(f"   Query: {query}")
    print(f"   Length: {len(query)} chars")
    
    start_time = time.time()
    
    try:
        # Make request
        response = requests.post(
            ENDPOINT,
            json={"text": query},
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        result = {
            "test_name": test_name,
            "query": query,
            "status_code": response.status_code,
            "elapsed_time": elapsed,
            "success": False,
            "error": None,
            "embedding_dim": None
        }
        
        if response.status_code == 200:
            data = response.json()
            if "embedding" in data and isinstance(data["embedding"], list):
                result["embedding_dim"] = len(data["embedding"])
                result["success"] = result["embedding_dim"] == 768
                print(f"   ✅ Status: {response.status_code}")
                print(f"   ✅ Embedding dimension: {result['embedding_dim']}")
                # Show first few values to verify it's not all zeros
                first_values = data["embedding"][:5]
                print(f"   ✅ First 5 values: {[f'{v:.4f}' for v in first_values]}")
            else:
                result["error"] = "Invalid response format"
                print(f"   ❌ Invalid response format")
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            print(f"   ❌ Status: {response.status_code}")
            print(f"   ❌ Error: {response.text[:200]}")
            
        print(f"   ⏱️  Time: {elapsed:.2f}s")
        
    except Exception as e:
        elapsed = time.time() - start_time
        result = {
            "test_name": test_name,
            "query": query,
            "status_code": None,
            "elapsed_time": elapsed,
            "success": False,
            "error": str(e),
            "embedding_dim": None
        }
        print(f"   ❌ Exception: {str(e)}")
        print(f"   ⏱️  Time: {elapsed:.2f}s")
    
    return result

def main():
    print("=" * 80)
    print("🌍 UNICODE & EMOJI HANDLING TEST")
    print("Testing Modal.com embedding endpoint with international characters")
    print("=" * 80)
    
    # Test cases with various Unicode and emoji
    test_cases = [
        # Emoji tests
        ("Single emoji", "🦄"),
        ("Emoji with text", "🦄 startup valuations"),
        ("Multiple emojis", "🚀💰📈 venture capital"),
        ("Emoji in sentence", "The startup raised 💵 $10M in Series A 🎉"),
        ("Complex emoji", "👨‍💻👩‍💻 founders building AI 🤖"),
        
        # Latin scripts with accents
        ("French", "Les startups françaises lèvent des fonds"),
        ("Spanish", "¿Cómo evaluar startups en América Latina?"),
        ("German", "Risikokapital für Münchner Startups"),
        ("Portuguese", "Avaliação de startups no Brasil"),
        
        # Non-Latin scripts
        ("Chinese (Simplified)", "创业公司估值方法"),
        ("Chinese (Traditional)", "創業投資基金"),
        ("Japanese", "スタートアップの評価方法"),
        ("Korean", "스타트업 평가 방법"),
        ("Arabic", "تقييم الشركات الناشئة"),
        ("Hebrew", "הערכת סטארטאפים"),
        ("Russian", "Оценка стартапов"),
        ("Greek", "Αξιολόγηση νεοφυών επιχειρήσεων"),
        
        # Mixed scripts
        ("English + Chinese", "AI startup 人工智能创业公司"),
        ("Emoji + Japanese", "🚀 スタートアップ ecosystem"),
        ("Multi-language", "Startup (新創) funding מימון تمويل"),
        
        # Special Unicode cases
        ("Right-to-left", "مرحبا startup world"),
        ("Combining characters", "e\u0301 (é) valuation"),
        ("Mathematical symbols", "Startup growth → ∞"),
        ("Currency symbols", "Raised €5M, £4M, ¥500M"),
        ("Arrows and symbols", "Growth ↑ 📊 Revenue ↗️"),
        
        # Edge cases
        ("Zalgo text", "S̸t̷a̶r̴t̵u̸p̷ v̶a̸l̷u̴a̵t̶i̸o̷n̴"),
        ("Box drawing", "┌─ Startup ─┐ │ Funding │ └─────────┘"),
        ("Musical notes", "♪ ♫ Startup symphony ♬ ♭"),
        ("Chess symbols", "♔ King of startups ♕ ♖ ♗ ♘"),
        ("Braille", "⠎⠞⠁⠗⠞⠥⠏ (startup in Braille)")
    ]
    
    results = []
    passed = 0
    failed = 0
    
    print("\n📊 Running Unicode/emoji tests...")
    
    for test_name, query in test_cases:
        result = test_unicode_query(test_name, query)
        results.append(result)
        
        if result["success"]:
            passed += 1
        else:
            failed += 1
        
        time.sleep(0.5)  # Small delay between requests
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ Passed: {passed}/{len(test_cases)}")
    print(f"❌ Failed: {failed}/{len(test_cases)}")
    
    print("\n📈 Results by Category:")
    print("-" * 80)
    
    # Group results
    emoji_tests = results[:5]
    latin_tests = results[5:9]
    nonlatin_tests = results[9:17]
    mixed_tests = results[17:20]
    special_tests = results[20:25]
    edge_tests = results[25:]
    
    categories = [
        ("Emoji", emoji_tests),
        ("Latin with accents", latin_tests),
        ("Non-Latin scripts", nonlatin_tests),
        ("Mixed scripts", mixed_tests),
        ("Special Unicode", special_tests),
        ("Edge cases", edge_tests)
    ]
    
    for cat_name, cat_results in categories:
        cat_passed = sum(1 for r in cat_results if r["success"])
        cat_total = len(cat_results)
        print(f"\n{cat_name}: {cat_passed}/{cat_total} passed")
        for r in cat_results:
            status = "✅" if r["success"] else "❌"
            print(f"  {status} {r['test_name']}: {r['embedding_dim'] or 'FAILED'}D")
    
    print("\n🎯 Expected Behavior:")
    print("- All Unicode inputs → 768D embeddings")
    print("- Consistent performance across character sets")
    print("- No encoding errors or crashes")
    print("- Meaningful embeddings (not all zeros)")
    
    # Check for failures
    if failed > 0:
        print(f"\n⚠️  {failed} TESTS FAILED:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['test_name']}: {r['error']}")
    else:
        print("\n✅ All Unicode/emoji tests passed successfully!")

if __name__ == "__main__":
    main()