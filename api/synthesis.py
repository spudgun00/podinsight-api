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

# --- LAZY INITIALIZATION FOR OPENAI CLIENT ---
# Global variable for the client, initialized to None
_openai_client = None

def get_openai_client():
    """
    Lazily initializes and returns a singleton AsyncOpenAI client.
    This prevents blocking operations during function cold start.
    """
    global _openai_client

    # Only initialize if it hasn't been for this function instance
    if _openai_client is None:
        logger.info("Client not initialized. Creating new AsyncOpenAI client.")
        api_key = os.getenv("OPENAI_API_KEY")

        # Fail fast with a clear error if the key is missing
        if not api_key:
            logger.error("CRITICAL: OPENAI_API_KEY environment variable not set or empty.")
            raise ValueError("OPENAI_API_KEY is not configured.")

        # Add timeout and reduce retries for Vercel compatibility
        _openai_client = AsyncOpenAI(
            api_key=api_key,
            timeout=10.0,  # 10 second timeout (well below Vercel's 30s)
            max_retries=1  # Reduce from default 2 to 1
        )
        logger.info("AsyncOpenAI client created successfully with 10s timeout.")

    return _openai_client

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
    confidence: Optional[float] = None
    show_confidence: bool = False

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

def analyze_chunks_for_specifics(chunks: List[Dict[str, Any]], query: str) -> bool:
    """Determine if chunks contain specific actionable data"""
    specific_indicators = [
        r'\$[\d,]+[MBK]?\s*(ARR|revenue|valuation)',  # Dollar amounts
        r'\d+[xX]\s*(return|multiple|growth)',         # Multiples
        r'Series [A-E]',                               # Funding rounds
        r'\d+%\s*(growth|increase|stake)',             # Percentages
        r'(acquired|raised|closed|launched)',           # Action verbs
    ]

    combined_text = " ".join([c.get("text", "") for c in chunks])

    # Check if any specific pattern matches
    for pattern in specific_indicators:
        if re.search(pattern, combined_text, re.IGNORECASE):
            return True

    # Check if specific companies are named (not generic)
    company_pattern = r'[A-Z][a-zA-Z]+\.ai|[A-Z][a-zA-Z]+\s+(AI|Labs|Tech|Bio)'
    if re.search(company_pattern, combined_text):
        return True

    return False

def extract_key_terms(query: str) -> List[str]:
    """Extract key terms from query for related content search"""
    # Remove common words
    stop_words = {'what', 'are', 'is', 'the', 'about', 'how', 'saying', 'doing', 'with', 'for'}
    words = query.lower().split()
    return [w for w in words if w not in stop_words and len(w) > 2]

def calculate_relatedness_score(chunk: Dict[str, Any], query_terms: List[str]) -> float:
    """Calculate how related a chunk is to query terms"""
    chunk_text = chunk.get("text", "").lower()
    score = 0.0

    for term in query_terms:
        if term in chunk_text:
            score += 0.3
        # Check for related terms
        if term == "valuation" and any(x in chunk_text for x in ["arr", "revenue", "funding"]):
            score += 0.2
        if term == "ai" and any(x in chunk_text for x in ["artificial intelligence", "machine learning", "llm"]):
            score += 0.2

    return min(score, 1.0)

def extract_entities(query: str) -> List[str]:
    """Extract potential entity names from query"""
    # Look for capitalized words that might be company/VC names
    potential_entities = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', query)

    # Filter out common non-entity words
    non_entities = {'What', 'When', 'Where', 'Why', 'How', 'The', 'Is', 'Are', 'Was', 'Were', 'Has', 'Have'}
    entities = [e for e in potential_entities if e not in non_entities]

    return entities

