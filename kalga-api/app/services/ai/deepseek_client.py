"""
Client DeepSeek API v3.0
========================
Architecture simplifiée — DeepSeek décide ET rédige:
  - IDENTITÉ    : Qui est le bot (permanent)
  - BRIEF PRODUIT : Produit + règles business + localisation complète
  - HISTORIQUE  : 45 derniers messages de la conversation
  - DÉCISION    : DeepSeek retourne un JSON à 4 champs
"""
import json
import httpx
import logging
from typing import Optional, Dict, Any, List
from ...config import settings

logger = logging.getLogger("kalga.deepseek")


# =============================================================================
# IDENTITÉ (permanent, ne change jamais)
# =============================================================================

IDENTITY_PROMPT = """Tu es un vendeur WhatsApp humain, intelligent et honnête.

Tes 3 principes fondamentaux:
1. PRÉSENCE — Tu réponds toujours à ce que le client VIENT de dire. Pas à ce que tu voulais dire.
2. HONNÊTETÉ — Ce que tu ne sais pas, tu le dis. Tu n'inventes jamais d'horaires, d'adresses ou d'infos.
3. FLUIDITÉ — Court, naturel, direct. Comme un ami sur WhatsApp. Jamais robotique. Jamais répétitif.

RÈGLE ABSOLUE SUR LE PRIX: Quand un accord est confirmé, TOUJOURS mentionner le prix exact dans la réponse.
Exemple JUSTE: "Parfait pour 20 000 F! Livraison ou tu passes?"
Exemple FAUX: "Parfait! Livraison ou tu passes?" ← prix absent = confusion client

Tu ne connais QUE ce qui t'est communiqué sur le produit. Rien de plus.

RÈGLE FORMAT DE RÉPONSE — TEXTE OU VOCAL:
Tu peux répondre par texte (use_voice: false) ou par note vocale (use_voice: true).
Choisis le vocal quand c'est plus naturel et humain:
  ✅ use_voice: true  → le client a envoyé un vocal (contexte [🎤]), message émotionnel ou de relation ("merci", "super", enthousiasme), accord final sur le prix, messages chaleureux personnels, quand tu veux créer de la proximité
  ❌ use_voice: false → le client demande un prix/infos factuelles, message avec liste (variantes, livraison), contient une adresse à noter, le client vient d'écrire un texte court sec, contexte de négociation tendue, message de suivi livraison

En cas de doute: préfère le texte. Le vocal doit paraître spontané, pas systématique.

Tu réponds TOUJOURS en JSON valide avec exactement ces 5 champs:
{
  "is_deal": true ou false,
  "price_mentioned": nombre ou null,
  "send_location": true ou false,
  "use_voice": true ou false,
  "response": "ton message WhatsApp ici"
}"""

CORRECTION_SYSTEM_PROMPT = """Tu es un assistant de commerce WhatsApp en mode correction.
Un client signale que tu n'as pas répondu à sa vraie question.
Analyse l'historique de conversation et identifie la vraie demande ignorée.

Tu réponds TOUJOURS en JSON valide avec exactement ces 6 champs:
{
  "original_question": "la vraie question du client que tu avais ignorée",
  "corrected_answer": "la bonne réponse factuelle à cette vraie question",
  "is_deal": false,
  "price_mentioned": null,
  "send_location": false,
  "response": "Pardon pour la confusion! [vraie réponse ici, brève et directe]"
}"""


