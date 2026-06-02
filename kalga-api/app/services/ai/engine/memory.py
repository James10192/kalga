"""
KALGA Conversation Engine — Memory
====================================
Système de mémoire multi-niveaux inspiré de Mem0 et MemGPT.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger("kalga.conversation_engine")


@dataclass
class ConversationMemory:
    """
    Système de mémoire multi-niveaux inspiré de Mem0 et MemGPT.

    - short_term: Messages récents (buffer limité)
    - facts: Faits extraits de la conversation
    - summary: Résumé compressé de l'historique
    """
    # Mémoire court terme (derniers messages)
    short_term: List[Dict[str, Any]] = field(default_factory=list)
    max_short_term: int = 10

    # Faits extraits
    facts: Dict[str, Any] = field(default_factory=dict)

    # Résumé de conversation
    summary: str = ""

    # Métriques
    total_messages: int = 0
    client_messages: int = 0
    bot_messages: int = 0

    def add_message(self, content: str, is_from_client: bool, metadata: Dict = None):
        """Ajoute un message à la mémoire"""
        message = {
            "content": content,
            "is_from_client": is_from_client,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.short_term.append(message)
        self.total_messages += 1

        if is_from_client:
            self.client_messages += 1
        else:
            self.bot_messages += 1

        # Gestion de la limite (garder les N derniers)
        if len(self.short_term) > self.max_short_term:
            # Comprimer les anciens messages dans le résumé
            old_messages = self.short_term[:len(self.short_term) - self.max_short_term]
            self._compress_to_summary(old_messages)
            self.short_term = self.short_term[-self.max_short_term:]

    def _compress_to_summary(self, messages: List[Dict]):
        """Compresse les anciens messages en résumé"""
        if not messages:
            return

        # Simple compression: extraire les points clés
        key_points = []
        for msg in messages:
            if msg["is_from_client"]:
                # Extraire les offres de prix
                price_match = re.search(r'(\d+)\s*k', msg["content"].lower())
                if price_match:
                    key_points.append(f"Client a proposé {price_match.group(1)}K")

        if key_points:
            if self.summary:
                self.summary += " | " + " | ".join(key_points)
            else:
                self.summary = " | ".join(key_points)

    def set_fact(self, key: str, value: Any):
        """Enregistre un fait"""
        self.facts[key] = value
        logger.debug(f"Memory: Fact set [{key}] = {value}")

    def get_fact(self, key: str, default: Any = None) -> Any:
        """Récupère un fait"""
        return self.facts.get(key, default)

    def get_context_window(self) -> List[Dict]:
        """Retourne le contexte actuel pour l'IA"""
        return self.short_term.copy()

    def get_formatted_history(self) -> str:
        """Retourne l'historique formaté pour le prompt"""
        lines = []

        if self.summary:
            lines.append(f"[Résumé précédent: {self.summary}]")
            lines.append("")

        for msg in self.short_term:
            role = "Client" if msg["is_from_client"] else "Vendeur"
            lines.append(f"{role}: {msg['content']}")

        return "\n".join(lines)
