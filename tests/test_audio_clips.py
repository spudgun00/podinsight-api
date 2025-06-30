"""
Tests for audio clip generation API endpoint.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from bson import ObjectId
import json
import httpx

# Import the audio clips router
from api.audio_clips import router, AudioClipResponse

# Create test client
from fastapi import FastAPI
app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Test data
VALID_EPISODE_ID = "507f1f77bcf86cd799439011"
INVALID_EPISODE_ID = "invalid-id"
TEST_GUID = "0e983347-7815-4b62-87a6-84d988a772b7"
TEST_FEED_SLUG = "a16z-podcast"
TEST_START_TIME_MS = 30000
TEST_DURATION_MS = 30000

@pytest.fixture
def mock_mongodb():
    """Mock MongoDB client and collections"""
    with patch('api.audio_clips.get_mongodb_client') as mock_get_client:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.podinsight = mock_db

        # Mock episode_metadata collection
        mock_episode_metadata = MagicMock()
        mock_db.episode_metadata = mock_episode_metadata

        # Mock transcript_chunks_768d collection
        mock_chunks = MagicMock()
        mock_db.transcript_chunks_768d = mock_chunks

        mock_get_client.return_value = mock_client

        yield {
            'client': mock_client,
            'db': mock_db,
            'episode_metadata': mock_episode_metadata,
            'chunks': mock_chunks
        }

@pytest.fixture
def mock_lambda_url():
    """Mock Lambda URL environment variable"""
    with patch.dict('os.environ', {'AUDIO_LAMBDA_URL': 'https://test-lambda.amazonaws.com'}):
        yield

class TestAudioClipEndpoint:
    """Test cases for audio clip generation endpoint"""

    def test_invalid_episode_id_format(self):
        """Test with invalid episode ID format"""
        response = client.get(
            f"/api/v1/audio_clips/{INVALID_EPISODE_ID}?start_time_ms=30000"
        )
        assert response.status_code == 400
        assert "Invalid episode ID format" in response.json()["detail"]

    def test_missing_start_time(self):
        """Test with missing start_time_ms parameter"""
        response = client.get(f"/api/v1/audio_clips/{VALID_EPISODE_ID}")
        assert response.status_code == 422  # FastAPI validation error

    def test_negative_start_time(self):
        """Test with negative start time"""
        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms=-1000"
        )
        assert response.status_code == 400
        assert "Start time must be non-negative" in response.json()["detail"]

    def test_invalid_duration(self):
        """Test with invalid duration"""
        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms=30000&duration_ms=70000"
        )
        assert response.status_code == 400
        assert "Duration must be between" in response.json()["detail"]

    @patch('api.audio_clips.httpx.AsyncClient')
    def test_episode_not_found(self, mock_httpx, mock_mongodb, mock_lambda_url):
        """Test when episode is not found in MongoDB"""
        # Mock episode not found
        mock_mongodb['episode_metadata'].find_one.return_value = None

        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms={TEST_START_TIME_MS}"
        )
        assert response.status_code == 404
        assert "Episode not found" in response.json()["detail"]

    @patch('api.audio_clips.httpx.AsyncClient')
    def test_missing_guid(self, mock_httpx, mock_mongodb, mock_lambda_url):
        """Test when episode has no GUID"""
        # Mock episode without GUID
        mock_mongodb['episode_metadata'].find_one.return_value = {
            "_id": ObjectId(VALID_EPISODE_ID),
            "episode_title": "Test Episode"
        }

        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms={TEST_START_TIME_MS}"
        )
        assert response.status_code == 500
        assert "Episode missing GUID" in response.json()["detail"]

    @patch('api.audio_clips.httpx.AsyncClient')
    def test_missing_feed_slug(self, mock_httpx, mock_mongodb, mock_lambda_url):
        """Test when feed_slug cannot be determined"""
        # Mock episode with GUID
        mock_mongodb['episode_metadata'].find_one.return_value = {
            "_id": ObjectId(VALID_EPISODE_ID),
            "guid": TEST_GUID,
            "episode_title": "Test Episode"
        }

        # Mock chunk not found
        mock_mongodb['chunks'].find_one.return_value = None

        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms={TEST_START_TIME_MS}"
        )
        assert response.status_code == 500
        assert "Could not determine podcast feed" in response.json()["detail"]

    def test_lambda_url_not_configured(self, mock_mongodb):
        """Test when Lambda URL is not configured"""
        # Mock episode and chunk data
        mock_mongodb['episode_metadata'].find_one.return_value = {
            "_id": ObjectId(VALID_EPISODE_ID),
            "guid": TEST_GUID,
            "episode_title": "Test Episode"
        }
        mock_mongodb['chunks'].find_one.return_value = {
            "feed_slug": TEST_FEED_SLUG
        }

        # Remove Lambda URL from environment
        with patch.dict('os.environ', {'AUDIO_LAMBDA_URL': ''}, clear=True):
            response = client.get(
                f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms={TEST_START_TIME_MS}"
            )
            assert response.status_code == 503
            assert "Audio service not configured" in response.json()["detail"]

    @patch('api.audio_clips.httpx.AsyncClient')
    async def test_successful_clip_generation(self, mock_httpx_class, mock_mongodb, mock_lambda_url):
        """Test successful audio clip generation"""
        # Mock MongoDB data
        mock_mongodb['episode_metadata'].find_one.return_value = {
            "_id": ObjectId(VALID_EPISODE_ID),
            "guid": TEST_GUID,
            "episode_title": "Test Episode",
            "podcast_title": "Test Podcast"
        }
        mock_mongodb['chunks'].find_one.return_value = {
            "feed_slug": TEST_FEED_SLUG
        }

        # Mock Lambda response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "clip_url": "https://test-bucket.s3.amazonaws.com/test-clip.mp3",
            "cache_hit": False
        }

        # Mock httpx client
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx_class.return_value.__aenter__.return_value = mock_client

        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms={TEST_START_TIME_MS}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["clip_url"] == "https://test-bucket.s3.amazonaws.com/test-clip.mp3"
        assert data["cache_hit"] is False
        assert "generation_time_ms" in data
        assert data["episode_info"]["episode_id"] == VALID_EPISODE_ID
        assert data["episode_info"]["guid"] == TEST_GUID
        assert data["episode_info"]["feed_slug"] == TEST_FEED_SLUG

    @patch('api.audio_clips.httpx.AsyncClient')
    async def test_lambda_timeout(self, mock_httpx_class, mock_mongodb, mock_lambda_url):
        """Test Lambda timeout handling"""
        # Mock MongoDB data
        mock_mongodb['episode_metadata'].find_one.return_value = {
            "_id": ObjectId(VALID_EPISODE_ID),
            "guid": TEST_GUID,
            "episode_title": "Test Episode"
        }
        mock_mongodb['chunks'].find_one.return_value = {
            "feed_slug": TEST_FEED_SLUG
        }

        # Mock timeout
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_httpx_class.return_value.__aenter__.return_value = mock_client

        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms={TEST_START_TIME_MS}"
        )

        assert response.status_code == 504
        assert "Audio generation timed out" in response.json()["detail"]

    def test_health_check(self, mock_lambda_url):
        """Test health check endpoint"""
        response = client.get("/api/v1/audio_clips/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "audio_clips"
        assert data["lambda_configured"] is True
        assert "mongodb_configured" in data

class TestCacheHitScenario:
    """Test cases for cache hit scenarios"""

    @patch('api.audio_clips.httpx.AsyncClient')
    async def test_cache_hit(self, mock_httpx_class, mock_mongodb, mock_lambda_url):
        """Test when clip is already cached"""
        # Mock MongoDB data
        mock_mongodb['episode_metadata'].find_one.return_value = {
            "_id": ObjectId(VALID_EPISODE_ID),
            "guid": TEST_GUID,
            "episode_title": "Test Episode"
        }
        mock_mongodb['chunks'].find_one.return_value = {
            "feed_slug": TEST_FEED_SLUG
        }

        # Mock Lambda response with cache hit
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "clip_url": "https://test-bucket.s3.amazonaws.com/cached-clip.mp3",
            "cache_hit": True
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx_class.return_value.__aenter__.return_value = mock_client

        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms={TEST_START_TIME_MS}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cache_hit"] is True
        assert "clip_url" in data

class TestEdgeCases:
    """Test edge cases and error scenarios"""

    @patch('api.audio_clips.httpx.AsyncClient')
    async def test_lambda_error_response(self, mock_httpx_class, mock_mongodb, mock_lambda_url):
        """Test Lambda error response handling"""
        # Mock MongoDB data
        mock_mongodb['episode_metadata'].find_one.return_value = {
            "_id": ObjectId(VALID_EPISODE_ID),
            "guid": TEST_GUID
        }
        mock_mongodb['chunks'].find_one.return_value = {
            "feed_slug": TEST_FEED_SLUG
        }

        # Mock Lambda error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Lambda error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx_class.return_value.__aenter__.return_value = mock_client

        response = client.get(
            f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms={TEST_START_TIME_MS}"
        )

        assert response.status_code == 500
        assert "Audio generation failed" in response.json()["detail"]

    def test_custom_duration(self, mock_mongodb, mock_lambda_url):
        """Test with custom duration parameter"""
        # Mock MongoDB data
        mock_mongodb['episode_metadata'].find_one.return_value = {
            "_id": ObjectId(VALID_EPISODE_ID),
            "guid": TEST_GUID
        }
        mock_mongodb['chunks'].find_one.return_value = {
            "feed_slug": TEST_FEED_SLUG
        }

        with patch('api.audio_clips.httpx.AsyncClient') as mock_httpx_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "clip_url": "https://test-bucket.s3.amazonaws.com/clip.mp3",
                "cache_hit": False
            }

            mock_client = AsyncMock()
            mock_httpx_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            # Test with 15 second duration
            response = client.get(
                f"/api/v1/audio_clips/{VALID_EPISODE_ID}?start_time_ms=30000&duration_ms=15000"
            )

            assert response.status_code == 200

            # Verify Lambda was called with correct duration
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            payload = call_args[1]['json']
            assert payload['duration_ms'] == 15000
