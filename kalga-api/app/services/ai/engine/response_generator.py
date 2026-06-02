"""
KALGA Conversation Engine — Response Generator
================================================
Générateur de réponses contextuelles et naturelles.
"""

import random
import logging
from typing import List, Dict

from .states import ConversationState, ConversationEvent
from .memory import ConversationMemory
from .sentiment import Emotion, SentimentAnalysis
from .intent import Intent
from .negotiation import NegotiationContext

logger = logging.getLogger("kalga.conversation_engine")


class ResponseGenerator:
    """
    Générateur de réponses contextuelles et naturelles.
    Adapte le ton et le contenu selon l'état, le sentiment et le contexte.
    """

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, List[str]]:
        """Charge les templates de réponses — variés, naturels, style WhatsApp ivoirien"""
        return {
            # === Salutations (premier message uniquement) ===
            "greeting_first": [
                "Salut! Oui c'est disponible à {price} F. Ça t'intéresse?",
                "Hey! Le {product} est là à {price} F. Tu veux?",
                "Coucou! Oui c'est dispo. {price} F. Ça te dit?",
                "Bonjour! Le {product} est disponible à {price} F. On peut discuter!",
                "Salut! C'est le {product} à {price} F. Tu veux plus d'infos?",
                "Oui c'est bien disponible! Prix: {price} F. Ça t'interesse?",
            ],

            # === Premier message avec intention de visite ===
            "first_message_visit": [
                "Merci pour ton intérêt! Tu sais où se trouve la boutique?",
                "Content que ça te plaise! Tu connais notre adresse?",
                "Super! Tu sais où on est situé?",
                "Cool! Tu connais déjà l'emplacement de la boutique?",
                "Avec plaisir! Tu as déjà l'adresse ou je t'envoie la localisation?",
            ],

            # === Prix présenté (pas de salutation) ===
            "price_presented": [
                "C'est {price} F. Tu veux qu'on discute?",
                "{price} F pour celui-là. Ça t'intéresse?",
                "Le prix c'est {price} F. On peut s'arranger!",
                "On est à {price} F. Tu as une offre à faire?",
                "Le {product} c'est {price} F. Qu'est-ce que t'en penses?",
            ],

            # === Acceptation de l'offre ===
            "offer_accepted": [
                "OK {client_price} F c'est bon! Livraison ou tu passes chercher?",
                "C'est deal à {client_price} F! Tu préfères livraison ou pickup?",
                "Parfait pour {client_price} F! Comment tu veux récupérer?",
                "On s'entend pour {client_price} F! Livraison ou tu viens?",
                "Banco à {client_price} F! On fait comment pour la livraison?",
                "C'est bon pour {client_price} F! Tu viens au magasin ou on t'envoie?",
            ],

            # === Contre-offre ===
            "counter_offer": [
                "Ah {client_price} F c'est un peu bas! On dit {counter} F?",
                "{client_price} F je peux pas... Allez {counter} F et on se comprend!",
                "Pour {client_price} F c'est chaud! {counter} F ça te va?",
                "Hm {client_price} F c'est juste. On peut faire {counter} F, c'est déjà un effort!",
                "{client_price} F c'est vraiment peu pour ce produit. {counter} F et on deal?",
                "Je comprends tu veux un bon prix. {counter} F c'est mon mieux là!",
                "Ah non {client_price} c'est trop bas. Je peux faire {counter} F, pas moins!",
            ],

            # === Dernier prix ===
            "final_offer": [
                "{price} F c'est vraiment mon DERNIER prix. À prendre ou à laisser!",
                "Je fais un gros effort: {price} F point final. C'est le minimum!",
                "Bon, {price} F et on arrête là. C'est mon prix plancher!",
                "Écoute, {price} F c'est tout ce que je peux faire. C'est sincère!",
                "Là c'est {price} F, je peux vraiment pas faire moins. Qu'est-ce que tu dis?",
            ],

            # === Fin de négociation (refus persistant) ===
            "negotiation_ended": [
                "J'ai fait mon maximum. Je peux vraiment pas descendre plus. Reviens quand tu veux!",
                "C'est vraiment mon dernier prix. Si ça te va pas, pas de souci!",
                "J'ai atteint ma limite là. N'hésite pas à revenir si tu changes d'avis!",
                "Désolé, je peux pas aller plus bas. Reviens quand tu veux, le produit reste dispo!",
            ],

            # === Client frustré — empathie ===
            "frustrated_empathy": [
                "Je comprends que ça puisse sembler cher, c'est de la vraie qualité!",
                "Écoute, je suis désolé si ça te semble élevé. C'est quoi ton budget?",
                "Je comprends ta réaction. Dis-moi ce qui te conviendrait?",
                "Hé je vois tu es frustré. Je veux qu'on trouve un accord. Ton budget c'est quoi?",
                "Calme, on va trouver quelque chose! Fais-moi une offre sérieuse.",
            ],

            # === Objection prix ===
            "objection_price": [
                "Je comprends! Dis-moi ton budget et on voit ce qu'on peut faire.",
                "C'est de la qualité, mais je peux faire un effort. Tu proposes combien?",
                "Je comprends que c'est un investissement. Fais-moi une offre!",
                "OK donne-moi un chiffre sérieux et on discute!",
                "Tout le monde veut un bon prix! C'est quoi ton budget max?",
            ],

            # === Objection qualité ===
            "objection_quality": [
                "C'est du {product} original, qualité garantie!",
                "Je te garantis la qualité. Si y'a un souci, tu reviens me voir!",
                "C'est du vrai, pas de la copie. Tu peux vérifier à la livraison!",
                "Garanti original! On fait même le retour si tu n'es pas satisfait.",
                "La qualité est top! C'est pas de la copie. Tu vas voir toi-même.",
            ],

            # === Objection confiance ===
            "objection_trust": [
                "Je comprends ta méfiance, c'est normal. Je suis un vendeur sérieux!",
                "Pas de souci, tu peux vérifier le produit avant de payer.",
                "On peut faire cash à la livraison si tu préfères!",
                "Ta confiance c'est important pour moi. Cash à la livraison, ça te va?",
                "Paiement à la livraison possible. Tu paies quand tu reçois le produit!",
            ],

            # === Objection timing ===
            "objection_timing": [
                "Pas de problème, prends ton temps! Je garde le produit.",
                "OK réfléchis bien. Je reste dispo quand tu veux!",
                "Aucun souci! Tu me recontactes quand tu es prêt.",
                "Prends le temps qu'il faut. Je suis là quand tu décides!",
                "Pas de rush! Reviens quand tu es sûr, le produit t'attend.",
            ],

            # === Choix livraison ===
            "ask_delivery_choice": [
                "Tu préfères la livraison ou tu passes au magasin?",
                "Livraison ou tu viens chercher?",
                "Comment tu veux faire? Livraison ou pickup?",
                "On te livre ou tu passes récupérer?",
                "Tu veux qu'on t'envoie ou tu viens directement?",
            ],

            # === Demande d'adresse ===
            "ask_address": [
                "Super! Envoie-moi ton adresse et numéro pour la livraison.",
                "OK pour la livraison! C'est où pour toi? Donne-moi l'adresse.",
                "Livraison c'est noté! Ton adresse et numéro stp?",
                "Parfait! Où est-ce qu'on te livre? Adresse + numéro.",
                "C'est bon! Envoie ton adresse complète et on règle ça.",
            ],

            # === Adresse reçue ===
            "address_received": [
                "Parfait! Je note. On te contacte pour organiser la livraison.",
                "C'est noté! Le vendeur te rappelle pour la livraison.",
                "Super! Tu seras contacté rapidement pour la livraison.",
                "Bien reçu! On te rappelle très vite pour confirmer.",
                "Noté! Le vendeur va te contacter pour fixer la livraison.",
            ],

            # === Localisation envoyée ===
            "location_sent": [
                "Je t'envoie la localisation!",
                "Voici l'adresse du magasin!",
                "Tiens, c'est ici!",
                "La position arrive!",
                "Je t'envoie le GPS!",
            ],

            # === Localisation demandée tôt dans la conversation ===
            "location_early": [
                "Je t'envoie la position! N'hésite pas si tu as des questions sur le {product}.",
                "Voici la localisation! Le {product} est à {display_price} F si ça t'intéresse.",
                "Tiens, voilà où on est! Passe quand tu veux.",
                "Je t'envoie l'adresse! Le {product} est dispo si tu veux.",
                "Position envoyée! Le {product} t'attend à {display_price} F.",
            ],

            # === Client mentionne un mauvais emplacement ===
            "wrong_location": [
                "Non, on n'est pas là-bas! On est à {merchant_address}. Je t'envoie la position exacte!",
                "Non pas du tout! La boutique est à {merchant_address}. Tiens, je t'envoie la localisation!",
                "Ah non! On est situé à {merchant_address}. Je t'envoie la position!",
                "Pas là! La boutique est à {merchant_address}. Position envoyée!",
                "Tu te trompes d'endroit! On est à {merchant_address}. Je t'envoie le GPS.",
            ],

            # === Attente pickup ===
            "pending_pickup": [
                "On t'attend au magasin!",
                "A tout a l'heure alors!",
                "Parfait, a bientot!",
                "OK on t'attend! A tout de suite.",
                "Super! Viens quand tu veux, on est là.",
                "On t'attend de pied ferme!",
            ],

            # === Questions d'horaires (jamais inventer) ===
            "hours_question": [
                "Pour les horaires, contacte directement le vendeur!",
                "Je ne connais pas les horaires exacts. Contacte le vendeur pour ça!",
                "Pour les heures d'ouverture, le vendeur te répondra directement.",
                "Les horaires varient! Mieux vaut contacter le vendeur pour être sûr.",
            ],

            # === Correction de statut (client nie avoir acheté) ===
            "status_correction": [
                "Pardon pour la confusion! On n'a pas encore finalisé. Tu es intéressé par le {product}?",
                "Toutes mes excuses! Je me suis trompé. On n'a rien conclu. Tu veux continuer?",
                "Excuse-moi pour la confusion! On n'a pas encore validé l'achat. Tu veux reprendre?",
                "Pardon! J'ai mal compris. Qu'est-ce que tu veux faire pour le {product}?",
            ],

            # === Questions générales ===
            "general_question": [
                "Tu veux savoir quoi exactement?",
                "Je t'écoute! Qu'est-ce que tu veux savoir?",
                "Dis-moi ce qui t'intéresse!",
                "Qu'est-ce que je peux faire pour toi?",
            ],

            # === Relance douce ===
            "soft_follow_up": [
                "Alors, ça t'intéresse?",
                "Tu veux qu'on procède?",
                "Des questions?",
                "Qu'est-ce que tu en penses?",
                "On avance?",
            ],

            # === Ambiguïté détectée (Phase 4) ===
            "ambiguity_clarify": [
                "Désolé, je n'ai pas bien compris. Tu parles du prix ou d'autre chose?",
                "Peux-tu préciser? Tu veux savoir quoi exactement?",
                "Je suis pas sûr de comprendre. Tu peux reformuler?",
                "Hmm dis-moi plus clairement ce que tu veux savoir!",
            ],
        }

    def generate(
        self,
        state: ConversationState,
        sentiment: SentimentAnalysis,
        negotiation: NegotiationContext,
        intent: Intent,
        memory: ConversationMemory,
        merchant_data: Dict = None
    ) -> str:
        """
        Génère une réponse appropriée basée sur tous les contextes.
        """
        # Variables de contexte
        merchant_address = ""
        if merchant_data and merchant_data.get('address'):
            merchant_address = merchant_data['address']

        # Prix à afficher : prix négocié si un accord est en cours, sinon prix catalogue
        display_price_value = negotiation.current_offer if negotiation.current_offer and negotiation.current_offer >= negotiation.min_price else negotiation.listed_price

        context = {
            "product": negotiation.product_name,
            "price": f"{negotiation.listed_price:,.0f}".replace(",", " "),
            "display_price": f"{display_price_value:,.0f}".replace(",", " "),
            "min_price": f"{negotiation.min_price:,.0f}".replace(",", " "),
            "client_price": f"{negotiation.current_offer:,.0f}".replace(",", " ") if negotiation.current_offer else "",
            "merchant_address": merchant_address,
        }

        # Sélectionner le template selon l'état
        template_key = self._select_template_key(state, sentiment, intent, negotiation, memory, merchant_data)

        # Traitement spécial pour les contre-offres
        if template_key == "counter_offer" and negotiation.current_offer:
            counter = negotiation.calculate_counter_offer(negotiation.current_offer)
            context["counter"] = f"{counter:,.0f}".replace(",", " ")
            negotiation.record_counter_offer(counter)

        # Sélectionner et formater le template
        templates = self.templates.get(template_key, self.templates["general_question"])
        template = random.choice(templates)

        try:
            response = template.format(**context)
        except KeyError:
            response = template

        return response

    def _select_template_key(
        self,
        state: ConversationState,
        sentiment: SentimentAnalysis,
        intent: Intent,
        negotiation: NegotiationContext,
        memory: ConversationMemory,
        merchant_data: Dict = None
    ) -> str:
        """Sélectionne la clé de template appropriée"""

        # Correction de statut — priorité absolue
        if intent.extracted_data.get("status_correction"):
            return "status_correction"

        # Mauvais emplacement mentionné par le client - priorité maximale
        if intent.extracted_data.get("wrong_location") and merchant_data and merchant_data.get('address'):
            return "wrong_location"

        # Demande de localisation — envoie la position SANS changer l'état de négociation
        # Demander où se trouve la boutique ≠ accepter d'acheter
        if intent.event == ConversationEvent.ASK_LOCATION:
            return "location_early"

        # Question d'horaires - priorité haute (jamais inventer)
        if intent.extracted_data.get("hours_question"):
            return "hours_question"

        # Client frustré - priorité haute
        if state == ConversationState.FRUSTRATED_CLIENT or sentiment.emotion in [Emotion.ANGRY, Emotion.FRUSTRATED]:
            return "frustrated_empathy"

        # Gestion des objections
        if state == ConversationState.OBJECTION_HANDLING:
            obj_type = intent.extracted_data.get("type", "price")
            return f"objection_{obj_type}"

        # États de négociation
        if state == ConversationState.GREETING:
            return "greeting_first"

        if state == ConversationState.PRICE_PRESENTED:
            # Si le client veut passer à la boutique → demander s'il connaît l'adresse
            if intent.extracted_data.get("visit_intent"):
                return "first_message_visit"
            # Si le client demande la localisation en early stage
            if intent.event == ConversationEvent.ASK_LOCATION:
                return "location_early"
            if memory.total_messages <= 1:
                return "greeting_first"
            return "price_presented"

        if state == ConversationState.DEAL_AGREED:
            if negotiation.current_offer:
                return "offer_accepted"
            return "ask_delivery_choice"

        if state == ConversationState.NEGOTIATING:
            if negotiation.current_offer and negotiation.current_offer >= negotiation.min_price:
                return "offer_accepted"
            return "counter_offer"

        if state == ConversationState.COUNTER_OFFER:
            return "counter_offer"

        if state == ConversationState.FINAL_OFFER:
            if negotiation.should_end_negotiation:
                return "negotiation_ended"
            return "final_offer"

        if state == ConversationState.ENDED:
            return "negotiation_ended"

        # États de livraison
        if state == ConversationState.CHOOSING_DELIVERY:
            return "ask_delivery_choice"

        if state == ConversationState.COLLECTING_ADDRESS:
            return "ask_address"

        if state == ConversationState.PENDING_DELIVERY:
            return "address_received"

        if state == ConversationState.PENDING_PICKUP:
            return "pending_pickup"

        if state == ConversationState.COOLING_OFF:
            return "objection_timing"

        return "soft_follow_up"