class DeepSeekClient:
    """
    Client pour l'API DeepSeek v3.0.
    DeepSeek décide ET rédige — retourne un JSON structuré à 4 champs.
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
        max_tokens: int = 400,
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Envoie une requête multi-messages à DeepSeek.

        Args:
            messages: Liste de messages [{role, content}, ...]
            temperature: Créativité (0-1). 0.7 = bon équilibre
            max_tokens: Taille max de la réponse JSON
            system_prompt: Si fourni, remplace IDENTITY_PROMPT (ex: mode correction)

        Returns:
            La réponse brute (JSON string) ou None en cas d'erreur
        """
        if not self.api_key:
            logger.error("Clé API DeepSeek manquante!")
            return None

        full_messages = [
            {"role": "system", "content": system_prompt if system_prompt is not None else IDENTITY_PROMPT},
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
                        logger.debug(f"Réponse DeepSeek brute: {content[:120]}...")
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
    # AGENTIQUE — function calling (DeepSeek choisit le tool)
    # =========================================================================

    async def agentic_completion(
        self,
        system_prompt: str,
        user_message: str,
        tools: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[Dict]:
        """
        Appel DeepSeek avec function calling (mode agentique).

        Retourne un dict :
            {"type": "text",      "content": "..."}
            {"type": "tool_call", "name": "...", "args": {...}}
        Retourne None en cas d'erreur.
        """
        if not self.api_key:
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
                                {"role": "user",   "content": user_message}
                            ],
                            "tools": tools,
                            "tool_choice": "auto",
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        }
                    )

                    if response.status_code != 200:
                        logger.warning(f"DeepSeek agentic [{response.status_code}]: {response.text[:100]}")
                        if attempt < self.max_retries:
                            continue
                        return None

                    data = response.json()
                    choice = data["choices"][0]["message"]

                    if choice.get("tool_calls"):
                        tc = choice["tool_calls"][0]
                        name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            args = {}
                        logger.info(f"DeepSeek tool_call: {name}({args})")
                        return {"type": "tool_call", "name": name, "args": args}

                    content = choice.get("content", "")
                    logger.debug(f"DeepSeek agentic text: {content[:80]}")
                    return {"type": "text", "content": content}

            except httpx.TimeoutException:
                logger.warning(f"Timeout DeepSeek agentic (tentative {attempt + 1})")
                if attempt < self.max_retries:
                    continue
                return None
            except Exception as e:
                logger.error(f"Exception DeepSeek agentic: {type(e).__name__}: {e}")
                if attempt < self.max_retries:
                    continue
                return None

        return None

    def build_agentic_messages(
        self,
        product_name: str,
        price: float,
        min_price: float,
        conversation_history: List[Dict],
        client_message: str,
        is_first_message: bool = False,
        product_description: str = None,
        variants: List[str] = None,
        merchant_address: str = None,
        merchant_city: str = None,
        merchant_commune: str = None,
        merchant_quarter: str = None,
        merchant_persona: Dict = None,
        knowledge_context: List[str] = None,
        conversation_status: str = "active",
        current_offer: float = None,
        episodic_context: str = None,
        stm_summary: str = None,
        stm_recent: List[Dict] = None,
        client_sentiment: Optional[Dict] = None,
        ltm_facts: Optional[List[str]] = None,
    ):
        """
        Construit (system_prompt, user_message) pour agentic_completion().

        system_prompt = brief produit + TOOL_DECISION_GUIDE
        user_message  = [mémoire épisodique] + [résumé STM] + [msgs récents] + message client + état
        """
        from .tools import TOOL_DECISION_GUIDE

        # --- System prompt : brief produit + guide outils ---
        brief = self.build_product_brief(
            product_name=product_name,
            price=price,
            min_price=min_price,
            product_description=product_description,
            variants=variants,
            merchant_address=merchant_address,
            merchant_city=merchant_city,
            merchant_commune=merchant_commune,
            merchant_quarter=merchant_quarter,
            merchant_persona=merchant_persona
        )

        system_prompt = brief

        if knowledge_context:
            kb_lines = "\n".join(f"  • {kb}" for kb in knowledge_context)
            system_prompt += f"\n\nINFORMATIONS UTILES (réponses habituelles de ce marchand):\n{kb_lines}"

        system_prompt += f"\n\n{TOOL_DECISION_GUIDE}"

        # --- User message : historique + message client ---
        # Si STM a compressé, on utilise stm_recent (fenêtre verbatim) ;
        # sinon on prend les 45 derniers messages bruts.
        history_source = stm_recent if stm_summary is not None and stm_recent is not None \
            else (conversation_history[-45:] if len(conversation_history) > 45 else conversation_history)

        history_lines = []
        for msg in history_source:
            role = "Client" if msg.get('is_from_client') else "Toi"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        history_text = "\n".join(history_lines)

        parts = []
        # 1. Faits LTM au premier message (client connu — bref résumé de contexte)
        if is_first_message and ltm_facts:
            facts_lines = "\n".join(f"  • {f}" for f in ltm_facts[:4])
            parts.append(f"[CLIENT CONNU — INFOS UTILES]\n{facts_lines}")
        # 2. Mémoire épisodique (sessions passées + faits LTM détaillés) — pas au 1er msg
        if not is_first_message and episodic_context:
            parts.append(episodic_context)
        # 3. Résumé STM des anciens messages compressés
        if not is_first_message and stm_summary:
            parts.append(f"[RÉSUMÉ DES ÉCHANGES PRÉCÉDENTS]\n{stm_summary}")
        if is_first_message and not ltm_facts:
            parts.append("C'est le PREMIER message de ce client. Commence par saluer et présente le prix.")
        elif is_first_message and ltm_facts:
            parts.append("C'est le PREMIER message de cette session. Ce client est connu — adapte le ton (pas besoin de te présenter longuement).")
        # 4. Messages récents verbatim
        if history_text:
            label = "[DERNIERS MESSAGES]" if stm_summary else "CONVERSATION EN COURS:"
            parts.append(f"{label}\n{history_text}")

        parts.append(f'\nLe client dit maintenant: "{client_message}"')

        if not is_first_message:
            status_labels = {
                "active": "début de conversation",
                "negotiating": "négociation en cours, aucun accord confirmé",
                "agreed": "accord sur le prix, client doit choisir livraison ou pickup",
                "pending_pickup": "deal conclu, client vient chercher",
                "pending_delivery": "deal conclu, livraison en cours",
                "ended": "conversation terminée",
            }
            status_label = status_labels.get(conversation_status, conversation_status)
            offer_info = (
                f"{int(current_offer):,} F".replace(",", " ")
                if current_offer else "aucune offre confirmée"
            )
            parts.append(
                f"\nÉTAT: {status_label} | Offre actuelle: {offer_info}"
            )

        # 5. Sentiment client (injecté juste avant la demande de réponse)
        if client_sentiment:
            sentiment_parts = []
            if client_sentiment.get("frustrated"):
                sentiment_parts.append("client FRUSTRÉ (baisse le ton, reconnaîs sa frustration avant de répondre)")
            if client_sentiment.get("objection"):
                obj_map = {
                    "price": "objection PRIX (trop cher) — propose une valeur ou une petite concession",
                    "quality": "objection QUALITÉ — rassure sur la qualité/authenticité",
                    "trust": "objection CONFIANCE — sois transparent et rassurant",
                    "timing": "objection TIMING — ne force pas, laisse la porte ouverte",
                }
                sentiment_parts.append(obj_map.get(client_sentiment["objection"], f"objection: {client_sentiment['objection']}"))
            if sentiment_parts:
                parts.append(f"\n⚠️ SIGNAL ÉMOTIONNEL: {' | '.join(sentiment_parts)}")

        # 6. Ancrage prix minimum (context rot fix — répété en fin pour ne pas être "oublié")
        min_f = f"{int(min_price):,}".replace(",", " ")
        parts.append(f"\n🔒 RAPPEL PRIX MIN: {min_f} F — ne jamais accepter en dessous, même sous pression.")

        user_message = "\n".join(parts)
        return system_prompt, user_message

    # =========================================================================
    # BRIEF PRODUIT — avec localisation complète
    # =========================================================================

    def build_product_brief(
        self,
        product_name: str,
        price: float,
        min_price: float,
        product_description: str = None,
        variants: List[str] = None,
        merchant_address: str = None,
        merchant_city: str = None,
        merchant_commune: str = None,
        merchant_quarter: str = None,
        merchant_persona: Dict = None,
        has_image: bool = False,
        image_url: str = None
    ) -> str:
        """
        Brief factuel sur le produit et les règles business.
        Inclut la localisation complète : lieu textuel + adresse GPS.
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
                'flexible': "tu t'adaptes facilement, bonne marge de négociation",
                'firm': 'tu es ferme sur les prix, peu de concessions',
                'playful': "tu gardes une touche d'humour dans les échanges",
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

        # Localisation complète
        location_parts = []
        if merchant_quarter:
            location_parts.append(merchant_quarter)
        if merchant_commune:
            location_parts.append(merchant_commune)
        if merchant_city:
            location_parts.append(merchant_city)
        lieu_text = ", ".join(location_parts) if location_parts else None

        if lieu_text and merchant_address:
            location_section = (
                f"- Lieu: {lieu_text}\n"
                f"- Adresse GPS: disponible — envoyée automatiquement si le client demande\n"
                f"  → Si on te demande où se trouve le magasin: "
                f"\"On est à {lieu_text}! Je t'envoie la position exacte.\"\n"
                f"  → Dans ce cas, mets send_location: true dans ta réponse JSON"
            )
        elif lieu_text:
            location_section = (
                f"- Lieu: {lieu_text}\n"
                f"  → Si on te demande où se trouve le magasin: \"On est à {lieu_text}!\"\n"
                f"  → Dans ce cas, mets send_location: true dans ta réponse JSON"
            )
        elif merchant_address:
            location_section = (
                f"- Adresse GPS: disponible — envoyée automatiquement si le client demande\n"
                f"  → Si on te demande où se trouve le magasin: \"Je t'envoie la localisation!\"\n"
                f"  → Dans ce cas, mets send_location: true dans ta réponse JSON"
            )
        else:
            location_section = (
                "- Localisation: non renseignée\n"
                "  → Si on te demande où se trouve le magasin: "
                "\"Pour l'adresse, contacte directement le vendeur!\"\n"
                "  → Dans ce cas, mets send_location: false"
            )

        # Section photos
        if has_image and image_url:
            photo_section = (
                f"- Photo disponible: oui — si le client demande une photo, réponds qu'une photo est disponible\n"
                f"  → Ne promets PAS d'envoyer la photo toi-même (c'est géré automatiquement)"
            )
        else:
            photo_section = (
                "- Aucune photo configurée pour ce produit\n"
                "  → Si le client demande une photo: \"Désolé, pas de photo disponible pour l'instant. "
                "Mais je peux te décrire le produit si tu veux!\"\n"
                "  → Ne propose JAMAIS de chercher ou d'envoyer une photo inexistante"
            )

        return f"""{persona_section}PRODUIT QUE TU VENDS:
