# Critical Issues Remediation Plan - PodInsightHQ

**Created**: 2025-01-03
**Priority**: P0 - Must fix before public launch
**Estimated Total Effort**: 3-5 days

---

## 🚨 Issue 1: No Authentication - Exposed Backend

### What It Is
Public Next.js API routes (`/api/search`, `/api/v1/audio_clips/*`) use a server-side `BACKEND_API_TOKEN` to access the FastAPI backend. This means any unauthenticated user can trigger backend calls with elevated privileges.

**Current Flow**:
```
User → Next.js /api/search → FastAPI (with admin token) → Databases
        ↑ NO AUTH CHECK!
```

### Why It's a Critical Concern
- **Data Breach Risk**: Anyone can access all 823,763 transcript chunks
- **Resource Abuse**: No rate limiting = potential DoS attacks
- **Cost Explosion**: Unlimited OpenAI API calls could cost thousands
- **Compliance Violation**: No user tracking = can't meet GDPR requirements
- **Business Risk**: Competitors can scrape entire dataset

### Plan to Fix

#### Phase 1: Emergency Patch (4 hours)
1. Add basic API key authentication to Next.js routes
2. Implement simple rate limiting with memory store
3. Remove `BACKEND_API_TOKEN` from client-side code

#### Phase 2: Proper Auth System (2-3 days)
1. Implement NextAuth.js with email/OAuth providers
2. Add JWT-based session management
3. Create user table in Supabase
4. Implement role-based access control (RBAC)
5. Add API key management for programmatic access

### Repository & Files to Modify

**Repository**: `podinsight-dashboard` (Next.js)

```
Files to modify:
├── app/
│   ├── api/
│   │   ├── auth/             # NEW - Auth endpoints
│   │   │   ├── [...nextauth]/
│   │   │   │   └── route.ts  # NextAuth handler
│   │   │   └── middleware.ts # Auth middleware
│   │   ├── search/
│   │   │   └── route.ts      # Add auth check
│   │   └── v1/
│   │       └── audio_clips/
│   │           └── [episode_id]/
│   │               └── route.ts  # Add auth check
│   └── layout.tsx            # Add SessionProvider
├── lib/
│   ├── auth.ts              # NEW - Auth configuration
│   └── rate-limit.ts        # NEW - Rate limiting
└── middleware.ts            # NEW - Global auth middleware
```

### Implementation Code

```typescript
// lib/auth.ts
import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import { SupabaseAdapter } from "@auth/supabase-adapter"

export const { auth, signIn, signOut, handlers } = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    })
  ],
  adapter: SupabaseAdapter({
    url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
    secret: process.env.SUPABASE_SERVICE_KEY!,
  }),
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user
      const isApiRoute = nextUrl.pathname.startsWith('/api/')

      if (isApiRoute && !isLoggedIn) {
        return false // Redirect to login
      }

      return true
    }
  }
})

// app/api/search/route.ts (FIXED)
import { auth } from "@/lib/auth"
import { rateLimit } from "@/lib/rate-limit"

export async function POST(request: Request) {
  // Check authentication
  const session = await auth()
  if (!session) {
    return new Response("Unauthorized", { status: 401 })
  }

  // Check rate limit
  const identifier = session.user.email
  const { success } = await rateLimit.check(identifier, 20) // 20 req/min

  if (!success) {
    return new Response("Too many requests", { status: 429 })
  }

  // Continue with backend call...
  const body = await request.json()
  const response = await fetch(`${process.env.API_URL}/api/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${process.env.BACKEND_API_TOKEN}`
    },
    body: JSON.stringify(body)
  })

  return Response.json(await response.json())
}
```

### Acceptance Criteria
- [ ] All API routes require authentication
- [ ] Rate limiting prevents >20 requests/minute per user
- [ ] Backend token not accessible from browser DevTools
- [ ] Users can sign up/login with Google OAuth
- [ ] Session persists across page refreshes
- [ ] Unauthorized requests return 401
- [ ] Rate limited requests return 429
- [ ] Existing functionality works for authenticated users

### Testing Approach
```bash
# 1. Unit Tests (Jest)
- Test auth middleware with valid/invalid sessions
- Test rate limiter with burst requests
- Mock NextAuth for consistent testing

# 2. Integration Tests (Playwright)
- Login flow with Google OAuth
- API calls with/without auth
- Rate limit enforcement
- Session persistence

# 3. Security Tests
- Attempt to access API without auth
- Try to extract backend token
- Exceed rate limits
- Session hijacking attempts

# 4. Manual Testing Checklist
- [ ] Can't search without login
- [ ] Login with Google works
- [ ] Search works after login
- [ ] Logout clears session
- [ ] Rate limit message appears after 20 searches/min
```

