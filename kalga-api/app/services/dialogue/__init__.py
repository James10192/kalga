"""
Moteur de dialogue v2 — pipeline à 5 étages (spec 2026-06-11).

Phase 1 : étages ① (sanitizer) et ② (intents, understanding).
Le code décide QUOI faire ; le LLM décidera COMMENT le dire (phases suivantes).
"""
