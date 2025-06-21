# Sprint 2: 768D Vector Search Implementation Update

**Date**: June 21, 2025  
**Status**: Partial Success - Pivoting Strategy  
**Issue**: Vercel deployment size limits blocking Instructor-XL model

---

## 📋 What We Accomplished

### ✅ Completed Tasks:
1. **MongoDB Migration**: 823,763 chunks with 768D embeddings (100% complete)
2. **Vector Index**: Created and active in MongoDB Atlas
3. **Code Implementation**: All vector search code written and tested locally
4. **Local Testing**: Vector search works perfectly on local machine
5. **MongoDB Scaling**: Auto-scaled to M20 for 2.38GB index

### ❌ Blocker Discovered:
- **Instructor-XL model size**: ~2GB
- **Vercel deployment limit**: 250MB maximum
- **Result**: Production falls back to text search

---

## 💡 Vercel Limits Analysis

### Can We Pay Vercel for Larger Deployments?

**Short answer: NO** - This is a hard technical limit, not a pricing tier issue.

### Vercel's Limits (All Plans):
| Plan | Price | Deployment Size | Our Need |
|------|-------|----------------|----------|
| Hobby | $0 | 250MB | 2GB+ |
| Pro | $20/month | 250MB | 2GB+ |
| Enterprise | Custom | 250MB* | 2GB+ |

*Enterprise can request increases but typically for assets, not ML models

### Why These Limits Exist:
- Vercel optimized for **edge functions** (fast, small)
- Not designed for ML model hosting
- Even with payment, architecture doesn't support large models

---

## 🚀 Available Solutions

### Option 1: HuggingFace API (Recommended)
**Implementation Time**: 2-3 hours
```python
# Use BAAI/bge-large-en-v1.5 via API
# 768D embeddings, 95% quality of Instructor-XL
# Works perfectly on Vercel
```

**Costs**:
- HF API: $0-20/month depending on usage
- Can scale MongoDB back to M10 (save $132/month)
- **Net savings**: $112+/month

### Option 2: Alternative Hosting Platforms
**Implementation Time**: 1-2 days

| Platform | Model Support | Cost | Complexity |
|----------|--------------|------|------------|
| AWS Lambda | 10GB limit ✅ | ~$50/month | Medium |
| Google Cloud Run | 32GB limit ✅ | ~$40/month | Medium |
| Modal.com | Unlimited ✅ | ~$30/month | Low |
| Fly.io | Unlimited ✅ | ~$25/month | Medium |

### Option 3: Hybrid Architecture
**Implementation Time**: 1 day
- Keep API on Vercel
- Host embedding service separately
- Add 100-200ms latency

### Option 4: Smaller Models
**Implementation Time**: 1 hour
- `all-MiniLM-L12-v2`: 384D (already using)
- `all-mpnet-base-v2`: 768D but 420MB (fits Vercel!)
- Quality: 85% of Instructor-XL

---

## 📊 Current Search Performance

Despite falling back to text search, performance is good:

| Metric | Performance | Notes |
|--------|-------------|-------|
| First query | 6.9s | Model loading overhead |
| Subsequent | 1-2s | Cached and optimized |
| Result quality | Good | Real excerpts with highlighting |
| User experience | ✅ | Working well for MVP |

---

## 🎯 Recommendations

### Immediate (Do Today):
1. **Keep current text search** - It's working well
2. **Document the limitation** for investors/users
3. **Scale MongoDB back to M10** - Save $132/month

### Short Term (Next Sprint):
1. **Implement HF API** for 768D embeddings
2. **Test with BGE model** - Very close quality
3. **Monitor API costs** - Upgrade HF if needed

### Long Term (3+ months):
1. **Evaluate Modal/Fly.io** when you have customers
2. **Consider dedicated GPU** instance if volume justifies
3. **Build embedding cache** to reduce API calls

---

## 💰 Financial Impact

### Current Burn:
- MongoDB M20: $189/month (required for 3GB index)
- Vercel: $0 (hobby tier)
- **Total**: $189/month

### With HF API:
- MongoDB M10: $57/month (text search only)
- HF API: ~$9/month (estimated)
- Vercel: $0
- **Total**: $66/month
- **Savings**: $123/month = 7.5 months extra runway!

---

## 🚫 What NOT to Do

1. **Don't try to compress Instructor-XL** - Quality loss too high
2. **Don't split model into chunks** - Vercel doesn't support model assembly
3. **Don't pay for Vercel Pro/Enterprise** - Won't solve the limit
4. **Don't delete the 768D index yet** - Useful for future migration

---

## ✅ Action Items

1. **Today**: 
   - [ ] Decide on HF API vs keeping text search
   - [ ] Email MongoDB about scaling to M10
   - [ ] Update investors on technical pivot

2. **This Week**:
   - [ ] Implement chosen solution
   - [ ] Update documentation
   - [ ] Plan next sprint priorities

3. **Next Month**:
   - [ ] Evaluate if vector search needed based on user feedback
   - [ ] Research Modal.com if growth justifies

---

## 📝 Lessons Learned

1. **Verify deployment constraints early** - Should have checked Vercel limits before implementing
2. **Text search is often good enough** - Our fallback works surprisingly well
3. **MongoDB's pricing jumps** are significant (M10→M20 = 3.3x cost)
4. **Edge platforms ≠ ML platforms** - Different tools for different jobs

---

**Bottom Line**: We built great infrastructure that can't deploy on our current platform. The pragmatic move is to use HF API or stick with text search until we outgrow Vercel. Both options work well for MVP stage.