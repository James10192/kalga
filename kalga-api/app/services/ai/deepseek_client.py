"""
Client DeepSeek API v2.0
========================
Architecture en sous-prompts:
  - IDENTITÉ    : Qui est le bot (permanent, ~80 tokens)
  - BRIEF PRODUIT : Ce qu'il vend (par produit, ~150 tokens)
  - SITUATION    : État en cours (par message, ~150 tokens)
  - FORMAT COMPRIS/RÉPONSE : Raisonnement guidé avant réponse
"""
import httpx
import logging
from typing import Optional, Dict, Any, List
from ...config import settings

logger = logging.getLogger("kalga.deepseek")


# =============================================================================
# SOUS-PROMPT 1 — IDENTITÉ (permanent, ne change jamais)
# =============================================================================

IDENTITY_PROMPT = """Tu es un vendeur WhatsApp humain, intelligent et honnête.

Tes 3 principes fondamentaux:
1. PRÉSENCE — Tu réponds toujours à ce que le client VIENT de dire. Pas à ce que tu voulais dire.
2. HONNÊTETÉ — Ce que tu ne sais pas, tu le dis. Tu n'inventes jamais d'horaires, d'adresses ou d'infos.
3. FLUIDITÉ — Court, naturel, direct. Comme un ami sur WhatsApp. Jamais robotique. Jamais répétitif.

RÈGLE ABSOLUE SUR LE PRIX: Quand un accord est confirmé, TOUJOURS mentionner le prix exact dans la réponse.
Exemple JUSTE: "Parfait pour 20 000 F! Livraison ou tu passes?"
Exemple FAUX: "Parfait! Livraison ou tu passes?" ← prix absent = confusion client

Tu ne connais QUE ce qui t'est communiqué sur le produit. Rien de plus."""


class DeepSeekClient:
    """
    Client pour l'API DeepSeek v2.0.
    Architecture multi-messages pour un contexte structuré et puissant.
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
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> Optional[str]:
        """
        Envoie une requête multi-messages à DeepSeek.

        Args:
            messages: Liste de messages [{role, content}, ...]
                      Le system prompt IDENTITY est automatiquement ajouté.
            temperature: Créativité (0-1). 0.7 = bon équilibre
            max_tokens: Inclut le raisonnement COMPRIS + la RÉPONSE

        Returns:
            La réponse générée ou None en cas d'erreur
        """
        if not self.api_key:
            logger.error("Clé API DeepSeek manquante!")
            return None

        full_messages = [
            {"role": "system", "content": IDENTITY_PROMPT},
            *messages
        ]

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
                            "messages": full_messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data['choices'][0]['message']['content']
                        logger.debug(f"Réponse DeepSeek brute: {content[:80]}...")
                        return content
                    else:
                        logger.warning(
                            f"Erreur DeepSeek [{response.status_code}]: {response.text[:100]}"
                        )
                        if attempt < self.max_retries:
                            continue
                        return None

            except httpx.TimeoutException:
                logger.warning(
                    f"Timeout DeepSeek (tentative {attempt + 1}/{self.max_retries + 1})"
                )
                if attempt < self.max_retries:
                    continue
                return None

            except Exception as e:
                logger.error(f"Exception DeepSeek: {type(e).__name__}: {e}")
                if attempt < self.max_retries:
                    continue
                return None

        return None

    # =========================================================================
    # SOUS-PROMPT 2 — BRIEF PRODUIT
    # =========================================================================

    def build_product_brief(
        self,
        product_name: str,
        price: float,
        min_price: float,
        product_description: str = None,
        variants: List[str] = None,
        merchant_address: str = None,
        merchant_persona: Dict = None
    ) -> str:
        """
        Brief factuel sur le produit. Injecté une fois, stable pendant la conversation.
        Contient uniquement des faits vérifiables — aucune règle de comportement.
        Inclut optionnellement la persona du marchand (ton, style, phrase signature).
        """
        price_f = f"{int(price):,}".replace(",", " ")
        min_f = f"{int(min_price):,}".replace(",", " ")

        # Section persona (ton + style + catchphrase)
        persona_section = ""
        if merchant_persona:
            tone = merchant_persona.get('bot_tone', 'casual')
            style = merchant_persona.get('bot_style', 'flexible')
            catchphrase = merchant_persona.get('bot_catchphrase')
            tone_desc = {
                'casual': 'décontracté et proche, tu tutoies naturellement',
                'formal': 'respectueux et professionnel, tu vouvoies le client',
                'friendly': 'chaleureux et enthousiaste, tu utilises des expressions positives',
                'professional': 'sérieux et efficace, tu vas droit au but',
            }.get(tone, tone)
            style_desc = {
                'flexible': 'tu t\'adaptes facilement, bonne marge de négociation',
                'firm': 'tu es ferme sur les prix, peu de concessions',
                'playful': 'tu gardes une touche d\'humour dans les échanges',
            }.get(style, style)
            persona_lines = [
                "STYLE DE COMMUNICATION (respecte ce style dans toutes tes réponses):",
                f"- Ton: {tone_desc}",
                f"- Style: {style_desc}",
            ]
            if catchphrase:
                persona_lines.append(f"- Phrase signature: utilise \"{catchphrase}\" pour conclure ou motiver")
            persona_section = "\n".join(persona_lines) + "\n\n"

        desc_line = f"- Description: {product_description}" if product_description else ""
        variants_line = (
            f"- Variantes disponibles: {', '.join(variants)}"
            if variants else "- Variantes: aucune variante pour ce produit"
        )

        if merchant_address:
            location_line = f"- Localisation du magasin: {merchant_address}"
            location_rule = (
                f"  → Si on te demande où se trouve le magasin: "
                f"\"On est à {merchant_address}! Je t'envoie la position.\""
            )
        else:
            location_line = "- Localisation: position GPS envoyée automatiquement si demandée"
            location_rule = (
                "  → Si on te demande où se trouve le magasin: "
                "\"Je t'envoie la localisation!\" (GPS automatique)"
            )

        return f"""{persona_section}PRODUIT QUE TU VENDS:
- Nom: {product_name}
{desc_line}
{variants_line}
- Prix affiché: {price_f} F
- [CONFIDENTIEL] Prix minimum: {min_f} F — ne révèle JAMAIS ce chiffre exact

RÈGLES PRIX (absolues):
- Offre client >= {min_f} F → accepte immédiatement, demande livraison ou pickup
- Offre client < {min_f} F → propose un chiffre entre son offre et {price_f} F, jamais sous {min_f} F
- Ne propose jamais plus de {price_f} F

LOCALISATION:
{location_line}
{location_rule}

CE QUE TU NE CONNAIS PAS (réponds honnêtement si on te demande):
- Les horaires d'ouverture → "Pour les horaires, contacte directement le vendeur!"
- Les délais de livraison exacts
- Toute information non listée ci-dessus"""

    # =========================================================================
    # SOUS-PROMPT 3 — FEW-SHOT EXAMPLES (raisonnement guidé)
    # =========================================================================

    def build_few_shot_examples(self, product_name: str) -> str:
        """
        Exemples de conversations bien gérées.
        Montre le format COMPRIS/RÉPONSE en action sur les cas difficiles.
        Beaucoup plus puissant que des règles écrites.
        """
        return f"""EXEMPLES DE BONNES RÉPONSES (format obligatoire):

# Cas 1 — Expression inconnue
Client: "c est zo"
COMPRIS: Le client utilise une expression que je ne comprends pas avec certitude
RÉPONSE: Je ne suis pas sûr de comprendre. Tu veux dire que c'est trop cher?

# Cas 2 — Désignation d'un produit visible ("celui-là")
Client: "je veux lui la"
COMPRIS: Le client désigne le produit visible et l'accepte au prix affiché — je dois confirmer le prix EXPLICITEMENT
RÉPONSE: Parfait pour [PRIX ICI] F! Livraison ou tu passes chercher?

# Cas 3 — Question sur les horaires
Client: "vous ouvrez a quelle heure"
COMPRIS: Le client demande les horaires que je ne connais pas
RÉPONSE: Pour les horaires, contacte directement le vendeur!

# Cas 4 — Vente conclue prématurément par erreur
Client: "mais j ai rien acheté"
COMPRIS: Le bot a déclaré une vente qui n'a pas eu lieu — le client corrige
RÉPONSE: Pardon pour la confusion! On n'a pas encore finalisé. Tu es intéressé par le {product_name}?

# Cas 5 — Le bot a répété le même prix plusieurs fois
Client: "pourquoi je vais discuter"
COMPRIS: Le client remet en question la proposition de discuter — le bot a été trop répétitif
RÉPONSE: Bonne question! Tu proposes combien et on s'arrange.

# Cas 6 — Offre trop basse
Client: "5000"
COMPRIS: Le client propose un prix sous le minimum acceptable
RÉPONSE: 5 000 F c'est un peu bas! Fais-moi une offre plus proche et on se comprend.

# Cas 7 — Client frustré après incompréhension
Client: "repond a ma question"
COMPRIS: Le bot n'a pas répondu à ce que le client demandait et le client est frustré
RÉPONSE: Pardon! Tu demandais quoi exactement? Je t'écoute.

# Cas 8 — Client dit avoir supprimé une photo
Client: "non j ai supprime la photo par erreur"
COMPRIS: Le client a effacé la photo accidentellement et en a besoin — je dois la renvoyer, pas répéter "tu peux la regarder plus haut"
RÉPONSE: Pas de problème, je te renvoie!

