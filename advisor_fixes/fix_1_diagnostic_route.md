# Fix 1: Separate Diagnostic Lambda ✅

**Problem:** The diagnostic route was inside `topic_velocity.py` but Vercel only imports the file that matches the URL path.

**Solution:** Created `api/__diag.py` as a separate lambda file.

**File created:** `/api/__diag.py`

**What it does:**
- Connects to MongoDB and gets collection count
- Confirms environment variables are set
- Will be accessible at `https://podinsight-api.vercel.app/api/__diag`

**Status:** Ready to deploy