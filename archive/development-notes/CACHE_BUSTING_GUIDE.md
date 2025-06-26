# Vercel Cache Busting Guide

**Problem**: Code changes don't reflect immediately due to Vercel's caching layers

## 🚀 **Quick Cache Busting Methods**

### **Method 1: Force Fresh Deployment (Recommended)**
```bash
# Creates empty commit to trigger rebuild
git commit --allow-empty -m "deploy: Force cache refresh"
git push origin main

# Wait ~1-2 minutes for deployment
curl https://podinsight-api.vercel.app/api/health | grep deployment_time
```

### **Method 2: Vercel CLI (If Logged In)**
```bash
# Install Vercel CLI if needed
npm i -g vercel

# Login and force redeploy
vercel login
vercel --prod --force
```

### **Method 3: Cache-Busting URL Parameters**
```bash
# Add timestamp to bypass CDN cache
TIMESTAMP=$(date +%s)
curl "https://podinsight-api.vercel.app/api/search?v=$TIMESTAMP" \
  -X POST -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 1}'
```

### **Method 4: Check Deployment Time**
```bash
# Verify when the API was last deployed
curl https://podinsight-api.vercel.app/api/health | grep deployment_time

# Compare to when you made changes
echo "Current time: $(date -Iseconds)"
```

## 🔍 **Verifying Cache Status**

### **1. Check Health Endpoint**
```bash
curl https://podinsight-api.vercel.app/api/health
# Look for "deployment_time" field - should be recent
```

### **2. Test Search Endpoint**
```bash
# Test a specific feature you changed
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI", "limit": 1}' | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
r = data['results'][0] if data['results'] else {}
print(f'Episode title: \"{r.get(\"episode_title\", \"EMPTY\")}\"')
print(f'Published date: {r.get(\"published_date\", \"NOT FOUND\")}')
print(f'Excerpt length: {len(r.get(\"excerpt\", \"\"))} chars')
"
```

### **3. Compare Timestamps**
```bash
# Your local change time vs deployment time
echo "Local change: $(git log -1 --format='%ci')"
echo "Deployment: $(curl -s https://podinsight-api.vercel.app/api/health | grep -o '\"deployment_time\":\"[^\"]*\"')"
```

## ⚡ **Common Caching Issues**

### **Vercel Function Cache**
- **Issue**: Old function code still running
- **Solution**: Empty commit + push (Method 1)

### **CDN Cache**
- **Issue**: Edge cache serving old responses
- **Solution**: URL parameters (Method 3)

### **Browser Cache**
- **Issue**: Your browser caching API responses
- **Solution**: Hard refresh (Cmd+Shift+R) or incognito mode

## 🛠️ **Developer Workflow**

```bash
# Make code changes
git add .
git commit -m "feat: Your awesome feature"

# Push and force fresh deployment
git push origin main
git commit --allow-empty -m "deploy: Force refresh for testing"
git push origin main

# Wait and verify
sleep 60
curl https://podinsight-api.vercel.app/api/health | grep deployment_time

# Test your changes
curl -X POST https://podinsight-api.vercel.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 1}'
```

## 📋 **Troubleshooting Checklist**

- [ ] Made empty commit and pushed?
- [ ] Waited 1-2 minutes for deployment?
- [ ] Checked deployment_time in health endpoint?
- [ ] Tried cache-busting URL parameters?
- [ ] Tested in incognito browser window?
- [ ] Checked Vercel dashboard for deployment status?

## 🎯 **Pro Tips**

1. **Always check deployment_time first** - fastest way to verify cache status
2. **Use empty commits liberally** - they're free and guarantee fresh deployment
3. **Add timestamps to test requests** - helps bypass CDN caching
4. **Test in incognito** - avoids browser cache confusion

---

*Created: June 20, 2025*
*Last Updated: After UX improvements implementation*
