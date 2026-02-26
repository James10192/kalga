"""
KALGA Memory System
===================
Système de mémoire 3 couches pour le bot conversationnel.

- STM  : Short-Term Memory  — compression intra-session (rolling window)
- LTM  : Long-Term Memory   — profil sémantique client persisté en DB
- Episodic : récupération contextuelle inter-sessions (RAG léger)
"""