---

## 🚨 Issue 2: GUID Field Naming Confusion

### What It Is
MongoDB collections use inconsistent field names for the episode identifier:
- `episode_metadata` collection: Uses `guid` field
- `transcript_chunks_768d` collection: Uses `episode_id` field (but contains GUID!)

This causes joins to fail if developers assume `episode_id` is a different ID system.

### Why It's a Critical Concern
- **Data Integrity**: Incorrect joins return wrong/no data
- **Performance**: Failed joins waste database resources
- **Developer Confusion**: New devs waste hours debugging
- **Business Impact**: Search results could miss relevant episodes
- **Maintenance Debt**: Gets worse as codebase grows

### Plan to Fix

#### Option A: Database Migration (Recommended - 1 day)
1. Add new `guid` field to `transcript_chunks_768d`
2. Copy `episode_id` values to `guid`
3. Update all queries to use `guid`
4. Drop `episode_id` field after verification

#### Option B: Code Abstraction Layer (Faster - 4 hours)
1. Create database abstraction layer
2. Map fields automatically in queries
3. Document extensively
4. Add linting rules

### Repository & Files to Modify

**Repository**: `podinsight-api` (FastAPI backend)

```
Files to modify:
├── api/
│   ├── db/
│   │   ├── mongodb.py        # Update field mappings
│   │   └── migrations/       # NEW
│   │       └── 001_fix_guid_field.py
│   ├── search.py            # Update queries
│   ├── models/
│   │   └── episode.py       # Update schema
│   └── utils/
│       └── query_builder.py # NEW - Abstraction layer
```

### Implementation Code

```python
# Option A: Migration Script
# api/db/migrations/001_fix_guid_field.py
from pymongo import MongoClient, UpdateOne
import os
from datetime import datetime

def migrate_guid_field():
    """Add guid field to transcript_chunks_768d collection"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client["podinsight"]
    collection = db["transcript_chunks_768d"]

    # Add guid field to all documents
    print(f"Starting migration at {datetime.now()}")

    # Get total count
    total = collection.count_documents({})
    print(f"Migrating {total} documents...")

    # Batch update for performance
    batch_size = 1000
    operations = []

    cursor = collection.find({}, {"_id": 1, "episode_id": 1})
    for doc in cursor:
        operations.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"guid": doc["episode_id"]}}
            )
        )

        if len(operations) >= batch_size:
            result = collection.bulk_write(operations)
            print(f"Updated {result.modified_count} documents")
            operations = []

    # Final batch
    if operations:
        result = collection.bulk_write(operations)
        print(f"Updated {result.modified_count} documents")

    # Create index on new field
    collection.create_index("guid")
    print("Created index on guid field")

    # Verify
    sample = collection.find_one({"guid": {"$exists": True}})
    print(f"Verification - Sample document: {sample}")

    print(f"Migration completed at {datetime.now()}")

# Option B: Abstraction Layer
# api/utils/query_builder.py
class MongoQueryBuilder:
    """Handles field name mapping for MongoDB queries"""

    FIELD_MAPPINGS = {
        "transcript_chunks_768d": {
            "guid": "episode_id"  # Maps logical name to actual field
        }
    }

    @classmethod
    def build_query(cls, collection_name: str, query: dict) -> dict:
        """Transform query to use correct field names"""
        if collection_name not in cls.FIELD_MAPPINGS:
            return query

        mappings = cls.FIELD_MAPPINGS[collection_name]
        transformed = {}

        for key, value in query.items():
            actual_field = mappings.get(key, key)
            transformed[actual_field] = value

        return transformed

    @classmethod
    def join_episodes_with_chunks(cls, episode_guid: str):
        """Properly join episode metadata with chunks"""
        return {
            "$lookup": {
                "from": "transcript_chunks_768d",
                "let": {"episode_guid": "$guid"},
                "pipeline": [
                    {"$match": {
                        "$expr": {"$eq": ["$episode_id", "$$episode_guid"]}
                    }}
                ],
                "as": "chunks"
            }
        }
```

### Acceptance Criteria
- [ ] All queries return correct data regardless of field name
- [ ] No hardcoded references to `episode_id` when meaning `guid`
- [ ] Documentation clearly explains the mapping
- [ ] New developers can understand within 5 minutes
- [ ] Performance unchanged or improved
- [ ] Zero data loss during migration

