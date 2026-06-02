"""
KALGA Conversation Engine — Sentiment Analysis
================================================
Analyse de sentiment et détection d'émotions.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List


class Emotion(Enum):
    """Émotions détectables dans les messages"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    INTERESTED = "interested"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    DOUBTFUL = "doubtful"
    IMPATIENT = "impatient"
    CONFUSED = "confused"


@dataclass
class SentimentAnalysis:
    """Résultat de l'analyse de sentiment"""
    emotion: Emotion
    confidence: float  # 0.0 à 1.0
    is_positive: bool
    is_negative: bool
    intensity: float  # 0.0 à 1.0 (faible à forte)

    # Indicateurs spécifiques
    has_insults: bool = False
    has_urgency: bool = False
    has_questions: bool = False

    # Mots-clés détectés
    detected_keywords: List[str] = field(default_factory=list)


class SentimentAnalyzer:
    """
    Analyseur de sentiment avancé pour le contexte commercial africain.
    Détecte les émotions, l'intensité et les signaux d'achat.
    """

    # Lexiques par catégorie
    POSITIVE_WORDS = {
        'ok', 'oui', 'bien', 'super', 'parfait', 'excellent', 'génial', 'genial',
        'merci', 'thanks', 'cool', 'nice', 'top', 'intéressé', 'interesse',
        'j\'aime', 'jaime', 'deal', 'marché', 'vendu', 'd\'accord', 'daccord',
        'ça marche', 'ca marche', 'je prends', 'je veux', 'envoi', 'envoie'
    }

    NEGATIVE_WORDS = {
        'non', 'pas', 'jamais', 'cher', 'trop', 'beaucoup', 'arnaque',
        'voleur', 'escroc', 'menteur', 'faux', 'nul', 'nulle', 'mauvais',
        'impossible', 'ridicule', 'abuse', 'abusé', 'exagère', 'exagéré'
    }

    FRUSTRATION_MARKERS = {
        'voleur', 'arnaqueur', 'arnaque', 'escroc', 'menteur', 'idiot',
        'imbécile', 'imbecile', 'con', 'fou', 'folle', 'dingue', 'malade',
        'merde', 'bordel', 'putain', 'n\'importe quoi', 'nimporte quoi',
        'tu rigoles', 'tu plaisantes', 'tu délires', 'tu abuses',
        'c\'est du vol', 'tu te moques', 'tu te fous de moi'
    }

    DOUBT_MARKERS = {
        'sûr', 'sur', 'certain', 'vrai', 'vraiment', 'original', 'authentique',
        'garanti', 'garantie', 'confiance', 'peur', 'méfiant', 'doute',
        'qualité', 'qualite', 'faux', 'copie', 'contrefaçon'
    }

    INTEREST_MARKERS = {
        'intéress', 'interesse', 'veux', 'veut', 'prend', 'achète', 'acheter',
        'combien', 'prix', 'dispo', 'disponible', 'livr', 'envoi', 'photo',
        'image', 'voir', 'couleur', 'taille', 'modèle', 'adresse', 'où'
    }

    URGENCY_MARKERS = {
        'vite', 'urgent', 'rapidement', 'maintenant', 'aujourd\'hui',
        'tout de suite', 'immédiatement', 'asap', 'pressé'
    }

    def analyze(self, message: str) -> SentimentAnalysis:
        """Analyse complète du sentiment d'un message"""
        msg_lower = message.lower()
        words = set(msg_lower.split())

        # Comptage des indicateurs
        positive_count = sum(1 for w in self.POSITIVE_WORDS if w in msg_lower)
        negative_count = sum(1 for w in self.NEGATIVE_WORDS if w in msg_lower)

        # Détection spécifique
        has_frustration = any(m in msg_lower for m in self.FRUSTRATION_MARKERS)
        has_doubt = any(m in msg_lower for m in self.DOUBT_MARKERS)
        has_interest = any(m in msg_lower for m in self.INTEREST_MARKERS)
        has_urgency = any(m in msg_lower for m in self.URGENCY_MARKERS)
        has_questions = '?' in message

        # Indicateurs de colère (MAJUSCULES, !!!, ???)
        uppercase_ratio = sum(1 for c in message if c.isupper()) / max(len(message), 1)
        exclamation_count = message.count('!')
        question_count = message.count('?')

        is_shouting = uppercase_ratio > 0.5 and len(message) > 10
        is_emphatic = exclamation_count >= 2 or question_count >= 3

        # Déterminer l'émotion principale
        emotion = self._determine_emotion(
            has_frustration, has_doubt, has_interest,
            positive_count, negative_count, is_shouting, is_emphatic
        )

        # Calculer l'intensité
        intensity = self._calculate_intensity(
            positive_count, negative_count, is_shouting, is_emphatic,
            has_frustration, exclamation_count
        )

        # Collecter les mots-clés détectés
        detected = []
        if has_frustration:
            detected.extend([m for m in self.FRUSTRATION_MARKERS if m in msg_lower])
        if has_doubt:
            detected.extend([m for m in self.DOUBT_MARKERS if m in msg_lower])
        if has_interest:
            detected.extend([m for m in self.INTEREST_MARKERS if m in msg_lower])

        return SentimentAnalysis(
            emotion=emotion,
            confidence=min(0.9, 0.5 + intensity * 0.4),
            is_positive=emotion in [Emotion.HAPPY, Emotion.INTERESTED],
            is_negative=emotion in [Emotion.ANGRY, Emotion.FRUSTRATED],
            intensity=intensity,
            has_insults=has_frustration,
            has_urgency=has_urgency,
            has_questions=has_questions,
            detected_keywords=detected[:5]  # Limiter à 5
        )

    def _determine_emotion(
        self, has_frustration: bool, has_doubt: bool, has_interest: bool,
        positive_count: int, negative_count: int,
        is_shouting: bool, is_emphatic: bool
    ) -> Emotion:
        """Détermine l'émotion principale"""

        # Priorité aux émotions fortes négatives
        if has_frustration and (is_shouting or is_emphatic):
            return Emotion.ANGRY
        if has_frustration:
            return Emotion.FRUSTRATED

        # Doute
        if has_doubt and negative_count > positive_count:
            return Emotion.DOUBTFUL

        # Impatience
        if is_emphatic and negative_count > 0:
            return Emotion.IMPATIENT

        # Émotions positives
        if has_interest:
            return Emotion.INTERESTED
        if positive_count > negative_count + 1:
            return Emotion.HAPPY

        # Confusion si beaucoup de questions
        if is_emphatic and has_doubt:
            return Emotion.CONFUSED

        return Emotion.NEUTRAL

    def _calculate_intensity(
        self, positive_count: int, negative_count: int,
        is_shouting: bool, is_emphatic: bool,
        has_frustration: bool, exclamation_count: int
    ) -> float:
        """Calcule l'intensité émotionnelle (0.0 à 1.0)"""
        intensity = 0.3  # Base

        if is_shouting:
            intensity += 0.3
        if is_emphatic:
            intensity += 0.2
        if has_frustration:
            intensity += 0.3

        intensity += min(0.1, exclamation_count * 0.03)
        intensity += min(0.1, (positive_count + negative_count) * 0.02)

        return min(1.0, intensity)
