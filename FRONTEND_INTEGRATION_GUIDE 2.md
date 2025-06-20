# PodInsightHQ API - Frontend Integration Guide

**Last Updated:** June 15, 2025  
**API Version:** 1.0.0  
**Status:** ✅ DEPLOYED & OPERATIONAL  

## 🚀 Quick Start

**Production API Base URL:** `https://podinsight-api.vercel.app`

**Main Endpoint:** `https://podinsight-api.vercel.app/api/topic-velocity`

## 📊 API Endpoints

### 1. Health Check
```
GET https://podinsight-api.vercel.app/
```

**Response:**
```json
{
  "status": "healthy",
  "service": "PodInsightHQ API",
  "version": "1.0.0",
  "env_check": {
    "SUPABASE_URL": true,
    "SUPABASE_KEY": true,
    "PYTHON_VERSION": "3.12"
  }
}
```

### 2. Topic Velocity (Main Endpoint)
```
GET https://podinsight-api.vercel.app/api/topic-velocity
```

**Query Parameters:**
- `weeks` (optional): Number of weeks to return (default: 12)
- `topics` (optional): Comma-separated list of topics to track

**Response Format (Recharts-compatible):**
```json
{
  "data": {
    "AI Agents": [
      {
        "week": "2025-W12",
        "mentions": 1,
        "date": "Mar 17-23"
      },
      // ... more weeks
    ],
    "Capital Efficiency": [
      // ... weekly data
    ],
    "DePIN": [
      // ... weekly data
    ],
    "B2B SaaS": [
      // ... weekly data
    ]
  },
  "metadata": {
    "total_episodes": 1171,
    "date_range": "2025-01-01 to 2025-06-15",
    "data_completeness": "topics_only"
  }
}
```

## 🎯 Important: Topic Names

**These must match EXACTLY (case-sensitive, spacing matters):**

1. `"AI Agents"` - AI and autonomous agent discussions
2. `"Capital Efficiency"` - Burn rate, runway, cash management
3. `"DePIN"` - Decentralized Physical Infrastructure
4. `"B2B SaaS"` - Business software and enterprise SaaS
5. `"Crypto/Web3"` - Cryptocurrency and Web3 (NO spaces around /)

⚠️ **Critical:** `"Crypto/Web3"` has no spaces. Using `"Crypto / Web3"` will return 0 results.

## 💻 Frontend Implementation Examples

### React + Fetch
```javascript
const API_URL = 'https://podinsight-api.vercel.app/api/topic-velocity';

// Default request (4 topics, 12 weeks)
const fetchTopicData = async () => {
  try {
    const response = await fetch(API_URL);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching topic data:', error);
  }
};

// Custom parameters
const fetchCustomData = async (weeks = 4, topics = ['AI Agents', 'DePIN']) => {
  const params = new URLSearchParams({
    weeks: weeks,
    topics: topics.join(',')
  });
  
  const response = await fetch(`${API_URL}?${params}`);
  return response.json();
};
```

### Axios Example
```javascript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'https://podinsight-api.vercel.app',
  timeout: 5000
});

// Get topic velocity data
const getTopicVelocity = async (weeks, topics) => {
  const { data } = await apiClient.get('/api/topic-velocity', {
    params: { weeks, topics }
  });
  return data;
};
```

