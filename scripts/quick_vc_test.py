#!/usr/bin/env python3
"""Quick VC Search Test - Tests key VC scenarios in 5 minutes"""

import requests
import time
from datetime import datetime

VERCEL_BASE = 'https://podinsight-api.vercel.app'
vc_queries = [
    ('AI startup valuations', 'Investment analysis'),
    ('Series A metrics benchmarks', 'Funding stages'),
    ('product market fit indicators', 'Business strategy'),
    ('venture debt vs equity', 'Financing options'),
    ('founder burnout mental health', 'Leadership insights'),
    ('down round negotiations', 'Market conditions'),
    ('crypto bear market opportunities', 'Investment timing'),
    ('LLM moat defensibility', 'Technical strategy'),
    ('network effects marketplaces', 'Business models'),
    ('remote team productivity', 'Operations')
]

print('🚀 Quick VC Search Test Started')
print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'API: {VERCEL_BASE}')
print('-' * 60)

total_tests = len(vc_queries)
successful_tests = 0
failed_tests = 0
total_results = 0
vector_searches = 0
text_searches = 0

for i, (query, category) in enumerate(vc_queries):
    try:
        print(f'\n{i+1}/{total_tests}. Testing: "{query}" ({category})')
        start = time.time()

        response = requests.post(
            f'{VERCEL_BASE}/api/search',
            json={'query': query, 'limit': 3},
            timeout=20
        )

        latency = int((time.time() - start) * 1000)

        if response.status_code == 200:
            data = response.json()
            result_count = len(data.get('results', []))
            search_method = data.get('search_method', 'unknown')

            total_results += result_count
            if search_method == 'vector_768d':
                vector_searches += 1
            elif search_method == 'text':
                text_searches += 1

            # Get first result score if available
            first_score = ''
            if result_count > 0 and 'results' in data:
                score = data['results'][0].get('similarity_score', 0)
                first_score = f', score: {score:.3f}'

            print(f'   ✅ {latency}ms - {result_count} results ({search_method}{first_score})')
            successful_tests += 1
        else:
            print(f'   ❌ Status: {response.status_code}')
            failed_tests += 1

        time.sleep(0.5)  # Small delay between requests

    except Exception as e:
        print(f'   ❌ ERROR: {str(e)}')
        failed_tests += 1

# Summary
print('\n' + '=' * 60)
print('📊 TEST SUMMARY')
print('=' * 60)
print(f'Total Tests: {total_tests}')
print(f'Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)')
print(f'Failed: {failed_tests}')
print(f'Total Results Found: {total_results}')
print(f'Vector Searches: {vector_searches}')
print(f'Text Searches: {text_searches}')
print(f'Average Results per Query: {total_results/successful_tests:.1f}' if successful_tests > 0 else 'N/A')

# Performance check
if successful_tests == total_tests:
    print('\n✅ ALL TESTS PASSED!')
elif successful_tests >= total_tests * 0.8:
    print('\n⚠️  MOSTLY PASSED (>80% success rate)')
else:
    print('\n❌ TESTS FAILED (Low success rate)')

print(f'\nCompleted at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
