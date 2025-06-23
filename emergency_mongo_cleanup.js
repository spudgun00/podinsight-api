// Emergency cleanup script for MongoDB
// Run this in MongoDB Compass or mongo shell to remove duplicated fields

// Connect to the database
use podinsight

// Check current damage
print("=== CHECKING CURRENT DAMAGE ===");
var totalChunks = db.transcript_chunks_768d.countDocuments({});
var chunksWithText = db.transcript_chunks_768d.countDocuments({"full_episode_text": {$exists: true}});

print("Total chunks: " + totalChunks);
print("Chunks with duplicated text: " + chunksWithText);
print("Percentage affected: " + (chunksWithText/totalChunks*100).toFixed(1) + "%");

// Sample to estimate storage waste
var sample = db.transcript_chunks_768d.findOne({"full_episode_text": {$exists: true}});
if (sample && sample.full_episode_text) {
    var textSize = sample.full_episode_text.length;
    var estimatedWaste = chunksWithText * textSize;
    print("\nEstimated storage waste:");
    print("Sample text size: " + textSize + " bytes");
    print("Total duplicated: " + (estimatedWaste/1024/1024).toFixed(1) + " MB");
    print("Storage waste: ~" + (estimatedWaste/1024/1024/1024).toFixed(1) + " GB");
}

print("\n=== CLEANUP OPERATION ===");
print("Removing duplicated fields to reclaim storage...");

// Execute the cleanup
var result = db.transcript_chunks_768d.updateMany(
    {},
    {
        $unset: {
            "full_episode_text": "",
            "episode_title_full": "",
            "text_word_count": "",
            "text_char_count": "",
            "text_imported_at": ""
        }
    }
);

print("Cleanup complete!");
print("Modified documents: " + result.modifiedCount);

// Verify cleanup
var remaining = db.transcript_chunks_768d.countDocuments({"full_episode_text": {$exists: true}});
if (remaining === 0) {
    print("✅ Verification: No duplicated fields remain");
} else {
    print("⚠️ Warning: " + remaining + " documents still have duplicated fields");
}

print("\n=== STORAGE SHOULD NOW BE RECOVERED ===");
print("MongoDB disk usage should return to normal levels.");
print("The original chunk data and search functionality are unaffected.");