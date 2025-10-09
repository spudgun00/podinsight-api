# PodInsight Podcast Inventory Report

**Last Updated**: January 25, 2025  
**Report Type**: Current Ingestion Status

## Summary

Based on the MongoDB database analysis and system documentation:

- **Total Episodes in Database**: 1,236 episodes (from `episode_metadata` collection)
- **Total Transcript Chunks**: 823,763 chunks (from `transcript_chunks_768d` collection)
- **Episode Transcripts Available**: 1,171 episodes with full transcripts
- **Database Name**: `podinsight`

## Date Range of Ingested Content

Based on the available data in the system:

- **Latest Data Import**: June 25, 2025 (MongoDB import timestamp)
- **Sample Episode Date**: June 9, 2025 (from a16z Podcast example)
- **Processing Dates**: June 23-25, 2025 (based on processing timestamps)

## Podcast Feed Information

The system processes podcasts from various sources. Here's what we know about the structure:

### Storage Structure
- **Raw Audio**: Stored in S3 bucket `pod-insights-raw`
- **Path Pattern**: `s3://pod-insights-raw/{podcast_slug}/{guid}/audio/`
- **Stage Data**: Stored in S3 bucket `pod-insights-stage`
- **Production Data**: Stored in S3 bucket `pod-insights-prod`

### Example Podcasts Found in System

Based on the codebase analysis, these podcast slugs have been identified:

1. **a16z-podcast** (a16z Podcast)
   - Feed URL: https://feeds.simplecast.com/JGE3yC0V
   - Example GUID: 0e983347-7815-4b62-87a6-84d988a772b7

2. **unchained** 
   - Example mentioned in testing documentation
   - Example GUID: 022f8502-14c3-11f0-9b7c-bf77561f0071

3. **the-pomp-podcast**
   - Mentioned in migration documentation

4. **this-week-in-startups**
   - RSS URL: https://feeds.simplecast.com/this-week-in-startups

5. **the-ai-daily-brief-formerly-the-ai-breakdown-artificial-intelligence-news-and-analysis**
   - Long-form podcast name with episode data

6. **all-in-with**
   - Mentioned in episode intelligence documentation

7. **flightcast**
   - Uses custom GUID format: `flightcast:qoefujdsy5huurb987mnjpw2`

## Podcast Count Estimates

According to the master architecture documentation:
- **Estimated Feed Count**: Varies between 29-31 podcast feeds
- **Unique Podcasts in MongoDB**: Data suggests 30+ distinct podcast feeds

## Episode Distribution

- **Average Episodes per Podcast**: ~40 episodes (1,236 total episodes ÷ ~30 podcasts)
- **Average Chunks per Episode**: ~700 chunks (823,763 chunks ÷ 1,171 episodes)

## Data Collection Method

The system uses:
1. RSS feed parsing to collect podcast metadata
2. Audio file downloads to S3 raw bucket
3. Transcription processing pipeline
4. Vector embedding generation for semantic search
5. MongoDB storage for search and retrieval

## Recommendations for Complete Inventory

To get a definitive list of all ingested podcasts:

1. Run the Python script at `scripts/list_all_podcasts.py` (requires environment setup)
2. Query MongoDB directly:
   ```javascript
   db.episode_metadata.distinct("raw_entry_original_feed.podcast_slug")
   ```
3. List S3 bucket directories:
   ```bash
   aws s3 ls s3://pod-insights-raw/ --recursive | cut -d'/' -f3 | sort -u
   ```

## Notes

- The system appears to focus on tech/startup/VC-related podcasts
- Episode dates and content freshness vary by podcast
- Not all podcasts may have complete metadata or transcripts
- The GUID format varies by podcast source (standard UUID vs custom formats)

---

**Note**: This report is based on available documentation and code analysis. For real-time accurate counts and complete podcast listings, direct database queries or the inventory script should be used.