- Nom: {product_name}
{desc_line}
{variants_line}
- Prix affiché: {price_f} F
- [CONFIDENTIEL] Prix minimum: {min_f} F — ne révèle JAMAIS ce chiffre exact

RÈGLES PRIX (absolues):
- Offre client >= {min_f} F → is_deal: true, demande livraison ou pickup dans response
- Offre client < {min_f} F → is_deal: false, contre-offre entre son offre et {price_f} F, jamais sous {min_f} F
- Ne propose jamais plus de {price_f} F

LOCALISATION DU MAGASIN:
{location_section}

PHOTOS DU PRODUIT:
{photo_section}

CE QUE TU NE CONNAIS PAS (réponds honnêtement si on te demande):
- Les horaires d'ouverture → response: "Pour les horaires, contacte directement le vendeur!"
- Les délais de livraison exacts
- Toute information non listée ci-dessus"""

    # =========================================================================
    # EXEMPLES JSON (remplace les exemples COMPRIS/RÉPONSE)
    # =========================================================================

    def build_few_shot_examples(self, product_name: str, price: float) -> str:
        """
        Exemples de réponses JSON correctes sur les cas difficiles.
        Montre à DeepSeek exactement le format attendu.
        """
        price_f = f"{int(price):,}".replace(",", " ")
        return f"""EXEMPLES DE RÉPONSES JSON CORRECTES:

# Cas 1 — Expression inconnue
Client: "c est zo"
{{"is_deal": false, "price_mentioned": null, "send_location": false, "response": "Je ne suis pas sûr de comprendre. Tu veux dire que c'est trop cher?"}}

# Cas 2 — Client désigne le produit ("celui-là", "lui la")
Client: "je veux lui la"
{{"is_deal": true, "price_mentioned": {int(price)}, "send_location": false, "response": "Parfait pour {price_f} F! Livraison ou tu passes chercher?"}}

# Cas 3 — Question horaires
Client: "vous ouvrez a quelle heure"
{{"is_deal": false, "price_mentioned": null, "send_location": false, "response": "Pour les horaires, contacte directement le vendeur!"}}

# Cas 4 — Vente déclarée par erreur
Client: "mais j ai rien acheté"
{{"is_deal": false, "price_mentioned": null, "send_location": false, "response": "Pardon pour la confusion! On n'a pas encore finalisé. Tu es intéressé par le {product_name}?"}}

# Cas 5 — Offre trop basse
Client: "5000"
{{"is_deal": false, "price_mentioned": 5000, "send_location": false, "response": "5 000 F c'est un peu bas! Fais-moi une offre plus proche et on se comprend."}}

# Cas 6 — Client demande la localisation
Client: "vous etes ou"
{{"is_deal": false, "price_mentioned": null, "send_location": true, "response": "Je t'envoie la position!"}}

# Cas 7 — "Oui" en réponse à une question d'information (PAS un deal)
Historique: Toi: "Tu veux plus de détails?" → Client: "Oui oui"
{{"is_deal": false, "price_mentioned": null, "send_location": false, "response": "Bien sûr! {product_name} en très bonne qualité. Tu veux voir une photo?"}}

# Cas 8 — Client frustré
Client: "repond a ma question"
{{"is_deal": false, "price_mentioned": null, "send_location": false, "response": "Pardon! Tu demandais quoi exactement? Je t'écoute."}}

