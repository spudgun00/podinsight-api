================================================================================
EPISODE INTELLIGENCE E2E TEST REPORT
Generated: 2025-07-09T14:34:24.919414
================================================================================

## SUMMARY
Total Tests: 20
Passed: 17 ✅
Failed: 0 ❌
Warnings: 3 ⚠️
Success Rate: 85.0%

## PERFORMANCE SUMMARY
health: 111ms (threshold: 200ms) ✅
dashboard: 58ms (threshold: 500ms) ✅
brief: 37ms (threshold: 2000ms) ✅
preferences: 39ms (threshold: 500ms) ✅

## DATA INTEGRITY CHECKS

### GUID Matching
  total_intelligence_docs: 50
  matching_episodes: 50
  non_matching_episodes: 0
  match_rate: 100.0%

### Signal Extraction
  total_episodes: 50
  episodes_with_signals: 49
  empty_episodes: 1
  success_rate: 98.0%
  signal_distribution: {'total_investable': 102, 'total_competitive': 102, 'total_portfolio': 56, 'total_soundbites': 332}

### Collection Counts
  episode_metadata: 1236
  episode_intelligence: 50
  podcast_authority: 17
  user_intelligence_prefs: 0

## DETAILED TEST RESULTS

✅ Health Check
   Status: PASS
   Message: Service healthy, MongoDB connected to podinsight
   Duration: 111ms

✅ Required Collections Check
   Status: PASS
   Message: All required collections present

✅ Episode Data Check
   Status: PASS
   Message: Found 1236 episodes in metadata

⚠️ Dashboard Basic Request
   Status: WARN
   Message: Returned 0 episodes
   Duration: 58ms

⚠️ Dashboard Debug Analysis
   Status: WARN
   Message: Debug info: First 10 episodes checked: [{'count': 1, 'episode_id': '0e983347-7815-4b62-87a6-84d988a772b7', 'guid': '0e983347-7815-4b62-87a6-84d988a772b7', 'used_id': '0e983347-7815-4b62-87a6-84d988a772b7'}, {'count': 2, 'episode_id': '1216c2e7-42b8-42ca-92d7-bad784f80af2', 'guid': '1216c2e7-42b8-42ca-92d7-bad784f80af2', 'used_id': '1216c2e7-42b8-42ca-92d7-bad784f80af2'}, {'count': 3, 'episode_id': '24fed311-54ac-4dab-805a-ea90cd455b3b', 'guid': '24fed311-54ac-4dab-805a-ea90cd455b3b', 'used_id': '24fed311-54ac-4dab-805a-ea90cd455b3b'}, {'count': 4, 'episode_id': '46dc5446-2e3b-46d6-b4af-24e7c0e8beff', 'guid': '46dc5446-2e3b-46d6-b4af-24e7c0e8beff', 'used_id': '46dc5446-2e3b-46d6-b4af-24e7c0e8beff'}, {'count': 5, 'episode_id': '4c2fe9c7-ce0c-4ee2-a93e-993327035281', 'guid': '4c2fe9c7-ce0c-4ee2-a93e-993327035281', 'used_id': '4c2fe9c7-ce0c-4ee2-a93e-993327035281'}, {'count': 6, 'episode_id': '4df073b5-c70b-4516-af04-7302c5e6d635', 'guid': '4df073b5-c70b-4516-af04-7302c5e6d635', 'used_id': '4df073b5-c70b-4516-af04-7302c5e6d635'}, {'count': 7, 'episode_id': '55fd6289-2840-40e3-a148-7fa924c9af57', 'guid': '55fd6289-2840-40e3-a148-7fa924c9af57', 'used_id': '55fd6289-2840-40e3-a148-7fa924c9af57'}, {'count': 8, 'episode_id': '5c4c0a9d-328c-4d75-a511-7ffcb7f3eb85', 'guid': '5c4c0a9d-328c-4d75-a511-7ffcb7f3eb85', 'used_id': '5c4c0a9d-328c-4d75-a511-7ffcb7f3eb85'}, {'count': 9, 'episode_id': '61719217-bf40-4998-be1a-23bef65fc813', 'guid': '61719217-bf40-4998-be1a-23bef65fc813', 'used_id': '61719217-bf40-4998-be1a-23bef65fc813'}, {'count': 10, 'episode_id': '61e87d66-f357-496f-abc2-2052be163a85', 'guid': '61e87d66-f357-496f-abc2-2052be163a85', 'used_id': '61e87d66-f357-496f-abc2-2052be163a85'}]

✅ Dashboard Limit Parameter
   Status: PASS
   Message: Limit respected: returned 0 episodes

✅ Brief Valid Episode
   Status: PASS
   Message: Retrieved brief for episode: White House BTS, Google buys Wiz, Treasury vs Fed, Space Rescue
   Duration: 37ms

✅ Brief Structure Validation
   Status: PASS
   Message: All required fields present

✅ Key Insights Extraction
   Status: PASS
   Message: Extracted 3 key insights

✅ Brief Invalid Episode
   Status: PASS
   Message: Correctly returned 404 for invalid episode

✅ Share Invalid Method
   Status: PASS
   Message: Correctly rejected invalid share method

✅ Update Preferences
   Status: PASS
   Message: Preferences updated successfully
   Duration: 39ms

✅ Preferences Validation
   Status: PASS
   Message: Preferences correctly stored and returned

✅ GUID Matching Check
   Status: PASS
   Message: 100.0% of intelligence docs have matching metadata

✅ Signal Extraction Rate
   Status: PASS
   Message: 98.0% of episodes have extracted signals

⚠️ Empty Episodes Sample
   Status: WARN
   Message: Sample empty episodes: ['46dc5446-2e3b-46d6-b4af-24e7c0e8beff']

✅ MongoDB Collections Check
   Status: PASS
   Message: All required collections present (10 total)

✅ Signal Types Check
   Status: PASS
   Message: Signal types found: ['investable', 'competitive', 'portfolio', 'soundbites']

✅ Performance: health
   Status: PASS
   Message: Average response time: 41ms (threshold: 200ms)

✅ Performance: dashboard
   Status: PASS
   Message: Average response time: 54ms (threshold: 500ms)
