"""
Contrat LLM du moteur de dialogue (spec §9).

Le LLM n'a que DEUX rôles, derrière cette interface :
- classify : message ambigu → intentions du CATALOGUE (JSON, jamais d'action) ;
- speak    : brief verrouillé → texte naturel (jamais de décision).

Toute implémentation peut échouer → retourne None, jamais d'exception :
le moteur continue (règles seules / gabarits). L'adaptateur DeepSeek réel
arrive au branchement (P4) ; FakeLLMClient sert tous les tests.
"""
from typing import Any, Dict, List, Optional, Protocol


class LLMClient(Protocol):
    async def classify(self, message: str, context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Intentions candidates [{type, amount?, text?}] ou None si indisponible."""
        ...

    async def speak(self, brief: Dict[str, Any]) -> Optional[str]:
        """Texte de réponse à partir du brief, ou None si indisponible."""
        ...


class FakeLLMClient:
    """Faux client déterministe pour les tests (enregistre les appels)."""

    def __init__(self, speak_result: Optional[str] = None,
                 speak_results: Optional[List[Optional[str]]] = None,
                 classify_result: Optional[List[Dict[str, Any]]] = None,
                 fail: bool = False):
        self._speak_results = list(speak_results) if speak_results is not None \
            else ([speak_result] if speak_result is not None else [])
        self._classify_result = classify_result
        self._fail = fail
        self.speak_briefs: List[Dict[str, Any]] = []
        self.classify_calls: List[str] = []

    async def speak(self, brief: Dict[str, Any]) -> Optional[str]:
        self.speak_briefs.append(brief)
        if self._fail:
            return None
        if self._speak_results:
            return self._speak_results.pop(0)
        return None

    async def classify(self, message: str, context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        self.classify_calls.append(message)
        return None if self._fail else self._classify_result
