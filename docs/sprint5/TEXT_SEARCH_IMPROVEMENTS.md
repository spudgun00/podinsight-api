# Text Search Improvements

**Date**: 2025-01-13
**Sprint**: 5
**Issue**: Text search contributing 0% to scores despite 40% weight

## Problem Identified

Text search was failing because:
1. Podcast transcripts use varied terminology (e.g., "artificial intelligence" vs "AI")
2. Speech-to-text introduces variations ("A.I." vs "AI")
3. Natural speech patterns don't match search keywords exactly

Example: Query "AI valuations" missed:
- "artificial intelligence pricing"
- "ML company valuations"
- "these A.I. companies are valued at"

## Solutions Implemented

### 1. Synonym Expansion

Added synonym mapping for common VC terms:
```python
synonyms = {
    'ai': ['artificial intelligence', 'ml', 'machine learning', 'deep learning'],
    'vcs': ['venture capitalists', 'investors', 'venture capital'],
    'valuations': ['valuation', 'valued', 'pricing', 'price', 'worth'],
    'startup': ['startups', 'company', 'companies'],
    'funding': ['investment', 'raise', 'round', 'capital'],
    'crypto': ['cryptocurrency', 'blockchain', 'web3'],
    'saas': ['software as a service', 'subscription']
}
```

Now searching for "AI valuations" also searches for:
- "artificial intelligence valuations"
- "ML pricing"
- "machine learning worth"
- etc.

### 2. Adjusted Scoring Weights

Changed from 40/40/20 to 60/25/15:
- **Vector Search**: 40% → 60% (increased - it works better for transcripts)
- **Text Search**: 40% → 25% (decreased - often fails to match)
- **Domain Boost**: 20% → 15% (slightly decreased)

### 3. Updated Relevance Threshold

With new weights, scores will be different:
- Old: 0.962 × 0.4 + 0 × 0.4 + 0.1 × 0.2 = 0.425
- New: 0.962 × 0.6 + 0 × 0.25 + 0.1 × 0.15 = 0.592

Adjusted `RELEVANCE_THRESHOLD` from 0.42 to 0.55.

## Expected Impact

1. **Better Text Matching**: Synonyms should increase text search hit rate
2. **Higher Scores**: Vector search's increased weight means good matches score higher
3. **More Consistent Results**: Less dependent on exact phrase matching

## Example Score Calculation

For "AI valuations" query with same results:
- Vector: 96.2% match
- Text: Now might get 30% match (with synonyms)
- Domain: 10% boost

Old score: 0.962×0.4 + 0×0.4 + 0.1×0.2 = 0.405
New score: 0.962×0.6 + 0.3×0.25 + 0.1×0.15 = 0.667

Much better representation of actual relevance!

## Next Steps

1. Monitor text search hit rates with synonym expansion
2. Fine-tune synonym mappings based on actual transcript vocabulary
3. Consider adding more domain-specific synonyms
4. Potentially implement fuzzy matching for common transcription errors
