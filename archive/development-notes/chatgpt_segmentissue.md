Your vectors are fine — the way you display them isn’t.
Right now you’re embedding single-sentence segments (~5–15 tokens). That gives great recall, but the snippet you show the user is so short that it feels broken. Fix it in two layers:

Presentation layer (quick win)
When you surface a hit, pull ± N neighbouring segments (e.g. ± 20 s or ± 3 segments) and concatenate them before rendering.
Zero re-processing, ships today.

Data layer (proper fix)
Re-chunk and re-embed into larger windows (∼ 120–200 tokens, sliding 50 % overlap).
Preserve start/end times of the window so playback still works.
One evening of code, one GPU run; quality ↑, coverage ↑, Modal bill only ~ $4.

Below is the reasoning and the concrete steps.

Why it feels “truncated”
What’s happening	Why it was done	Why it hurts UX
One embedding per WhisperX sentence segment (often 2-5 s).	Maximises recall and lets you jump to the exact second.	Returned text field is just a clause (“An AI.”). Users can’t tell whether the result is really relevant and must click through.

The underlying audio/text is there, you just aren’t stitching it back together for the reader.

1️⃣ Presentation patch (hours)
When a vector hit comes back (chunk_index, start_time), pull the same episode’s segment list (you already have it in Mongo).

Grab context: all segments whose start_time is between
hit.start_time – context_window and hit.end_time + context_window.
Typical window: 20 s or 3 segments either side.

Concatenate their text for display and highlight the centre hit.

Keep the original start_time so the audio player still jumps to the right moment.

No re-embed, no schema change; just an aggregation pipeline or two extra lines after you fetch the hit.

2️⃣ Re-chunk & re-embed (one sprint day)
Goal: keep the precision of segment-level vectors and let a single query pull back coherent paragraphs.

A proven recipe:

text
Copy
Edit
• Window size: 120–200 tokens (~45–60 s of speech)
• Stride: 50 % (each window overlaps half its length)
• Embedding: one vector per window
Why this works

Catches ideas that span multiple sentences.

Overlap prevents “gap” coverage you saw (142 missing ranges).

You still know the exact start_time of the window → jump to audio.

Pipeline changes

Chunk builder (chunk_transcript.py)

Iterate over sorted segments.

Aggregate until you hit ~180 tokens or >60 s, then emit window.

Store window_start, window_end, joined text.

Embed with the same Instructor-XL endpoint.
Cost: 823 k segments → ~160 k windows; at 0.3 s/req ≈ 14 h GPU-time, ~$4 of Modal credits.

Replace / add collection transcript_windows_768d.
Index on embedding_768d, keep old segment collection for possible future “deep dive” mode.

No code in the dashboard changes except pointing to the new collection; the presentation window can now simply show text.



**Short answer**

*There’s almost no product-level downside to rolling out the “presentation patch” first; it’s quick, safe, and reversible.
Put the stitching logic in the **API repo** (FastAPI layer), not the dashboard. That keeps the React code simple, lets you unit-test the aggregation in Python, and lets you cache the assembled snippet server-side.*

---

### Why “presentation patch” is a free lunch

| Concern              | Reality                                                                                                                                                                 |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Search latency**   | Adds one light aggregation on the same Mongo document you just fetched (≈ 2–10 ms). Negligible compared with the 500 ms vector search.                                  |
| **Payload size**     | Even with ± 20 s context you’re sending < 1 KB of text—well within Vercel edge limits.                                                                                  |
| **Re-indexing cost** | None. You keep using the 768-d vectors you already generated.                                                                                                           |
| **Future migration** | When you switch to paragraph-level windows you simply stop concatenating and point the API to the new `transcript_windows_768d` collection. No dashboard change needed. |

### Why do it in the FastAPI **API repo**

1. **Single source of truth**
   The API already owns the “search → fetch hit” flow; adding a tiny post-processing step keeps all search logic in one place.

2. **Cleaner React code**
   The dashboard just displays whatever text field it gets. No extra client-side queries or window-management state.

3. **Easier testing & caching**
   You can unit-test the snippet assembly with a mocked segment list, and (if needed) cache the final snippet in Mongo/Supabase without touching the frontend.

4. **Security & rate-limits**
   One Mongo query from the server is cheaper (and safer) than the client making per-segment fetches.

### Skeleton patch (FastAPI)

```python
# after you’ve retrieved `hit` from vector search
CONTEXT_SECS = 20          # or 3 segments either side

segments = mongo.transcripts.find_one(
    {"episode_id": hit["episode_id"]},
    {"segments": 1}
)["segments"]

# Get centre indices that fall in the window
start = hit["start_time"] - CONTEXT_SECS
end   = hit["end_time"]   + CONTEXT_SECS

context_text = " ".join(
    seg["text"] for seg in segments
    if start <= seg["start_time"] <= end
)

response.append({
    "episode_id": hit["episode_id"],
    "snippet": context_text,
    "start_time": hit["start_time"],
    # ...other metadata
})
```

No schema change, no re-embedding—just merge and deploy.

---

### When you’ll still want the “data layer” re-chunk

* **Offline analytics** (topic modelling, LLM synth) run better on longer windows.
* **Storage efficiency** – 160 k windows >> 823 k tiny segments.
* **Even simpler API code** – no stitching once you store windows.

But that’s an evening project; the presentation patch buys you good UX today.