def find_related_insights(query: str, all_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find actually valuable related content"""
    # Extract entities and key terms from query
    query_entities = extract_entities(query)
    query_terms = extract_key_terms(query)

    # Score chunks based on entity overlap AND value indicators
    scored_chunks = []
    for chunk in all_chunks:
        chunk_text = chunk.get("text", "")

        # Check for specific value indicators
        has_metrics = bool(re.search(r'\$\d+[BMK]|\d+%|\d+x', chunk_text))
        has_entities = any(entity.lower() in chunk_text.lower() for entity in query_entities)
        has_action = bool(re.search(r'(raised|closed|launched|acquired|valued|grew)', chunk_text))

        # Only include if it has real value
        if has_metrics or (has_entities and has_action):
            relevance_score = calculate_relatedness_score(chunk, query_terms)
            if relevance_score > 0.3:
                scored_chunks.append((relevance_score, chunk))

    # Return top valuable chunks only (with higher threshold)
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in scored_chunks[:3] if score > 0.4]

def analyze_available_topics(chunks: List[Dict[str, Any]]) -> List[str]:
    """Analyze what topics are available in the chunks"""
    topics = set()
    combined_text = " ".join([c.get("text", "") for c in chunks[:100]]).lower()

    # Check for common topics
    topic_patterns = {
        "ARR": r"arr|annual recurring revenue",
        "funding": r"funding|raised|series [a-e]|investment",
        "AI": r"artificial intelligence|\bai\b|machine learning|llm",
        "founder": r"founder|ceo|entrepreneur",
        "growth": r"growth|scaling|expansion",
        "product": r"product|feature|launch",
        "market": r"market|industry|sector"
    }

    for topic, pattern in topic_patterns.items():
        if re.search(pattern, combined_text, re.IGNORECASE):
            topics.add(topic)

    return list(topics)

def generate_better_queries(original_query: str, available_chunks: List[Dict[str, Any]]) -> str:
    """Generate queries based on what's actually in your data"""
    # Analyze what topics/entities you have data for
    available_entities = set()
    available_metrics = set()

    for chunk in available_chunks[:100]:  # Sample recent chunks
        text = chunk.get("text", "")

        # Extract company names
        companies = re.findall(r'[A-Z][a-zA-Z]+(?:\.ai|Labs|Capital|Ventures|AI)', text)
        available_entities.update(companies)

        # Extract metric types
        if "$" in text and "ARR" in text:
            available_metrics.add("ARR")
        if re.search(r'Series [A-E]', text):
            available_metrics.add("funding")
        if "acquired" in text:
            available_metrics.add("acquisitions")
        if "IPO" in text:
            available_metrics.add("IPO")

    # Generate suggestions based on what exists
    suggestions = []

    # If query is about valuation/metrics
    if any(term in original_query.lower() for term in ["valuation", "metrics", "numbers"]):
        if "ARR" in available_metrics:
            suggestions.append("companies with ARR metrics")
        if "funding" in available_metrics:
            suggestions.append("recent Series A rounds")

    # If query mentions AI/tech
    if any(term in original_query.lower() for term in ["ai", "tech", "startup"]):
        if available_entities:
            # Pick a real entity they might search for
            sample_company = list(available_entities)[:2]
            if sample_company:
                suggestions.append(f"{sample_company[0]} latest updates")

    # Add time-based suggestions if we have recent content
    if "IPO" in available_metrics:
        suggestions.append("recent IPO discussions")
    if "acquisitions" in available_metrics:
        suggestions.append("recent acquisitions")

    # Fallback suggestions
    if not suggestions:
        suggestions = ["recent funding rounds", "founder insights this week"]

    return " or ".join([f"'{s}'" for s in suggestions[:2]])

def is_recent(chunk: Dict[str, Any], days: int = 30) -> bool:
    """Check if chunk is from recent content"""
    # This would need actual date checking implementation
    # For now, return True as placeholder
    # TODO: Implement actual date checking using chunk['published_at']
    _ = (chunk, days)  # Suppress unused warnings until implemented
    return True

def calculate_smart_confidence(has_specific_data: bool, chunks: List[Dict[str, Any]]) -> Optional[float]:
    """Only show high confidence when we have real value"""
    if not has_specific_data:
        return None  # Don't show confidence for no results

    # Base confidence on quality of results
    quality_score = 0.7  # Base

    # Boost for multiple sources
    if len(chunks) >= 3:
        quality_score += 0.15

    # Boost for recent content
    if any(is_recent(chunk) for chunk in chunks):
        quality_score += 0.1

    return min(quality_score, 0.95)  # Cap at 95%

def remove_gpt_fluff(text: str) -> str:
    """Remove GPT's apologetic/verbose patterns"""
    fluff_patterns = [
        r"I apologize, but.*?\.",
        r"Unfortunately,.*?\.",
        r"It appears that.*?\.",
        r"Based on the provided sources,",
        r"The sources indicate that",
        r"In summary,.*?(\.|:)",
        r"Here are the actionable findings.*?:",
    ]

    for pattern in fluff_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()

def format_no_results_prompt(query: str, num_sources: int, related_insights: List[Dict[str, Any]]) -> str:
    """Format prompt when no direct results found"""
    prompt_parts = [
        f"Query: \"{query}\"\n",
        f"Direct search returned no specific results from {num_sources} sources.\n",
        "However, here are related insights that might be valuable:\n"
    ]

    for i, chunk in enumerate(related_insights, 1):
        podcast = chunk.get("podcast_title", "Unknown Podcast")
        episode = chunk.get("episode_title", "Unknown Episode")
        text = chunk.get("text", "").strip()[:200]

        prompt_parts.append(
            f"[{i}] {podcast} - {episode}\n"
            f"Related content: \"{text}\"\n"
        )

    return "\n".join(prompt_parts)

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
        "\nProvide specific, actionable intelligence that directly addresses the query. "
        "Prioritize company names, metrics, and concrete details. "
        "Cite sources using [number] format. Never generalize when specifics are available."
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
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    max_tokens: int = 250
) -> Optional[SynthesizedAnswer]:
    """
    Main synthesis function that calls OpenAI and formats the response
    """
    # Check feature flag at runtime
    if os.getenv("ANSWER_SYNTHESIS_ENABLED", "true").lower() != "true":
        logger.info("Answer synthesis is disabled via feature flag")
        return None

    start_time = time.time()
    logger.info("[SYNTHESIS v1] Running original synthesize_answer function")

    try:
        # Get the OpenAI client using lazy initialization
        client = get_openai_client()
        # First, deduplicate chunks
        deduplicated_chunks = deduplicate_chunks(chunks, max_per_episode=2)
        logger.info(f"Deduplicated from {len(chunks)} to {len(deduplicated_chunks)} chunks")

        if not deduplicated_chunks:
            logger.warning("No chunks available for synthesis")
            return None

        # Format chunks for the prompt
        user_prompt = format_chunks_for_prompt(deduplicated_chunks, query)

        # Analyze if we have specific actionable data
        has_specific_data = analyze_chunks_for_specifics(deduplicated_chunks, query)

        # System prompt
        system_prompt = (
            "You are a VC intelligence system. Your responses must be scannable in 2 seconds.\n\n"

            "OUTPUT RULES:\n"
            "1. If specific data exists: List it immediately with bullets\n"
            "2. If no specific data: State it in ONE line, then pivot to related insights\n"
            "3. Never explain why data is missing\n"
            "4. Never use more than 50 words for 'no results' scenarios\n"
            "5. Always suggest better searches based on available data\n\n"

            "FORMAT FOR POSITIVE RESULTS:\n"
            "• Company/Person - Specific metric/fact [Source, timestamp]\n"
            "• Use bullets for multiple findings\n"
            "• Include playable timestamps\n\n"

            "FORMAT FOR NO DIRECT RESULTS:\n"
            "○ No [specific thing] found in [N] sources\n\n"
            "💡 Related insights:\n"
            "• [Most relevant tangential finding] [Source]\n"
            "• [Second best related insight] [Source]\n\n"
            "🔍 Try: '[suggestion1]' or '[suggestion2]'"
        )

        logger.info(f"Calling OpenAI {model} for synthesis")
        openai_start = time.time()

        # Call OpenAI with tighter token limit for conciseness
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=150,  # Tighter limit for more concise responses
            n=1
        )

        openai_end = time.time()
        logger.info(f"OpenAI API call completed in {openai_end - openai_start:.2f} seconds")

        # Extract the answer
        raw_answer = response.choices[0].message.content.strip()
        logger.info(f"Raw answer from OpenAI: {raw_answer}")

        # Remove GPT fluff
        cleaned_answer = remove_gpt_fluff(raw_answer)

        # Parse citations and format with superscripts
        formatted_answer, cited_indices = parse_citations(cleaned_answer)

        # Calculate confidence based on actual value
        confidence = calculate_smart_confidence(has_specific_data, deduplicated_chunks)

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

        # Check if this is a "no results" response
        is_no_results = any(pattern in formatted_answer.lower() for pattern in [
            "no specific", "○ no", "no results found", "didn't find",
            "no insights found", "no data available"
        ])
        logger.info(f"[SYNTHESIS DEBUG] Is no results: {is_no_results}, Original confidence: {confidence}")

        if is_no_results:
            logger.info("[SYNTHESIS v1] No results detected, returning None for frontend")
            return None  # This will cause answer: null in API response

        # Only show confidence for positive results with high confidence
        confidence_str = ""
        show_confidence = False
        if confidence and confidence > 0.8:
            confidence_str = f" ({int(confidence * 100)}% confidence)"
            show_confidence = True

        logger.info(f"[SYNTHESIS DEBUG] Final show_confidence: {show_confidence}")

        return SynthesizedAnswer(
            text=formatted_answer + confidence_str,
            citations=citations,
            cited_indices=cited_indices,
            synthesis_time_ms=synthesis_time_ms,
            confidence=confidence,
            show_confidence=show_confidence
        )

    except Exception as e:
        logger.error(f"Error during synthesis: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

async def synthesize_answer_v2(
    chunks: List[Dict[str, Any]],
    query: str,
    all_chunks: List[Dict[str, Any]] = None,  # For finding related content
    model: str = "gpt-4o-mini",
    temperature: float = 0.0
) -> Optional[SynthesizedAnswer]:
    """Enhanced synthesis with fallback to related insights"""

    start_time = time.time()
    logger.info("[SYNTHESIS v2 - UPDATED] Running enhanced synthesis with confidence fixes")

    try:
        client = get_openai_client()

        # Deduplicate primary chunks
        deduplicated_chunks = deduplicate_chunks(chunks, max_per_episode=2)
        logger.info(f"Deduplicated from {len(chunks)} to {len(deduplicated_chunks)} chunks")

        # Analyze if we have specific actionable data
        has_specific_data = analyze_chunks_for_specifics(deduplicated_chunks, query)

        if has_specific_data:
            # Standard synthesis for good results
            user_prompt = format_chunks_for_prompt(deduplicated_chunks, query)
        else:
            # Enhanced prompt for no direct results
            if all_chunks:
                related_insights = find_related_insights(query, all_chunks)
                user_prompt = format_no_results_prompt(query, len(chunks), related_insights)
            else:
                user_prompt = format_chunks_for_prompt(deduplicated_chunks, query)

        # Add query suggestions based on what we DO have
        suggestions = generate_better_queries(query, all_chunks or deduplicated_chunks)
        user_prompt += f"\n\nSuggested searches: {suggestions}"

        # System prompt
        system_prompt = (
            "You are a VC intelligence system. Your responses must be scannable in 2 seconds.\n\n"

            "OUTPUT RULES:\n"
            "1. If specific data exists: List it immediately with bullets\n"
            "2. If no specific data: State it in ONE line, then pivot to related insights\n"
            "3. Never explain why data is missing\n"
            "4. Never use more than 50 words for 'no results' scenarios\n"
            "5. Always suggest better searches based on available data\n\n"

            "FORMAT FOR POSITIVE RESULTS:\n"
            "• Company/Person - Specific metric/fact [Source, timestamp]\n"
            "• Use bullets for multiple findings\n"
            "• Include playable timestamps\n\n"

            "FORMAT FOR NO DIRECT RESULTS:\n"
            "○ No [specific thing] found in [N] sources\n\n"
            "💡 Related insights:\n"
            "• [Most relevant tangential finding] [Source]\n"
            "• [Second best related insight] [Source]\n\n"
            "🔍 Try: '[suggestion1]' or '[suggestion2]'"
        )

        # Call OpenAI with strict token limit
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=150  # Keep it tight
        )

        raw_answer = response.choices[0].message.content.strip()

        # Clean up the answer
        cleaned_answer = remove_gpt_fluff(raw_answer)

        # Parse citations and format with superscripts
        formatted_answer, cited_indices = parse_citations(cleaned_answer)

        # Calculate confidence based on actual value
        confidence = calculate_smart_confidence(has_specific_data, deduplicated_chunks)

        # Build citation objects
        citations = []
        for idx in cited_indices:
            if 1 <= idx <= len(deduplicated_chunks):
                chunk = deduplicated_chunks[idx - 1]
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

        # Check if this is a "no results" response
        is_no_results = any(pattern in formatted_answer.lower() for pattern in [
            "no specific", "○ no", "no results found", "didn't find",
            "no insights found", "no data available"
        ])
        logger.info(f"[SYNTHESIS DEBUG] Is no results: {is_no_results}, Original confidence: {confidence}")

        if is_no_results:
            logger.info("[SYNTHESIS v1] No results detected, returning None for frontend")
            return None  # This will cause answer: null in API response

        # Only show confidence for positive results with high confidence
        confidence_str = ""
        show_confidence = False
        if confidence and confidence > 0.8:
            confidence_str = f" ({int(confidence * 100)}% confidence)"
            show_confidence = True

        logger.info(f"[SYNTHESIS DEBUG] Final show_confidence: {show_confidence}")

        return SynthesizedAnswer(
            text=formatted_answer + confidence_str,
            citations=citations,
            cited_indices=cited_indices,
            synthesis_time_ms=synthesis_time_ms,
            confidence=confidence,
            show_confidence=show_confidence
        )

    except Exception as e:
        logger.error(f"Error during enhanced synthesis: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

async def synthesize_with_retry(
    chunks: List[Dict[str, Any]],
    query: str,
    max_retries: int = 0  # Reduced from 2 to avoid timeout issues
) -> Optional[SynthesizedAnswer]:
    """
    Wrapper function with retry logic for resilience
    Updated to use the enhanced v2 synthesis
    """
    logger.info(f"[SYNTHESIS WITH RETRY] Called with query: '{query}', chunks: {len(chunks)}")

    for attempt in range(max_retries + 1):
        try:
            # Try v2 first for better results
            logger.info("[SYNTHESIS WITH RETRY] Attempting v2 synthesis")
            result = await synthesize_answer_v2(chunks, query)
            if result:
                logger.info(f"[SYNTHESIS WITH RETRY] v2 succeeded, confidence: {result.confidence}, show: {result.show_confidence}")
                return result
            # Fallback to original if v2 fails
            logger.info("[SYNTHESIS WITH RETRY] v2 failed, falling back to v1")
            result = await synthesize_answer(chunks, query)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Synthesis attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

    return None
