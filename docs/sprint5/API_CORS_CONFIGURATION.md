# API CORS Configuration Guide

## Overview
This document provides instructions for configuring CORS (Cross-Origin Resource Sharing) headers in the PodInsight API to allow the frontend dashboard to communicate with the backend API.

## Problem
The frontend dashboard (running on `http://localhost:3000`, `http://localhost:3001`, etc.) needs to make API calls to the backend (`https://podinsight-api.vercel.app`). Without proper CORS headers, browsers block these requests for security reasons.

## Required CORS Headers

### For Development
```javascript
// Allow requests from localhost development servers
const allowedOrigins = [
  'http://localhost:3000',
  'http://localhost:3001',
  'http://localhost:3002',
  'http://localhost:3003',
  'http://127.0.0.1:3000',
  'http://127.0.0.1:3001',
  'http://127.0.0.1:3002',
  'http://127.0.0.1:3003'
];
```

### For Production
```javascript
// Add your production domain
const productionOrigins = [
  'https://podinsight-dashboard.vercel.app',
  'https://podinsighthq.com',
  'https://www.podinsighthq.com'
];
```

## Implementation Options

### Option 1: Express.js Middleware (Recommended)

If your API uses Express.js, install the `cors` package:

```bash
npm install cors
```

Then configure it in your main server file:

```javascript
const express = require('express');
const cors = require('cors');
const app = express();

// CORS configuration
const corsOptions = {
  origin: function (origin, callback) {
    const allowedOrigins = [
      'http://localhost:3000',
      'http://localhost:3001',
      'http://localhost:3002',
      'http://localhost:3003',
      'https://podinsight-dashboard.vercel.app',
      // Add your production domains here
    ];

    // Allow requests with no origin (like mobile apps or curl requests)
    if (!origin) return callback(null, true);

    if (allowedOrigins.indexOf(origin) !== -1) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true, // Allow cookies to be sent
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
  exposedHeaders: ['X-Total-Count', 'X-Page-Count'], // If you need to expose custom headers
  maxAge: 86400 // Cache preflight response for 24 hours
};

app.use(cors(corsOptions));
```

### Option 2: Vercel Configuration

If your API is deployed on Vercel, add this to your `vercel.json`:

```json
{
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Credentials", "value": "true" },
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Access-Control-Allow-Methods", "value": "GET,OPTIONS,PATCH,DELETE,POST,PUT" },
        { "key": "Access-Control-Allow-Headers", "value": "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization" }
      ]
    }
  ]
}
```

For more restrictive CORS (recommended), use a function to check origins:

```javascript
// api/cors-middleware.js
export function corsMiddleware(req, res) {
  const allowedOrigins = [
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:3002',
    'http://localhost:3003',
    'https://podinsight-dashboard.vercel.app'
  ];

  const origin = req.headers.origin;

  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
  }

  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Max-Age', '86400');
}
```

### Option 3: Manual Headers (For Custom Implementations)

If you're handling requests manually, add these headers to every API response:

```javascript
// For each API endpoint
function handleRequest(req, res) {
  const origin = req.headers.origin;
  const allowedOrigins = [
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:3002',
    'http://localhost:3003',
    'https://podinsight-dashboard.vercel.app'
  ];

  // Check if origin is allowed
  if (allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
  }

  // Set other CORS headers
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  // Your API logic here
}
```

## Affected Endpoints

Make sure CORS is configured for all these endpoints:

1. **Topic Velocity**: `/api/topic-velocity`
2. **Sentiment Analysis**: `/api/sentiment_analysis_v2`
3. **Signals**: `/api/signals`
4. **Intelligence Dashboard**: `/api/intelligence/dashboard`
5. **Intelligence Brief**: `/api/intelligence/brief/:id`
6. **Episode Search**: `/api/intelligence/search`
7. **Prewarm**: `/api/prewarm` (if implemented)

## Testing CORS Configuration

### 1. Using curl
```bash
# Test preflight request
curl -X OPTIONS https://podinsight-api.vercel.app/api/topic-velocity \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v

# Test actual request
curl https://podinsight-api.vercel.app/api/topic-velocity \
  -H "Origin: http://localhost:3000" \
  -v
```

### 2. Expected Response Headers
```
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
```

## Security Considerations

1. **Never use `Access-Control-Allow-Origin: *` in production** with credentials
2. **Explicitly list allowed origins** rather than using wildcards
3. **Validate origins** against a whitelist
4. **Use HTTPS** for production domains
5. **Limit allowed methods** to only what's needed
6. **Set appropriate max-age** for preflight caching

## Environment-Based Configuration

```javascript
// Recommended approach
const isDevelopment = process.env.NODE_ENV === 'development';

const corsOptions = {
  origin: function (origin, callback) {
    let allowedOrigins = [];

    if (isDevelopment) {
      // Allow all localhost ports in development
      allowedOrigins = [
        /^http:\/\/localhost:\d+$/,
        /^http:\/\/127\.0\.0\.1:\d+$/
      ];
    } else {
      // Strict origins in production
      allowedOrigins = [
        'https://podinsight-dashboard.vercel.app',
        'https://podinsighthq.com',
        'https://www.podinsighthq.com'
      ];
    }

    // Check if origin matches
    const isAllowed = allowedOrigins.some(allowed => {
      if (allowed instanceof RegExp) {
        return allowed.test(origin);
      }
      return allowed === origin;
    });

    if (!origin || isAllowed) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
};
```

## Troubleshooting

### Common Issues

1. **"No 'Access-Control-Allow-Origin' header is present"**
   - Ensure CORS middleware is applied before route handlers
   - Check that the origin is in the allowed list

2. **"CORS policy: The request client is not a secure context"**
   - This happens with HTTP in production; use HTTPS

3. **Preflight requests failing**
   - Ensure OPTIONS requests are handled properly
   - Check that all requested headers are in allowedHeaders

4. **Credentials not working**
   - Set `Access-Control-Allow-Credentials: true`
   - Don't use wildcard origin with credentials

## Quick Fix for Development

If you need a quick fix for development only, you can use a permissive CORS policy:

```javascript
// WARNING: Only for development!
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.header('Access-Control-Allow-Credentials', 'true');

  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }

  next();
});
```

## Contact

If you need help implementing these changes, please reach out to the frontend team with:
1. Your current API framework (Express, Vercel Functions, etc.)
2. Current deployment platform
3. List of production domains that need access