### Testing Approach
```python
# 1. Unit Tests
def test_guid_field_mapping():
    # Test that episode_id and guid return same results
    chunks_by_episode_id = db.transcript_chunks_768d.find_one(
        {"episode_id": "1216c2e7-42b8-42ca-92d7-bad784f80af2"}
    )
    chunks_by_guid = db.transcript_chunks_768d.find_one(
        {"guid": "1216c2e7-42b8-42ca-92d7-bad784f80af2"}
    )
    assert chunks_by_episode_id == chunks_by_guid

# 2. Integration Tests
- Test search endpoint returns correct episodes
- Test join queries work properly
- Verify no performance degradation

# 3. Data Validation
- Count total records before/after
- Verify all chunks have guid field
- Check index creation
- Sample 100 random joins
```

---

## 🚨 Issue 3: Hardcoded S3 File Paths

### What It Is
S3 files have complex, inconsistent naming patterns that don't match documentation:
- Docs say: `transcripts/transcript.json`
- Reality: `transcripts/{feed}-{date}-{title}_{guid[:8]}_raw_transcript.json`

Hardcoding paths causes failures when file naming patterns vary.

### Why It's a Critical Concern
- **Data Loss**: ETL scripts miss files = incomplete data
- **Brittle System**: Any S3 reorganization breaks everything
- **Maintenance Nightmare**: Each new podcast might have different patterns
- **Silent Failures**: Scripts continue but miss data
- **Scale Blocker**: Can't onboard new podcasts easily

### Plan to Fix

#### Implementation Plan (1 day)
1. Create S3 file discovery utility
2. Replace all hardcoded paths with dynamic discovery
3. Add pattern matching for known file types
4. Implement fallback strategies
5. Add comprehensive logging

### Repository & Files to Modify

**Repository**: `podinsight-etl` (Python ETL scripts)

```
Files to modify:
├── modules/
│   ├── s3_reader.py         # Main changes here
│   ├── file_discovery.py    # NEW - Discovery utility
│   └── s3_patterns.py       # NEW - Pattern definitions
├── tests/
│   └── test_file_discovery.py # NEW - Unit tests
└── main.py                  # Update to use discovery
```

### Implementation Code

```python
# modules/file_discovery.py
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError

@dataclass
class S3FilePattern:
    """Defines a pattern for finding files in S3"""
    file_type: str
    folder: str
    pattern: str
    required: bool = True

class S3FileDiscovery:
    """Dynamic file discovery for S3 buckets"""

    # Define known patterns
    FILE_PATTERNS = [
        S3FilePattern(
            file_type="transcript",
            folder="transcripts",
            pattern=r".*\.json$"
        ),
        S3FilePattern(
            file_type="meta",
            folder="meta",
            pattern=r"meta_.*_details\.json$"
        ),
        S3FilePattern(
            file_type="kpis",
            folder="kpis",
            pattern=r"kpis_.*\.json$"
        ),
        S3FilePattern(
            file_type="entities",
            folder="cleaned_entities",  # NOT "entities"!
            pattern=r".*_clean\.json$"
        ),
        S3FilePattern(
            file_type="embeddings",
            folder="embeddings",
            pattern=r".*_768d_unfiltered\.npy$",  # Prefer 768d version
            required=False  # Some episodes might not have embeddings
        ),
    ]

    def __init__(self, s3_client, bucket_name: str):
        self.s3 = s3_client
        self.bucket = bucket_name

    def discover_episode_files(
        self,
        feed_slug: str,
        guid: str
    ) -> Dict[str, Optional[str]]:
        """
        Discover all files for an episode using dynamic patterns

        Returns dict like:
        {
            'transcript': 's3://bucket/feed/guid/transcripts/complex_name.json',
            'meta': 's3://bucket/feed/guid/meta/meta_guid_details.json',
            'kpis': None,  # If not found
            ...
        }
        """
        results = {}
        base_prefix = f"{feed_slug}/{guid}/"

        for pattern in self.FILE_PATTERNS:
            file_path = self._find_file_by_pattern(
                base_prefix,
                pattern
            )

            if file_path is None and pattern.required:
                raise FileNotFoundError(
                    f"Required file type '{pattern.file_type}' not found "
                    f"for episode {guid} in {pattern.folder}/"
                )

            results[pattern.file_type] = file_path

        return results

    def _find_file_by_pattern(
        self,
        base_prefix: str,
        pattern: S3FilePattern
    ) -> Optional[str]:
        """Find a file matching the pattern in the specified folder"""

        folder_prefix = f"{base_prefix}{pattern.folder}/"

        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=folder_prefix
            )

            if 'Contents' not in response:
                return None

            # Find files matching pattern
            matches = []
            for obj in response['Contents']:
                key = obj['Key']
                filename = key.split('/')[-1]

                if re.match(pattern.pattern, filename):
                    matches.append(key)

            if not matches:
                return None

            # Prefer files with guid in name
            guid = base_prefix.split('/')[1]
            for match in matches:
                if guid in match:
                    return f"s3://{self.bucket}/{match}"

            # Otherwise return first match
            return f"s3://{self.bucket}/{matches[0]}"

        except ClientError as e:
            print(f"Error accessing S3: {e}")
            return None

# modules/s3_reader.py (UPDATED)
from modules.file_discovery import S3FileDiscovery

class S3Reader:
    def __init__(self, s3_client, bucket_name):
        self.s3 = s3_client
        self.bucket = bucket_name
        self.discovery = S3FileDiscovery(s3_client, bucket_name)

    def read_episode_data(self, feed_slug: str, guid: str) -> dict:
        """Read all data for an episode using dynamic discovery"""

        # Discover files dynamically
        file_paths = self.discovery.discover_episode_files(
            feed_slug,
            guid
        )

        print(f"Discovered files for {guid}:")
        for file_type, path in file_paths.items():
            print(f"  {file_type}: {path or 'NOT FOUND'}")

        # Read discovered files
        episode_data = {
            'guid': guid,
            'feed_slug': feed_slug,
            'files': file_paths
        }

        # Read transcript if found
        if file_paths.get('transcript'):
            transcript_data = self._read_json_from_s3(
                file_paths['transcript']
            )
            episode_data['transcript'] = transcript_data

        # Read other files...
        # (similar pattern for meta, kpis, entities)

        return episode_data
```

