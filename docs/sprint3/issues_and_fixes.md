# Sprint 3 Issues and Fixes

## Purpose
Document problems encountered during Sprint 3 implementation and their solutions.

---

## Issue Template
```
### Issue #[number]: [Brief Description]
**Date**: YYYY-MM-DD
**Phase**: [1A/1B/1C/2A/2B/2C/3A/3B/3C]
**Severity**: [Critical/High/Medium/Low]
**Status**: [Open/In Progress/Resolved]

**Description**:
Detailed description of the issue.

**Root Cause**:
Analysis of why the issue occurred.

**Solution**:
How the issue was resolved.

**Prevention**:
Steps to prevent similar issues in the future.
```

---

## Active Issues

### Issue #1: MongoDB Security Password Rotation
**Date**: 2024-12-28
**Phase**: Pre-Sprint
**Severity**: High
**Status**: Resolved

**Description**:
MongoDB password was exposed in previous commits and needed rotation.

**Root Cause**:
Credentials were accidentally committed to version control.

**Solution**:
Password was rotated on June 26, 2025, as documented in the MongoDB data model file.

**Prevention**:
- Use environment variables for all credentials
- Add .env files to .gitignore
- Regular security audits of commits

---

## Known Limitations

### Audio File Formats
- System currently assumes MP3 format for all podcasts
- Some podcasts may use M4A or other formats
- Need to implement format detection and conversion

### Edge Cases to Handle
1. Episodes shorter than 30 seconds
2. Chunks at the very start/end of episodes
3. Missing or corrupted audio files
4. Network interruptions during S3 operations

---

## Resolved Issues

*Issues will be moved here once resolved*

---

## Workarounds

### Temporary Solutions
Document any temporary workarounds implemented while permanent fixes are developed.

---

## Performance Issues

### Known Bottlenecks
- S3 download time for large audio files
- FFmpeg processing time varies by file size
- Cold start latency for Lambda functions
