"""
Unit tests for the answer synthesis module
Tests OpenAI integration, citation parsing, and error handling
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from api.synthesis import (
    synthesize_answer,
    synthesize_with_retry,
    deduplicate_chunks,
    format_chunks_for_prompt,
    parse_citations,
    format_timestamp,
    SynthesizedAnswer,
    Citation
)

# Sample test data
def get_sample_chunks():
    """Generate sample chunks for testing"""
    return [
        {
            "episode_id": "ep1",
            "episode_title": "The AI Revolution",
            "podcast_title": "All-In Podcast",
            "text": "VCs are seeing crazy valuations for AI agents, sometimes 50-100x revenue multiples.",
            "start_time": 1500.0,
            "end_time": 1510.0,
            "score": 0.92,
            "chunk_index": 45
        },
        {
            "episode_id": "ep2",
            "episode_title": "Venture Capital Trends",
            "podcast_title": "Acquired",
            "text": "The market for AI agents is overheated. Valuations don't match the fundamentals.",
            "start_time": 820.0,
            "end_time": 830.0,
            "score": 0.89,
            "chunk_index": 23
        },
        {
            "episode_id": "ep1",  # Same episode as first chunk
            "episode_title": "The AI Revolution",
            "podcast_title": "All-In Podcast",
            "text": "We need to be careful about these inflated valuations in the AI space.",
            "start_time": 1520.0,
            "end_time": 1530.0,
            "score": 0.88,
            "chunk_index": 46
        },
        {
            "episode_id": "ep3",
            "episode_title": "Market Analysis",
            "podcast_title": "The Twenty Minute VC",
            "text": "AI agent companies are raising at unprecedented valuations despite unclear moats.",
            "start_time": 450.0,
            "end_time": 460.0,
            "score": 0.87,
            "chunk_index": 15
        }
    ]

class TestUtilityFunctions:
    """Test utility functions"""

    def test_format_timestamp(self):
        """Test timestamp formatting"""
        assert format_timestamp(0) == "0:00"
        assert format_timestamp(59) == "0:59"
        assert format_timestamp(60) == "1:00"
        assert format_timestamp(1624) == "27:04"
        assert format_timestamp(3661) == "61:01"

    def test_deduplicate_chunks(self):
        """Test chunk deduplication logic"""
        chunks = get_sample_chunks()

        # With max 2 per episode, should keep first 2 from ep1
        deduplicated = deduplicate_chunks(chunks, max_per_episode=2)
        assert len(deduplicated) == 4  # All chunks since only ep1 has duplicates

        # With max 1 per episode
        deduplicated = deduplicate_chunks(chunks, max_per_episode=1)
        assert len(deduplicated) == 3  # One from each unique episode
        assert all(d["episode_id"] in ["ep1", "ep2", "ep3"] for d in deduplicated)

    def test_parse_citations(self):
        """Test citation parsing and superscript conversion"""
        # Test single citations
        text, indices = parse_citations("This is a fact[1].")
        assert text == "This is a fact¹."
        assert indices == [1]

        # Test multiple citations
        text, indices = parse_citations("First fact[1] and second fact[2].")
        assert text == "First fact¹ and second fact²."
        assert indices == [1, 2]

        # Test adjacent citations
        text, indices = parse_citations("Combined facts[1][3].")
        assert text == "Combined facts¹³."
        assert indices == [1, 3]

        # Test no citations
        text, indices = parse_citations("No citations here.")
        assert text == "No citations here."
        assert indices == []

    def test_format_chunks_for_prompt(self):
        """Test chunk formatting for OpenAI prompt"""
        chunks = get_sample_chunks()[:2]
        query = "What are VCs saying about AI valuations?"

        prompt = format_chunks_for_prompt(chunks, query)

        # Check key components
        assert "Query: \"What are VCs saying about AI valuations?\"" in prompt
        assert "[1] All-In Podcast - The AI Revolution" in prompt
        assert "[2] Acquired - Venture Capital Trends" in prompt
        assert "50-100x revenue multiples" in prompt
        assert "2-sentence answer (max 60 words)" in prompt


class TestSynthesisFunction:
    """Test the main synthesis function"""

    @pytest.mark.asyncio
    async def test_successful_synthesis(self):
        """Test successful answer synthesis"""
        chunks = get_sample_chunks()
        query = "What are VCs saying about AI agent valuations?"

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "VCs express concern that AI agent valuations are outpacing fundamentals[1][2]. "
            "Recent rounds show 50-100x revenue multiples despite unclear moats[1][4]."
        )

        with patch('api.synthesis.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            result = await synthesize_answer(chunks, query)

            assert result is not None
            assert isinstance(result, SynthesizedAnswer)
            assert "VCs express concern" in result.text
            assert "¹²" in result.text  # Superscripts
            assert "¹⁴" in result.text
            assert len(result.citations) == 4
            assert result.cited_indices == [1, 2, 1, 4]

            # Check OpenAI was called correctly
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]["model"] == "gpt-3.5-turbo"
            assert call_args[1]["temperature"] == 0.0
            assert call_args[1]["max_tokens"] == 80

    @pytest.mark.asyncio
    async def test_synthesis_with_deduplication(self):
        """Test that deduplication works correctly"""
        chunks = get_sample_chunks()  # Has 2 chunks from ep1
        query = "AI valuations"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Answer with citations[1][2]."

        with patch('api.synthesis.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            result = await synthesize_answer(chunks, query)

            # Check that chunks were deduplicated
            # With max 2 per episode, all 4 chunks should be included
            assert result is not None
            # The prompt should include all 4 chunks
            call_args = mock_create.call_args
            user_content = call_args[1]["messages"][1]["content"]
            assert "[4]" in user_content  # Should have 4 chunks

    @pytest.mark.asyncio
    async def test_synthesis_error_handling(self):
        """Test error handling when OpenAI fails"""
        chunks = get_sample_chunks()
        query = "test query"

        with patch('api.synthesis.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("OpenAI API error")

            result = await synthesize_answer(chunks, query)

            assert result is None  # Should return None on error

    @pytest.mark.asyncio
    async def test_synthesis_with_retry(self):
        """Test retry logic"""
        chunks = get_sample_chunks()
        query = "test query"

        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success[1]."

        with patch('api.synthesis.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = [Exception("Temporary error"), mock_response]

            result = await synthesize_with_retry(chunks, query, max_retries=2)

            assert result is not None
            assert "Success¹" in result.text
            assert mock_create.call_count == 2  # Called twice due to retry


class TestCitationGeneration:
    """Test citation object generation"""

    @pytest.mark.asyncio
    async def test_citation_metadata(self):
        """Test that citations contain correct metadata"""
        chunks = get_sample_chunks()[:2]
        query = "test"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Answer citing both sources[1][2]."

        with patch('api.synthesis.client.chat.completions.create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            result = await synthesize_answer(chunks, query)

            assert len(result.citations) == 2

            # Check first citation
            cit1 = result.citations[0]
            assert cit1.index == 1
            assert cit1.episode_id == "ep1"
            assert cit1.episode_title == "The AI Revolution"
            assert cit1.podcast_name == "All-In Podcast"
            assert cit1.timestamp == "25:00"  # 1500 seconds
            assert cit1.start_seconds == 1500.0

            # Check second citation
            cit2 = result.citations[1]
            assert cit2.index == 2
            assert cit2.episode_id == "ep2"
            assert cit2.timestamp == "13:40"  # 820 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
