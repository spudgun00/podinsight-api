"""
Answer synthesis module for OpenAI integration
Generates 2-sentence summaries with citations from search results
"""
import os
import re
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
import openai
from openai import AsyncOpenAI
import time

logger = logging.getLogger(__name__)

# Add diagnostic logging for Vercel debugging
print("--- Loading synthesis.py module ---")
ANSWER_SYNTHESIS_ENABLED_VAL = os.getenv("ANSWER_SYNTHESIS_ENABLED", "true")
OPENAI_API_KEY_VAL = os.getenv("OPENAI_API_KEY")
print(f"VERCEL_ENV: Reading ANSWER_SYNTHESIS_ENABLED: '{ANSWER_SYNTHESIS_ENABLED_VAL}'")
print(f"VERCEL_ENV: Reading OPENAI_API_KEY: Present? {OPENAI_API_KEY_VAL is not None and len(OPENAI_API_KEY_VAL) > 0}")

# Feature flag for answer synthesis (can be disabled if needed)
ANSWER_SYNTHESIS_ENABLED = ANSWER_SYNTHESIS_ENABLED_VAL.lower() == "true"

# Initialize OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY_VAL)
print("--- Synthesis.py module loaded ---")

# Superscript mapping for citations
SUPERSCRIPT_MAP = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"
}

class Citation(BaseModel):
    """Citation metadata for answer synthesis"""
    index: int
    episode_id: str
    episode_title: str
    podcast_name: str
    timestamp: str  # Human-readable format like "27:04"
    start_seconds: float
    chunk_index: int
    chunk_text: str

class SynthesizedAnswer(BaseModel):
    """Result of answer synthesis"""
    text: str  # The synthesized answer with superscript citations
    citations: List[Citation]
    cited_indices: List[int]  # Which chunks were actually cited
    synthesis_time_ms: int

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

def deduplicate_chunks(chunks: List[Dict[str, Any]], max_per_episode: int = 2) -> List[Dict[str, Any]]:
    """
    Deduplicate chunks to ensure diversity (max N chunks per episode)
    Returns deduplicated list maintaining score order
    """
    episode_counts = {}
    deduplicated = []

    for chunk in chunks:
        episode_id = chunk.get("episode_id", "unknown")

        # Track how many chunks we've taken from this episode
        if episode_id not in episode_counts:
            episode_counts[episode_id] = 0

        # Only include if we haven't hit the limit for this episode
        if episode_counts[episode_id] < max_per_episode:
            deduplicated.append(chunk)
            episode_counts[episode_id] += 1

    return deduplicated

def format_chunks_for_prompt(chunks: List[Dict[str, Any]], query: str) -> str:
    """
    Format chunks for the OpenAI prompt with clear numbering
    """
    prompt_parts = [
        f"Query: \"{query}\"\n",
        f"Here are {len(chunks)} context sources from podcast discussions:\n"
    ]

    for i, chunk in enumerate(chunks, 1):
        podcast = chunk.get("podcast_title", "Unknown Podcast")
        episode = chunk.get("episode_title", "Unknown Episode")
        text = chunk.get("text", "").strip()

        # Truncate text if too long (keep prompt manageable)
        if len(text) > 200:
            text = text[:197] + "..."

        prompt_parts.append(
            f"[{i}] {podcast} - {episode}\n"
            f"Excerpt: \"{text}\"\n"
        )

    prompt_parts.append(
        "\nSynthesize a 2-sentence answer (max 60 words) that directly addresses the query. "
        "Be specific and actionable. Cite sources using [number] format, e.g., [1] or [3]. "
        "Only cite sources that directly support your statements."
    )

    return "\n".join(prompt_parts)

def parse_citations(text: str) -> Tuple[str, List[int]]:
    """
    Parse citation markers like [1], [2] from text and convert to superscripts
    Returns: (formatted_text, list_of_cited_indices)
    """
    cited_indices = []

    def replace_citation(match):
        number = match.group(1)
        cited_indices.append(int(number))
        # Convert each digit to superscript
        return "".join(SUPERSCRIPT_MAP.get(digit, digit) for digit in number)

    # Replace [number] with superscript
    formatted_text = re.sub(r'\[(\d+)\]', replace_citation, text)

    return formatted_text, cited_indices

async def synthesize_answer(
    chunks: List[Dict[str, Any]],
    query: str,
    model: str = "gpt-3.5-turbo-0125",
    temperature: float = 0.0,
    max_tokens: int = 80
) -> Optional[SynthesizedAnswer]:
    """
    Main synthesis function that calls OpenAI and formats the response
    """
    # Check feature flag
    if not ANSWER_SYNTHESIS_ENABLED:
        logger.info("Answer synthesis is disabled via feature flag")
        return None

    start_time = time.time()

    try:
        # First, deduplicate chunks
        deduplicated_chunks = deduplicate_chunks(chunks, max_per_episode=2)
        logger.info(f"Deduplicated from {len(chunks)} to {len(deduplicated_chunks)} chunks")

        if not deduplicated_chunks:
            logger.warning("No chunks available for synthesis")
            return None

        # Format chunks for the prompt
        user_prompt = format_chunks_for_prompt(deduplicated_chunks, query)

        # System prompt
        system_prompt = (
            "You are a podcast intelligence assistant. Given search results from various podcasts, "
            "provide a concise 2-sentence synthesis (max 60 words) that directly answers the question. "
            "Cite sources with [number] format. Be specific and use exact quotes when impactful. "
            "Focus on insights from VCs, founders, and industry experts."
        )

        logger.info(f"Calling OpenAI {model} for synthesis")

        # Call OpenAI
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            n=1
        )

        # Extract the answer
        raw_answer = response.choices[0].message.content.strip()
        logger.info(f"Raw answer from OpenAI: {raw_answer}")

        # Parse citations and format with superscripts
        formatted_answer, cited_indices = parse_citations(raw_answer)

        # Build citation objects for cited sources
        citations = []
        for idx in cited_indices:
            if 1 <= idx <= len(deduplicated_chunks):
                chunk = deduplicated_chunks[idx - 1]  # Convert to 0-based index
                citations.append(Citation(
                    index=idx,
                    episode_id=chunk.get("episode_id", "unknown"),
                    episode_title=chunk.get("episode_title", "Unknown Episode"),
                    podcast_name=chunk.get("podcast_title", "Unknown Podcast"),
                    timestamp=format_timestamp(chunk.get("start_time", 0)),
                    start_seconds=chunk.get("start_time", 0),
                    chunk_index=chunk.get("chunk_index", 0),
                    chunk_text=chunk.get("text", "")
                ))

        synthesis_time_ms = int((time.time() - start_time) * 1000)

        return SynthesizedAnswer(
            text=formatted_answer,
            citations=citations,
            cited_indices=cited_indices,
            synthesis_time_ms=synthesis_time_ms
        )

    except Exception as e:
        logger.error(f"Error during synthesis: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

async def synthesize_with_retry(
    chunks: List[Dict[str, Any]],
    query: str,
    max_retries: int = 2
) -> Optional[SynthesizedAnswer]:
    """
    Wrapper function with retry logic for resilience
    """
    for attempt in range(max_retries + 1):
        try:
            result = await synthesize_answer(chunks, query)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Synthesis attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

    return None