### Acceptance Criteria
- [ ] Zero hardcoded S3 paths in codebase
- [ ] ETL successfully processes all 1,171 episodes
- [ ] New podcast feeds work without code changes
- [ ] Clear error messages when files not found
- [ ] File discovery logs show what was found/missed
- [ ] Performance within 10% of hardcoded version
- [ ] Pattern matching handles all known variations

### Testing Approach
```python
# 1. Unit Tests
def test_file_discovery_patterns():
    """Test pattern matching for known file formats"""
    test_cases = [
        ("a16z-2025-01-15-AI-Boom_0e983347_raw_transcript.json", True),
        ("transcript.json", True),
        ("meta_0e983347-7815-4b62-87a6-84d988a772b7_details.json", True),
        ("kpis_0e983347-7815-4b62-87a6-84d988a772b7.json", True),
        ("0e983347-7815-4b62-87a6-84d988a772b7_clean.json", True),
    ]

    for filename, should_match in test_cases:
        # Test each pattern

# 2. Integration Tests
- Test with production S3 bucket (read-only)
- Verify all 1,171 episodes discovered
- Check edge cases (missing files, empty folders)
- Test with new mock podcast structure

# 3. Performance Tests
- Measure discovery time for 100 episodes
- Compare with hardcoded baseline
- Ensure <10% performance impact

# 4. Regression Tests
- Run full ETL pipeline
- Verify same output as before
- Check data completeness
```

---

## 📋 Implementation Timeline

### Week 1 (Immediate)
- **Day 1-2**: Fix authentication (Issue #1 Phase 1)
- **Day 3**: Fix GUID confusion (Issue #2 Option B)
- **Day 4**: Fix S3 paths (Issue #3)
- **Day 5**: Testing and verification

### Week 2 (Follow-up)
- **Day 1-3**: Implement proper auth system (Issue #1 Phase 2)
- **Day 4-5**: Consider database migration for GUID field

### Success Metrics
- [ ] Zero security vulnerabilities in scanner
- [ ] 100% of API calls authenticated
- [ ] Zero failed joins due to field names
- [ ] 100% file discovery success rate
- [ ] No increase in error rates
- [ ] Performance within 10% of baseline

---

## 🚀 Next Steps

1. **Get Approval**: Review plan with team
2. **Create Tickets**: Break down into JIRA/Asana tasks
3. **Assign Owners**: One dev per issue
4. **Set Up Monitoring**: Track progress daily
5. **Plan Testing**: Coordinate QA resources
6. **Schedule Deploy**: Plan for low-traffic window

---

**Remember**: These are all blocking issues for public launch. The authentication issue is especially critical as it exposes the entire backend to abuse.