# Cas 9 — Client demande le prix après désignation d'un article
Client: "il fait combien"
COMPRIS: Le client veut confirmer le prix avant de finaliser — je dois donner le prix clairement sans relancer la négociation
RÉPONSE: C'est [PRIX] F. Ça te va?"""

    # =========================================================================
    # SOUS-PROMPT 4 — SITUATION EN COURS (par message)
    # =========================================================================

    def build_situation_prompt(
        self,
        negotiation_stage: str,
        history_text: str,
        key_facts: List[str] = None,
        health_alerts: List[str] = None,
        is_first_message: bool = False,
        final_price_mode: bool = False,
        min_price: float = None,
        client_profile: str = None,
        knowledge_context: List[str] = None
    ) -> str:
        """
        Snapshot de la situation actuelle de la conversation.
        Contient: stade, faits clés, alertes, base de connaissances, historique.
        """
        lines = ["SITUATION EN COURS:"]

        # Stade
        lines.append(f"- Stade: {negotiation_stage}")

        # Premier message
        if is_first_message:
            lines.append("- C'est le PREMIER message du client → commence par \"Salut!\" et donne le prix")

        # Mode dernier prix
        if final_price_mode and min_price:
            min_f = f"{int(min_price):,}".replace(",", " ")
            lines.append(
                f"- MODE DERNIER PRIX: propose {min_f} F comme prix final absolu, sois ferme mais respectueux"
            )

        # Profil client (fidélité)
        if client_profile:
            lines.append(f"- Profil client: {client_profile}")

        # Faits clés extraits de la conversation
        if key_facts:
            lines.append("\nFAITS CLÉS:")
            for fact in key_facts:
                lines.append(f"  → {fact}")

        # Alertes santé conversationnelle
        if health_alerts:
            lines.append("\nALERTES CONTEXTE:")
            for alert in health_alerts:
                lines.append(f"  ⚡ {alert}")

        # Base de connaissances (réponses types du marchand)
        if knowledge_context:
            lines.append("\nINFORMATIONS UTILES (réponses déjà données par ce marchand):")
            for kb_entry in knowledge_context:
                lines.append(f"  • {kb_entry}")

        # Historique
        if history_text:
            lines.append(f"\nCONVERSATION EN COURS:\n{history_text}")

        return "\n".join(lines)

    # =========================================================================
    # ASSEMBLAGE FINAL — build_messages()
    # =========================================================================

    def build_messages(
        self,
        product_name: str,
        price: float,
        min_price: float,
        history_text: str,
        client_message: str,
        is_first_message: bool = False,
        product_description: str = None,
        variants: List[str] = None,
        merchant_address: str = None,
        key_facts: List[str] = None,
        negotiation_stage: str = None,
        health_alerts: List[str] = None,
        final_price_mode: bool = False,
        client_profile: str = None,
        knowledge_context: List[str] = None,
        merchant_persona: Dict = None
    ) -> List[Dict]:
        """
        Assemble les 4 sous-prompts en un tableau de messages structuré.

        Structure:
          user  → Brief produit + few-shot examples
          assistant → "Compris."  (ancrage cognitif)
          user  → Situation en cours + message client + format attendu
        """
        # --- Sous-prompt 2: Brief produit + exemples ---
        brief = self.build_product_brief(
            product_name=product_name,
            price=price,
            min_price=min_price,
            product_description=product_description,
            variants=variants,
            merchant_address=merchant_address,
            merchant_persona=merchant_persona
        )
        examples = self.build_few_shot_examples(product_name)
        knowledge_message = f"{brief}\n\n{examples}"

        # --- Sous-prompt 3: Situation en cours ---
        situation = self.build_situation_prompt(
            negotiation_stage=negotiation_stage or "CONVERSATION EN COURS",
            history_text=history_text,
            key_facts=key_facts,
            health_alerts=health_alerts,
            is_first_message=is_first_message,
            final_price_mode=final_price_mode,
            min_price=min_price,
            client_profile=client_profile,
            knowledge_context=knowledge_context
        )

        # --- Message final: le client + format de réponse ---
        request = (
            f'Le client dit maintenant: "{client_message}"\n\n'
            f"Réponds en format EXACT:\n"
            f"COMPRIS: [une phrase — ce que le client veut vraiment]\n"
            f"RÉPONSE: [ton message WhatsApp, 1-2 phrases max, naturel et direct]"
        )

        final_user_message = f"{situation}\n\n{request}"

        return [
            {"role": "user", "content": knowledge_message},
            {"role": "assistant", "content": "Compris. Je suis prêt."},
            {"role": "user", "content": final_user_message},
        ]

    def parse_response(self, raw_response: str) -> str:
        """
        Extrait uniquement la partie RÉPONSE du format COMPRIS/RÉPONSE.
        Si le format n'est pas respecté, retourne la réponse brute.
        """
        if not raw_response:
            return raw_response

        # Chercher "RÉPONSE:" ou "REPONSE:" (avec ou sans accent)
        for marker in ["RÉPONSE:", "REPONSE:", "Réponse:", "Reponse:"]:
            if marker in raw_response:
                response_part = raw_response.split(marker, 1)[1].strip()
                # Nettoyer les éventuelles lignes supplémentaires
                response_part = response_part.split("\n")[0].strip()
                if response_part:
                    logger.debug(f"COMPRIS extrait: {raw_response.split(marker)[0][:80]}")
                    return response_part

        # Format non respecté — retourner la réponse brute nettoyée
        logger.warning("Format COMPRIS/RÉPONSE non respecté — réponse brute utilisée")
        return raw_response.strip()


# Instance globale
_deepseek_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    """Retourne l'instance globale du client DeepSeek"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client
