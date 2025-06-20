# MongoDB Text Search Scoring Explained

## Why "207% relevance"? 

You caught an important issue! MongoDB text search scores are **NOT percentages**.

### MongoDB Scoring System

MongoDB's text search returns a **relevance score** that:
- Can be any positive number (0.5, 1.0, 2.5, 10.0, etc.)
- Higher = more relevant
- NOT limited to 0-100%
- Based on term frequency and document relevance

### Typical Score Ranges

From our tests:
- **Low relevance**: 0.5 - 1.0
- **Good relevance**: 1.0 - 2.0  
- **High relevance**: 2.0 - 3.0+

Our search results showed scores of 1.98 - 3.03, indicating high-quality matches.

### The Display Problem

The code incorrectly formatted MongoDB scores as percentages:
```python
# WRONG - MongoDB scores aren't percentages!
print(f"Score: {result.similarity_score:.1%}")  # Shows "206.9%"

# CORRECT - Show as score value
print(f"Score: {result.similarity_score:.2f}")  # Shows "2.07"
```

### User-Friendly Alternatives

Instead of showing raw scores to users, we could:
1. **Star ratings**: ⭐⭐⭐⭐⭐ (5 stars for score > 2.5)
2. **Labels**: "Excellent Match", "Good Match", "Fair Match"
3. **Bar visualization**: ████████░░ (80% filled)
4. **Simply hide scores** and rely on ranking order

### What Really Matters

The important improvement isn't the score number, but:
- **Real excerpts** vs generic placeholders
- **Actual conversation content** users can preview
- **Highlighted search terms** for quick scanning
- **Better ranking** of truly relevant episodes

The scoring display can be refined, but the core value is already delivered!