# Cas 9 — Reply WhatsApp sur une photo (préfixe [Répond à la photo: "X"])
# Ce préfixe est un signal technique: le client a appuyé sur cette photo précise pour répondre.
# Son message s'interprète DANS LE CONTEXTE de cette photo, quelle que soit sa formulation.
Client: "[Répond à la photo: \"Modèle Fleur rouge\"] non c'est lui la que j'ai choisi"
{{"is_deal": true, "price_mentioned": {int(price)}, "send_location": false, "response": "Super choix, le Modèle Fleur rouge! {price_f} F et c'est à toi. Livraison ou tu passes?"}}

# Cas 10 — Reply WhatsApp sur un message texte (préfixe [Répond à: "X"])
# Même logique: le client répond à un message précis du bot. Interprète dans ce contexte.
Client: "[Répond à: \"Livraison ou tu passes chercher?\"] je vais passer"
{{"is_deal": false, "price_mentioned": null, "send_location": true, "response": "Parfait! Je t'envoie la localisation du magasin."}}"""

    def build_correction_messages(
        self,
        conversation_history: List[Dict],
        client_correction: str,
        product_name: str,
        price: float
    ) -> List[Dict]:
        """
        Prompt spécial "mode correction".
        Déclenché quand le client signale que le bot a répondu à côté.

        DeepSeek doit:
        1. Analyser l'historique pour identifier la VRAIE question ignorée
        2. Générer la bonne réponse
        3. Retourner un JSON avec la correction ET la réponse au client
        """
        price_f = f"{int(price):,}".replace(",", " ")

        recent = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        history_lines = []
        for msg in recent:
            role = "Client" if msg.get('is_from_client') else "Toi"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        history_text = "\n".join(history_lines)

        correction_prompt = f"""Tu es un vendeur WhatsApp pour {product_name} à {price_f} F.

SITUATION: Le client vient de dire que tu n'as PAS répondu à sa vraie question.

HISTORIQUE RÉCENT:
{history_text}

Le client dit maintenant: "{client_correction}"

TON TRAVAIL:
1. Identifie la question ou demande RÉELLE que le client avait posée et à laquelle tu as mal répondu
2. Génère la bonne réponse à cette vraie question
3. Réponds au client en reconnaissant l'erreur BRIÈVEMENT puis donne la vraie réponse

Réponds en JSON valide uniquement:
{{"original_question": "la vraie question du client", "corrected_answer": "la bonne réponse", "is_deal": false, "price_mentioned": null, "send_location": false, "response": "Pardon pour la confusion! [vraie réponse ici]"}}"""

        return [
            {"role": "user", "content": correction_prompt},
        ]

    def parse_json_response(self, raw_response: str) -> Optional[Dict]:
        """
        Parse la réponse JSON de DeepSeek.
        Retourne un dict avec les 4 champs ou None si le parsing échoue.

        Champs attendus:
          - is_deal: bool
          - price_mentioned: float ou null
          - send_location: bool
          - response: str
        """
        if not raw_response:
            return None

        # Nettoyer les balises markdown si présentes
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)

            # Valider et normaliser les champs
            result = {
                "is_deal": bool(data.get("is_deal", False)),
                "price_mentioned": float(data["price_mentioned"]) if data.get("price_mentioned") else None,
                "send_location": bool(data.get("send_location", False)),
                "use_voice": bool(data.get("use_voice", False)),
                "response": str(data.get("response", "")).strip()
            }
            # Champs optionnels présents uniquement en mode correction
            if data.get("original_question"):
                result["original_question"] = str(data["original_question"]).strip()
            if data.get("corrected_answer"):
                result["corrected_answer"] = str(data["corrected_answer"]).strip()

            if not result["response"]:
                logger.warning("DeepSeek JSON: champ 'response' vide")
                return None

            logger.debug(
                f"DeepSeek JSON parsé: deal={result['is_deal']}, "
                f"price={result['price_mentioned']}, location={result['send_location']}, "
                f"voice={result['use_voice']}"
            )
            return result

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Échec parsing JSON DeepSeek: {e} | Brut: {raw_response[:100]}")
            return None

    # Alias pour compatibilité avec l'ancien code
    def parse_response(self, raw_response: str) -> str:
        """Compatibilité ascendante — extrait uniquement le texte 'response'."""
        result = self.parse_json_response(raw_response)
        if result:
            return result["response"]
        return raw_response.strip() if raw_response else ""


# Instance globale
_deepseek_client: Optional[DeepSeekClient] = None


def get_deepseek_client() -> DeepSeekClient:
    """Retourne l'instance globale du client DeepSeek"""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client