### React Query Example
```javascript
import { useQuery } from '@tanstack/react-query';

const useTopicVelocity = (weeks = 12, topics) => {
  return useQuery({
    queryKey: ['topicVelocity', weeks, topics],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (weeks) params.append('weeks', weeks);
      if (topics) params.append('topics', topics);
      
      const response = await fetch(
        `https://podinsight-api.vercel.app/api/topic-velocity?${params}`
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch topic data');
      }
      
      return response.json();
    },
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
    staleTime: 4 * 60 * 1000, // Consider data stale after 4 minutes
  });
};
```

## 📈 Recharts Integration

The API response is formatted specifically for Recharts. Here's a complete example:

```jsx
import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const TopicVelocityChart = ({ data }) => {
  // Transform API data for Recharts
  const transformData = (apiData) => {
    const weeks = new Set();
    const topics = Object.keys(apiData);
    
    // Collect all weeks
    topics.forEach(topic => {
      apiData[topic].forEach(point => weeks.add(point.week));
    });
    
    // Create chart data
    return Array.from(weeks).sort().map(week => {
      const point = { week };
      topics.forEach(topic => {
        const topicData = apiData[topic].find(d => d.week === week);
        point[topic] = topicData ? topicData.mentions : 0;
      });
      return point;
    });
  };

  const chartData = transformData(data);
  
  const colors = {
    'AI Agents': '#10B981',
    'Capital Efficiency': '#6B46C1',
    'DePIN': '#3B82F6',
    'B2B SaaS': '#EF4444'
  };

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="week" />
        <YAxis />
        <Tooltip />
        <Legend />
        {Object.keys(colors).map(topic => (
          <Line
            key={topic}
            type="monotone"
            dataKey={topic}
            stroke={colors[topic]}
            strokeWidth={2}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
};
```

## 🔧 CORS Configuration

The API has CORS enabled for all origins:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

No additional CORS configuration needed for frontend development.

## ⚡ Performance Expectations

- **Average Response Time:** 50-100ms
- **Max Response Time:** < 500ms
- **Availability:** 99.9%
- **Rate Limits:** None currently (monitor usage)

## 🐛 Error Handling

### Possible Error Responses

1. **Invalid Parameters (400)**
```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["query", "weeks"],
      "msg": "Input should be a valid integer",
      "input": "invalid"
    }
  ]
}
```

2. **Server Error (500)**
```json
{
  "detail": "Failed to fetch topic velocity data: [error details]"
}
```

### Frontend Error Handling Example
```javascript
const fetchWithErrorHandling = async () => {
  try {
    const response = await fetch(API_URL);
    
    if (!response.ok) {
      // Handle HTTP errors
      if (response.status === 500) {
        throw new Error('Server error - please try again later');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
    
  } catch (error) {
    // Handle network errors
    if (error instanceof TypeError) {
      throw new Error('Network error - please check your connection');
    }
    throw error;
  }
};
```

## 🔐 Environment Variables for Frontend

When deploying your frontend to Vercel, add these environment variables:

```bash
# .env.local or Vercel Dashboard
NEXT_PUBLIC_API_URL=https://podinsight-api.vercel.app
NEXT_PUBLIC_API_TIMEOUT=5000
```

## 📱 Testing the API

### Browser Console Test
```javascript
// Quick test in browser console
fetch('https://podinsight-api.vercel.app/api/topic-velocity')
  .then(res => res.json())
  .then(console.log)
  .catch(console.error);
```

### cURL Test
```bash
# Default request
curl https://podinsight-api.vercel.app/api/topic-velocity

# With parameters
curl "https://podinsight-api.vercel.app/api/topic-velocity?weeks=4&topics=AI+Agents,DePIN"
```

## 📋 Deployment Checklist for Frontend

When deploying your frontend application:

- [ ] Set API URL environment variable
- [ ] Configure build command (e.g., `npm run build`)
- [ ] Set Node.js version if needed
- [ ] Enable HTTPS (automatic on Vercel)
- [ ] Test API connectivity after deployment
- [ ] Monitor for CORS issues (should be none)
- [ ] Set up error boundaries for API failures
- [ ] Implement loading states for API calls
- [ ] Add retry logic for failed requests

## 🎨 UI/UX Recommendations

1. **Loading States**
   - Show skeleton loader while fetching
   - ~50-100ms typical load time

2. **Empty States**
   - Some topics may have 0 mentions in certain weeks
   - Design for sparse data scenarios

3. **Time Range Selector**
   - Default: Last 12 weeks
   - Options: 4, 8, 12, 24 weeks
   - Max: 24 weeks (current data limit)

4. **Topic Selector**
   - Show all 5 available topics
   - Default: 4 main topics (exclude Crypto/Web3)
   - Allow multi-select up to 4 topics for clarity

## 📞 Support & Troubleshooting

### Common Issues

1. **"Crypto/Web3" returning 0 results**
   - Ensure no spaces around the forward slash
   - Correct: `"Crypto/Web3"`
   - Wrong: `"Crypto / Web3"`

2. **CORS errors**
   - Should not occur (API allows all origins)
   - If seen, check browser extensions blocking requests

3. **Timeout errors**
   - Increase client timeout beyond 5 seconds
   - API typically responds in 50-100ms

### API Status

Check API health: https://podinsight-api.vercel.app/

### Repository

Backend API Code: https://github.com/spudgun00/podinsight-api

---

**Note:** This API is currently in staging. For production use with custom domains or higher rate limits, please contact the development team.