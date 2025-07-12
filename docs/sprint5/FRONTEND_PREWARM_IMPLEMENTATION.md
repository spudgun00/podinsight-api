# Frontend Pre-warming Implementation Guide

## Overview
We've created a backend endpoint that pre-warms the Modal embedding service. When users open the search UI, we can trigger this endpoint to eliminate the 18-second cold start delay.

## Backend Endpoint Ready
- **URL**: `POST /api/prewarm`
- **Response**: `{"status": "warming", "message": "Modal pre-warming initiated"}`
- **Behavior**: Fire-and-forget (returns immediately, warming happens in background)

## Frontend Implementation Required

### 1. Find the Search/Command Bar Component
Look for the component that handles the search UI (likely named `CommandBar`, `SearchBar`, or similar).

### 2. Add Pre-warming Logic
Add this to your search component:

```typescript
import { useEffect, useRef } from 'react';

// Inside your component
const hasWarmed = useRef(false);

useEffect(() => {
  // When search UI opens
  if (open && !hasWarmed.current) {
    // Fire pre-warm request (ignore response)
    fetch('/api/prewarm', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    }).catch(() => {
      // Silent fail is OK - pre-warming is optional
    });

    // Mark as warmed to prevent duplicate requests
    hasWarmed.current = true;

    // Reset after 3 minutes (in case Modal goes cold again)
    setTimeout(() => {
      hasWarmed.current = false;
    }, 180000); // 3 minutes
  }
}, [open]); // Trigger when 'open' state changes
```

### 3. Alternative: For Slash Key or Button Click
If you trigger search with a button or slash key:

```typescript
const handleSearchOpen = () => {
  // Your existing logic to open search
  setSearchOpen(true);

  // Add pre-warming
  if (!hasWarmed.current) {
    fetch('/api/prewarm', { method: 'POST' }).catch(() => {});
    hasWarmed.current = true;
  }
};
```

## Why This Works
- Users typically take 3-5 seconds to type their query
- Modal warms up in 2-3 seconds
- By the time they submit, Modal is ready!
- Cost: Only ~$5-10/month vs $50-100/month for 24/7 warming

## Testing
1. Open Network tab in DevTools
2. Open search UI
3. You should see a POST request to `/api/prewarm`
4. Type a query and submit - should be fast!

## Important Notes
- The prewarm request should fire when UI **opens**, not when query is submitted
- It's OK if the request fails - search will still work (just slower)
- Don't show any loading indicator for pre-warming
- The backend handles all the complexity

## Questions?
If you need any clarification or run into issues, the backend implementation is in:
- `/api/prewarm.py` - The pre-warming endpoint
- `/api/index.py` - Where it's registered

The pre-warming is completely optional - if not implemented, search still works but with cold start delays.
