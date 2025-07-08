# ETL Field Mapping Request - Episode Intelligence Integration

## Issue Summary
The Episode Intelligence API is unable to display real data because the `episode_id` fields don't match between MongoDB collections.

## Current State
- `episode_metadata` collection uses field: `guid` (e.g., "0e983347-7815-4b62-87a6-84d988a772b7")
- `episode_intelligence` collection uses field: `episode_id` (e.g., "02fc268c-61dc-4074-b7ec-882615bc6d85")
- These values don't match, causing the API to return mock data instead of real intelligence

## Requested Change
Add a new field `episode_id` to all documents in the `episode_metadata` collection that copies the value from the existing `guid` field.

### MongoDB Update Script

#### Step 1: Update Existing Documents
```javascript
// Run this in MongoDB to add episode_id field to existing documents
db.episode_metadata.updateMany(
  {},
  [
    {
      $set: {
        episode_id: "$guid"
      }
    }
  ]
);

// Verify the update
db.episode_metadata.findOne({}, { guid: 1, episode_id: 1 });
```

#### Step 2: Handle Future Documents
For new documents, the ETL pipeline needs to be updated to automatically set `episode_id = guid` when inserting.

**Option A: Update ETL Code**
```python
# In your ETL script when inserting new episodes
episode_doc = {
    "guid": episode_guid,
    "episode_id": episode_guid,  # Add this line
    # ... other fields
}
```

**Option B: MongoDB Schema Validation (Automatic)**
```javascript
// Add a pre-save middleware or trigger to automatically copy guid to episode_id
// This depends on your MongoDB setup (Atlas triggers, etc.)
db.runCommand({
  collMod: "episode_metadata",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["guid"],
      properties: {
        episode_id: {
          bsonType: "string",
          description: "Should match guid field"
        }
      }
    }
  }
});
```

**Option C: MongoDB Atlas Trigger (Recommended)**
Create a trigger in MongoDB Atlas that automatically sets `episode_id = guid` on insert/update:
```javascript
exports = function(changeEvent) {
  const collection = context.services.get("mongodb-atlas").db("podinsight").collection("episode_metadata");
  const docId = changeEvent.documentKey._id;

  if (changeEvent.operationType === "insert" || changeEvent.operationType === "update") {
    const doc = changeEvent.fullDocument;
    if (doc.guid && !doc.episode_id) {
      collection.updateOne(
        { _id: docId },
        { $set: { episode_id: doc.guid } }
      );
    }
  }
};
```

## Expected Result
After this update:
- Both collections will have matching `episode_id` fields
- The Episode Intelligence API will automatically start returning real data
- No code changes are required in the API

## Alternative Solution (If Above Not Possible)
If the `episode_id` values in `episode_intelligence` are actually different IDs (not GUIDs), please provide:
1. The mapping between `episode_metadata.guid` and `episode_intelligence.episode_id`
2. Or update `episode_intelligence.episode_id` to use the GUID values from `episode_metadata`

## Verification
After the update, test the API endpoint:
```bash
curl https://podinsight-api.vercel.app/api/intelligence/dashboard
```

The response should contain real episode data instead of mock data (check for `episode_id` NOT starting with "mock-").

## Priority
**HIGH** - This is blocking Story 5B (Episode Intelligence API) and Story 4 (Dashboard Integration)

## Contact
Please update this document with the status once complete or if there are any questions about the mapping.
