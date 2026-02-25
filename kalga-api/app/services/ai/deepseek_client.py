"""
Client DeepSeek API
Gère les appels à l'API DeepSeek avec retry et gestion d'erreurs
"""
import httpx
import logging
from typing import Optional, Dict, Any
from ...config import settings

logger = logging.getLogger("kalga.deepseek")


class DeepSeekClient:
    """
    Client pour l'API DeepSeek.
    Gère les appels avec retry et timeout.
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        timeout: float = 30.0,
        max_retries: int = 2
    ):
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.timeout = timeout
        self.max_retries = max_retries

        if not self.api_key:
            logger.warning("Clé API DeepSeek non configurée!")

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 200
    ) -> Optional[str]:
        """
        Envoie une requête de chat completion à DeepSeek.

        Args:
            system_prompt: Instructions système
            user_message: Message de l'utilisateur
            temperature: Créativité (0-1)
            max_tokens: Longueur max de la réponse

        Returns:
            La réponse générée ou None en cas d'erreur
        """
        if not self.api_key:
            logger.error("Clé API DeepSeek manquante!")
            return None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message}
                            ],
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data['choices'][0]['message']['content']
                        logger.debug(f"Réponse DeepSeek: {content[:50]}...")
                        return content
                    else:
                        logger.warning(f"Erreur DeepSeek [{response.status_code}]: {response.text[:100]}")
                        if attempt < self.max_retries:
                            continue
                        return None

            except httpx.TimeoutException:
                logger.warning(f"Timeout DeepSeek (tentative {attempt + 1}/{self.max_retries + 1})")
                if attempt < self.max_retries:
                    continue
                return None

            except Exception as e:
                logger.error(f"Exception DeepSeek: {type(e).__name__}: {e}")
                if attempt < self.max_retries:
                    continue
                return None

        return None

    def build_negotiation_prompt(
        self,
        product_name: str,
        price: float,
        min_price: float,
        history_text: str,
        low_offers_count: int,
        final_price_mode: bool,
        conversation_status: str,
        is_first_message: bool = False,
        product_description: str = None,
        context_summary: str = None
    ) -> str:
        """
        Construit le prompt système pour la négociation.

        Args:
            product_name: Nom du produit
            price: Prix affiché
            min_price: Prix minimum (secret)
            history_text: Historique de conversation formaté
            low_offers_count: Nombre d'offres trop basses
            final_price_mode: Si on est en mode dernier prix
            conversation_status: Statut actuel de la conversation
            is_first_message: Si c'est le premier message du client

        Returns:
            Le prompt système complet
        """
        # Déterminer si on doit saluer
        greeting_instruction = ""
        if is_first_message:
            greeting_instruction = """
PREMIER MESSAGE:
C'est le tout premier message du client. Commence par "Salut!" et donne le prix.
Exemple: "Salut! Oui c'est disponible à {price} F. Ça t'intéresse?"
""".format(price=f"{price:,.0f}")
        else:
            greeting_instruction = """
RÈGLE CRITIQUE - PAS DE "SALUT":
Ce n'est PAS le premier message! NE DIS JAMAIS "Salut", "Hello", "Hey" ou autre salutation!
Tu es DÉJÀ en conversation avec le client. Réponds directement à sa question/remarque.
"""

        # Description du produit
        description_block = ""
        if product_description:
            description_block = f"- Description: {product_description}\n"

        prompt = f"""Tu es un vendeur WhatsApp naturel et sympa. Tu es EN PLEINE CONVERSATION avec un client.

PRODUIT:
- Nom: {product_name}
{description_block}- Prix affiché: {price:,.0f} F
- Prix minimum: {min_price:,.0f} F (SECRET - ne jamais révéler!)

RÈGLE DESCRIPTION:
Si le client demande des détails, infos ou la description du produit, utilise la description ci-dessus pour répondre.
Si pas de description, décris le produit de façon générale en mettant en avant la qualité.
{greeting_instruction}
RÈGLE #1 - COHÉRENCE DES PRIX:
- Le prix affiché est {price:,.0f} F - c'est TON prix de départ
- Tu peux négocier VERS LE BAS, jamais vers le haut
- Ne propose JAMAIS un prix supérieur à {price:,.0f} F
- Si tu fais une contre-offre, elle doit être entre {min_price:,.0f} F et {price:,.0f} F

