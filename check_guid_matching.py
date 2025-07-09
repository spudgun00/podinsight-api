#!/usr/bin/env python3
"""Create a custom endpoint to check GUID matching issues"""

# Add to api/intelligence.py temporarily
check_matching_code = '''
@router.get("/check-guid-matching")
async def check_guid_matching():
    """Debug endpoint to check which GUIDs match between collections"""
    try:
        db = get_mongodb()
        
        # Get all episode_intelligence documents
        intelligence_collection = db.get_collection("episode_intelligence")
        intelligence_docs = list(intelligence_collection.find({}, {"episode_id": 1}))
        
        # Get all episode_metadata documents  
        metadata_collection = db.get_collection("episode_metadata")
        
        results = {
            "total_intelligence_docs": len(intelligence_docs),
            "matching_guids": [],
            "non_matching_guids": []
        }
        
        for intel_doc in intelligence_docs:
            episode_id = intel_doc.get("episode_id")
            
            # Try to find in metadata using both guid and episode_id fields
            metadata_match = metadata_collection.find_one({
                "$or": [
                    {"guid": episode_id},
                    {"episode_id": episode_id}
                ]
            })
            
            if metadata_match:
                results["matching_guids"].append({
                    "episode_id": episode_id,
                    "metadata_id": str(metadata_match["_id"]),
                    "title": metadata_match.get("raw_entry_original_feed", {}).get("episode_title", "Unknown")
                })
            else:
                results["non_matching_guids"].append(episode_id)
        
        results["matching_count"] = len(results["matching_guids"])
        results["non_matching_count"] = len(results["non_matching_guids"])
        
        return results
        
    except Exception as e:
        return {"error": str(e)}
'''

print("Add this code to api/intelligence.py after the other debug endpoints:")
print(check_matching_code)
print("\nThen test with:")
print("curl -X GET 'https://podinsight-api.vercel.app/api/intelligence/check-guid-matching' | jq")