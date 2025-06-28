# ADR-001: On-Demand Audio Clip Generation

## Status
Accepted

## Context
Pre-generating 823K clips would create 60-80% duplicates due to overlapping time windows.

## Decision
Generate audio clips on-demand via Lambda when users click play.

## Consequences
- Saves $10K/year in storage
- 2-3s latency on first play (acceptable)
- Scales with actual usage
- No duplicate files

Full analysis: See AUDIO_CLIP_ARCHITECTURE_ANALYSIS.md