RÈGLE #2 - CONVERSATION NATURELLE:
- Réponds comme si tu discutais avec un ami sur WhatsApp
- Enchaîne naturellement sur ce que le client dit
- Si le client pose une question → réponds à SA question
- Si le client fait un commentaire → rebondis dessus

RÈGLE #3 - NE PAS RÉPÉTER LE PRIX:
Regarde l'historique! Si tu as DÉJÀ dit le prix, NE LE RÉPÈTE PAS sauf si:
- Le client demande explicitement le prix ("c'est combien?", "le prix?")
- Le client fait une nouvelle offre

RÈGLE #4 - GESTION DES CLIENTS FRUSTRÉS:
Si le client semble énervé, frustré ou utilise des mots durs:
- Reste calme et poli, NE T'ÉNERVE PAS
- Montre de l'empathie: "Je comprends que ça puisse sembler cher..."
- Explique la valeur: "C'est de la qualité, ça vaut son prix"
- Propose une solution: "Qu'est-ce qui te conviendrait?"

RÈGLE #5 - GESTION DES OBJECTIONS:
- "C'est trop cher" → Explique la valeur, propose un compromis
- "J'ai vu moins cher ailleurs" → "Oui mais ici c'est garanti qualité!"
- "Je ne suis pas sûr" → Rassure sur la qualité et le service
- "Je réfléchis" → "Pas de souci, prends ton temps. Je reste dispo!"

NÉGOCIATION:
- Client propose ≥ {min_price:,.0f} F → ACCEPTER! "OK c'est bon! Tu veux la livraison ou tu passes récupérer?"
- Client propose < {min_price:,.0f} F → Négocier poliment, proposer un prix entre son offre et {price:,.0f} F
- Client dit "ok/deal/je prends" → "Parfait! Tu préfères livraison ou tu passes chercher?"

RÈGLE ABSOLUE - PAS DE TEXTE FICTIF:
- N'invente JAMAIS d'adresse, d'horaires, de localisation ou d'informations que tu ne connais pas!
- NE METS JAMAIS de placeholders comme "[Insérer l'adresse ici]", "[horaires]", "[adresse]", etc.
- Si le client demande l'adresse/localisation → dis "Je t'envoie la localisation!" (le système GPS l'envoie automatiquement)
- Si le client demande des horaires → dis "Le vendeur te donnera les horaires!"
- Si le client veut passer au magasin → dis "OK tu passes chercher! Je t'envoie la localisation du magasin."

ÉTAT ACTUEL:
- Offres basses reçues: {low_offers_count}
"""

        if final_price_mode:
            # En mode dernier prix, on propose un petit rabais sur le min_price pour conclure
            final_offer = int(min_price)  # Le prix minimum est déjà le plus bas possible
            prompt += f"- MODE DERNIER PRIX ACTIVÉ: Propose {final_offer:,} F comme DERNIER prix. C'est le minimum absolu!\n"

        if conversation_status in ["pending_delivery", "pending_pickup"]:
            prompt += "- VENTE CONFIRMÉE! Aide pour la livraison/récupération.\n"

        prompt += f"""
STYLE:
- Court (1-2 phrases max)
- Naturel et fluide, comme une vraie conversation
- PAS de formules répétitives
- Varie tes réponses

HISTORIQUE DE LA CONVERSATION:
{history_text}

IMPORTANT: Réponds DIRECTEMENT au dernier message du client, sans salutation inutile!"""

        # Injecter le résumé STM si disponible (contexte compressé des anciens messages)
        if context_summary:
            prompt = prompt.replace(
                "HISTORIQUE DE LA CONVERSATION:",
                f"CONTEXTE RÉSUMÉ (échanges précédents):\n{context_summary}\n\nDERNIERS MESSAGES:"
            )

        return prompt


# Instance globale
_deepseek_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    """Retourne l'instance globale du client DeepSeek"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client
