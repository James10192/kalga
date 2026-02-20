"""
Réponses de secours (fallback)
Utilisées quand l'API DeepSeek échoue
"""
import random
from typing import Optional, Tuple, List, Dict

from .detectors import (
    extract_price_offer,
    detect_agreement,
    detect_location_request,
    detect_frustration,
    detect_objection
)


class FallbackResponses:
    """
    Générateur de réponses de secours intelligentes.
    Utilisé quand l'API DeepSeek n'est pas disponible.
    """

    @staticmethod
    def generate_response(
        client_message: str,
        product_name: str,
        price: float,
        min_price: float,
        current_offer: Optional[float],
        is_first_message: bool,
        low_offers_count: int,
        product_description: str = None
    ) -> Tuple[str, Optional[float], bool, str]:
        """
        Génère une réponse de secours intelligente.

        Returns:
            (response, new_offer, deal_accepted, new_status)
        """
        price_offer = extract_price_offer(client_message)
        final_price_mode = low_offers_count >= 2
        end_negotiation = low_offers_count >= 3 and price_offer and price_offer < min_price

        # Si le client fait une offre de prix
        if price_offer:
            return FallbackResponses._handle_price_offer(
                price_offer=price_offer,
                min_price=min_price,
                price=price,
                final_price_mode=final_price_mode,
                end_negotiation=end_negotiation
            )

        # Premier message
        if is_first_message:
            return FallbackResponses._first_message_response(product_name, price)

        # Message de suivi sans prix
        return FallbackResponses._handle_followup(
            client_message=client_message,
            product_name=product_name,
            current_offer=current_offer,
            product_description=product_description
        )

    @staticmethod
    def _handle_price_offer(
        price_offer: float,
        min_price: float,
        price: float,
        final_price_mode: bool,
        end_negotiation: bool
    ) -> Tuple[str, Optional[float], bool, str]:
        """Gère une offre de prix du client"""

        # Offre acceptable
        if price_offer >= min_price:
            responses = [
                f"OK {price_offer:,.0f} F c'est bon! Tu veux qu'on te livre?",
                f"Ça marche pour {price_offer:,.0f} F! On fait comment pour la livraison?",
                f"C'est bon {price_offer:,.0f} F! Tu veux la livraison?"
            ]
            return random.choice(responses), price_offer, True, "agreed"

        # Trop d'offres basses - arrêter poliment
        if end_negotiation:
            responses = [
                "Écoute, j'ai déjà fait mon maximum. Je peux vraiment pas descendre plus. Reviens quand tu veux!",
                "L'ami, c'est vraiment mon dernier prix. Si ça te va pas, pas de souci!",
                "Je comprends mais j'ai atteint ma limite. Reviens pour d'autres produits!"
            ]
            return random.choice(responses), price_offer, False, "ended"

        # Mode dernier prix - on propose le prix minimum comme dernier prix
        if final_price_mode:
            last_price = int(min_price)  # Le minimum est notre dernier prix
            responses = [
                f"Bon écoute, {last_price:,.0f} F c'est vraiment mon DERNIER prix. À ce prix je gagne presque rien!",
                f"Je fais un gros effort là: {last_price:,.0f} F dernier prix. C'est à prendre ou à laisser!",
                f"Allez, {last_price:,.0f} F point final. C'est le prix du patron!"
            ]
            return random.choice(responses), price_offer, False, "negotiating"

        # Offre proche du minimum (80%+)
        if price_offer >= min_price * 0.8:
            counter = int((price_offer + price) / 2)
            responses = [
                f"Ah {price_offer:,.0f} F c'est trop bas! Fais {counter:,.0f} F et on se comprend.",
                f"À {price_offer:,.0f} F je perds de l'argent! Dernier prix {counter:,.0f} F.",
                f"{price_offer:,.0f} F c'est chaud! Bon, {counter:,.0f} F et ça marche."
            ]
            return random.choice(responses), price_offer, False, "negotiating"

        # Offre trop basse
        responses = [
            f"Ah non {price_offer:,.0f} F c'est pas possible! Fais un effort, propose mieux.",
            f"{price_offer:,.0f} F c'est vraiment trop bas! C'est de la bonne qualité hein.",
            f"{price_offer:,.0f} F? Non vraiment! Propose quelque chose de sérieux."
        ]
        return random.choice(responses), price_offer, False, "negotiating"

    @staticmethod
    def _first_message_response(
        product_name: str,
        price: float
    ) -> Tuple[str, Optional[float], bool, str]:
        """Génère une réponse pour le premier message"""
        responses = [
            f"Salut! Oui c'est disponible. C'est {price:,.0f} F. Ça te dit?",
            f"Hey! Oui le {product_name} est là. C'est {price:,.0f} F. Tu veux?",
            f"Coucou! Oui c'est dispo. {price:,.0f} F. Ça t'intéresse?"
        ]
        return random.choice(responses), None, False, "active"

    @staticmethod
    def _handle_followup(
        client_message: str,
        product_name: str,
        current_offer: Optional[float],
        product_description: str = None
    ) -> Tuple[str, Optional[float], bool, str]:
        """Gère les messages de suivi sans prix (PAS de salutation ici!)"""
        msg_lower = client_message.lower()

        # Client frustré ou utilise des insultes - priorité haute
        if detect_frustration(client_message):
            responses = [
                "Je comprends que ça puisse sembler cher, mais c'est vraiment de la qualité!",
                "Écoute, je suis désolé si ça te semble élevé. On peut en discuter calmement.",
                "Je comprends ta réaction. Dis-moi ce qui te conviendrait?",
                "Pas de souci, je comprends. C'est quoi ton budget?"
            ]
            return random.choice(responses), current_offer, False, "negotiating"

        # Gestion des objections
        objection_type = detect_objection(client_message)
        if objection_type == "price":
            responses = [
                "Je comprends! Dis-moi ton budget et on voit ce qu'on peut faire.",
                "C'est de la bonne qualité, mais je peux faire un effort. Tu proposes combien?",
                "Je comprends que c'est un investissement. Fais-moi une offre!"
            ]
            return random.choice(responses), current_offer, False, "negotiating"

        if objection_type == "quality":
            responses = [
                f"C'est du {product_name} original, qualité garantie!",
                "Je te garantis la qualité. Si y'a un problème, tu reviens me voir!",
                "C'est du vrai, pas de la copie. Tu peux vérifier toi-même!"
            ]
            return random.choice(responses), None, False, "active"

        if objection_type == "trust":
            responses = [
                "Je comprends ta méfiance. Je suis un vendeur sérieux, regarde mes avis!",
                "Pas de souci, tu peux vérifier le produit avant de payer.",
                "On peut faire cash à la livraison si tu préfères!"
            ]
            return random.choice(responses), None, False, "active"

        if objection_type == "timing":
            responses = [
                "Pas de problème, prends ton temps! Je garde le produit pour toi.",
                "OK, réfléchis bien. Je reste dispo quand tu veux!",
                "Aucun souci! Tu me recontactes quand tu es prêt."
            ]
            return random.choice(responses), None, False, "active"

        # Client accepte
        if detect_agreement(client_message):
            return "OK c'est bon! Tu veux qu'on te livre?", current_offer, True, "agreed"

        # Questions sur la disponibilité
        if any(kw in msg_lower for kw in ['dispo', 'disponible', 'stock', 'reste', 'encore']):
            responses = [
                "Oui c'est toujours dispo! Tu le veux?",
                "Oui il est là! Tu veux qu'on procède?",
            ]
            return random.choice(responses), None, False, "active"

        # Questions sur la livraison
        if any(kw in msg_lower for kw in ['livr', 'envoi', 'envoie', 'expédi']):
            responses = [
                "Oui on peut te livrer! C'est où pour toi?",
                "Livraison possible! Tu es dans quel coin?",
            ]
            return random.choice(responses), None, False, "active"

        # Questions sur le magasin/localisation
        if detect_location_request(client_message):
            responses = [
                "Je t'envoie la localisation tout de suite!",
                "OK voilà l'adresse!",
                "Tiens, voici où nous trouver!",
            ]
            return random.choice(responses), current_offer, True, "pending_pickup"

        # Salutations du client (PAS de "Salut" en retour, on répond directement)
        if any(kw in msg_lower for kw in ['salut', 'bonjour', 'bonsoir', 'hello', 'hey', 'coucou', 'slt']):
            responses = [
                "Alors ça t'intéresse?",
                "Tu veux qu'on procède?",
                "Je t'écoute!",
            ]
            return random.choice(responses), None, False, "active"

        # Remerciements
        if any(kw in msg_lower for kw in ['merci', 'thanks', 'thank']):
            responses = [
                "De rien! Alors tu le prends?",
                f"Pas de quoi! Tu veux le {product_name}?",
            ]
            return random.choice(responses), None, False, "active"

        # Questions sur la marque
        if any(kw in msg_lower for kw in ['marque', 'brand', 'modèle', 'model']):
            responses = [
                f"C'est un {product_name} de bonne qualité!",
                f"C'est du {product_name}, original!",
            ]
            return random.choice(responses), None, False, "active"

        # Questions sur les détails / pourquoi le prix
        if any(kw in msg_lower for kw in ['détail', 'detail', 'caractéristique', 'info', 'plus', 'description', 'pourquoi']):
            if product_description:
                # Utiliser la vraie description du marchand
                responses = [
                    f"Voici les détails: {product_description}",
                    f"Pour le {product_name}: {product_description}",
                    f"{product_description}\nÇa t'intéresse?",
                ]
            else:
                responses = [
                    f"C'est un {product_name} en très bon état, qualité garantie!",
                    f"Le {product_name} est original et de qualité. Tu veux plus de détails?",
                    "Je te donne toutes les infos. Tu veux savoir quoi exactement?",
                ]
            return random.choice(responses), None, False, "active"

        # Questions sur l'état
        if any(kw in msg_lower for kw in ['neuf', 'nouveau', 'occasion', 'état', 'etat']):
            responses = [
                "C'est en excellent état! Tu veux qu'on procède?",
                "C'est nickel, qualité garantie!",
            ]
            return random.choice(responses), None, False, "active"

        # Questions sur la couleur/taille
        if any(kw in msg_lower for kw in ['couleur', 'taille', 'size', 'color']):
            responses = [
                "C'est celui sur la photo! Tu veux d'autres couleurs?",
                "Tu veux savoir quelles couleurs/tailles sont dispo?",
            ]
            return random.choice(responses), None, False, "active"

        # Questions générales / commentaires
        if any(kw in msg_lower for kw in ['pense', 'crois', 'trouve', 'avis']):
            responses = [
                "Je peux te donner plus de détails si tu veux!",
                "Qu'est-ce que tu veux savoir exactement?",
                "Dis-moi ce qui t'intéresse!",
            ]
            return random.choice(responses), None, False, "active"

        # Message par défaut (conversation naturelle, PAS de salutation)
        responses = [
            "Tu veux plus d'infos sur quoi?",
            f"Tu veux le {product_name}? On peut discuter!",
            "Dis-moi ce que tu veux savoir!",
            "Tu es intéressé? On peut négocier!"
        ]
        return random.choice(responses), None, False, "active"
