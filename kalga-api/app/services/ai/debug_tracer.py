"""
DebugTracer — Pipeline AI trace collector
==========================================
Objet optionnel passé à travers le pipeline AI pour collecter
les événements de debug sans impacter le code de production.

Usage:
    tracer = DebugTracer()
    result = await generate_response(..., tracer=tracer)
    trace = tracer.to_dict()  # injecté dans DebugBotResponse

Le tracer est None en production → aucun overhead.
"""

import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("kalga.debug_tracer")


class TraceEvent:
    """Un événement horodaté dans le pipeline."""

    def __init__(self, category: str, name: str, data: Dict[str, Any]):
        self.ts = time.time()
        self.category = category   # DETECTOR | LLM | MEMORY | FSM | BUSINESS | CHAT | TOOL | KB
        self.name = name
        self.data = data

    def to_dict(self) -> Dict:
        return {
            "ts": round(self.ts, 3),
            "category": self.category,
            "name": self.name,
            "data": self.data
        }


class DebugTracer:
    """
    Collecte les événements de debug à travers tout le pipeline AI.
    Conçu pour être passé en paramètre optionnel (tracer=None en prod).
    """

    def __init__(self):
        self._start = time.time()
        self._events: List[TraceEvent] = []
        self.llm_prompt: Optional[List[Dict]] = None      # Messages envoyés à DeepSeek
        self.llm_raw_response: Optional[str] = None       # Réponse JSON brute
        self.llm_parsed: Optional[Dict] = None            # JSON parsé
        self.llm_latency_ms: Optional[float] = None       # Latence appel HTTP
        self.llm_prompt_msg_count: Optional[int] = None   # Nb messages dans le prompt
        self.memory_stm: Optional[Dict] = None            # Snapshot STM
        self.memory_ltm: Optional[Dict] = None            # Snapshot LTM
        self.memory_episodic: Optional[Dict] = None       # Snapshot épisodique
        self.kb_results: Optional[List[str]] = None       # Résultats KB search
        self.detectors: Dict[str, Any] = {}               # Résultats des détecteurs
        self.mode: Optional[str] = None                   # Mode choisi: normal|correction|pending|fallback
        self.fallback_used: bool = False                   # Fallback déclenché
        self.fsm_transitions: List[Dict] = []             # Transitions FSM
        self.tool_calls: List[Dict] = []                  # Outils appelés par l'IA
        self.total_ms: Optional[float] = None             # Durée totale pipeline

    def event(self, category: str, name: str, **data) -> None:
        """Enregistre un événement de pipeline."""
        self._events.append(TraceEvent(category, name, data))

    def set_detector(self, name: str, result: Any) -> None:
        """Enregistre le résultat d'un détecteur."""
        self.detectors[name] = result
        self.event("DETECTOR", name, result=result)

    def set_mode(self, mode: str) -> None:
        """Définit le mode de traitement choisi."""
        self.mode = mode
        self.event("CHAT", "mode_selected", mode=mode)

    def set_llm_call(
        self,
        messages: List[Dict],
        raw_response: Optional[str],
        parsed: Optional[Dict],
        latency_ms: float
    ) -> None:
        """Capture les données de l'appel LLM."""
        self.llm_prompt = messages
        self.llm_raw_response = raw_response
        self.llm_parsed = parsed
        self.llm_latency_ms = round(latency_ms, 1)
        self.llm_prompt_msg_count = len(messages)
        self.event(
            "LLM", "deepseek_call",
            msg_count=len(messages),
            latency_ms=round(latency_ms, 1),
            success=parsed is not None,
            is_deal=parsed.get("is_deal") if parsed else None,
            price_mentioned=parsed.get("price_mentioned") if parsed else None,
            send_location=parsed.get("send_location") if parsed else None,
        )

    def set_kb_results(self, results: Optional[List[str]]) -> None:
        """Capture les résultats de la recherche KB."""
        self.kb_results = results
        self.event("KB", "search", found=len(results) if results else 0)

    def set_stm(self, msg_count: int, compressed: bool, window: int) -> None:
        """Capture l'état de la mémoire court-terme."""
        self.memory_stm = {
            "total_messages": msg_count,
            "compressed": compressed,
            "recent_window": window
        }
        self.event("MEMORY", "stm", **self.memory_stm)

    def set_ltm(self, facts: List[Dict], preferences: Optional[Dict]) -> None:
        """Capture les faits LTM extraits."""
        self.memory_ltm = {
            "fact_count": len(facts),
            "facts": facts[:5],
            "preferences": preferences
        }
        self.event("MEMORY", "ltm", fact_count=len(facts))

    def set_episodic(self, sessions: List[Dict], fact_count: int) -> None:
        """Capture le contexte épisodique injecté."""
        self.memory_episodic = {
            "session_count": len(sessions),
            "fact_count": fact_count,
            "sessions": sessions
        }
        self.event("MEMORY", "episodic", session_count=len(sessions), fact_count=fact_count)

    def add_fsm_transition(self, from_state: str, event_name: str, to_state: str) -> None:
        """Enregistre une transition FSM."""
        t = {"from": from_state, "event": event_name, "to": to_state}
        self.fsm_transitions.append(t)
        self.event("FSM", "transition", **t)

    def add_tool_call(self, tool_name: str, reason: str, args: Optional[Dict] = None) -> None:
        """Enregistre un appel d'outil agentic."""
        tc = {"tool": tool_name, "reason": reason, "args": args or {}}
        self.tool_calls.append(tc)
        self.event("TOOL", tool_name, **tc)

    def set_fallback(self, reason: str) -> None:
        """Marque l'utilisation du fallback."""
        self.fallback_used = True
        self.event("CHAT", "fallback_triggered", reason=reason)

    def finalize(self) -> None:
        """Calcule la durée totale."""
        self.total_ms = round((time.time() - self._start) * 1000, 1)
        self.event("CHAT", "pipeline_done", total_ms=self.total_ms)

    def to_dict(self) -> Dict:
        """Sérialise le trace complet pour la réponse API."""
        return {
            "total_ms": self.total_ms,
            "mode": self.mode,
            "fallback_used": self.fallback_used,
            "events": [e.to_dict() for e in self._events],
            "detectors": self.detectors,
            "llm": {
                "prompt_msg_count": self.llm_prompt_msg_count,
                "prompt": self.llm_prompt,
                "raw_response": self.llm_raw_response,
                "parsed": self.llm_parsed,
                "latency_ms": self.llm_latency_ms,
            },
            "memory": {
                "stm": self.memory_stm,
                "ltm": self.memory_ltm,
                "episodic": self.memory_episodic,
            },
            "kb_results": self.kb_results,
            "fsm_transitions": self.fsm_transitions,
            "tool_calls": self.tool_calls,
        }
