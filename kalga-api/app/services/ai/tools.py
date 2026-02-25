"""
Agentic Tool Definitions
========================
Définit les tools exposés à DeepSeek via function calling.
DeepSeek utilise le même format qu'OpenAI (compatible).

L'IA décide ELLE-MÊME quel tool appeler selon le contexte.
Le bot exécute ensuite le tool localement.

Tools disponibles :
- send_photo         : envoyer la photo du produit actuel (1ère demande ou re-demande)
- send_variants      : envoyer d'AUTRES modèles/couleurs/tailles (≠ photo du même produit)
- send_location      : envoyer la localisation GPS du marchand
- counter_offer      : proposer un contre-prix pendant la négociation
- accept_deal        : confirmer la vente et demander livraison ou retrait
- end_conversation   : terminer la conversation poliment

═══════════════════════════════════════════════════════════════
GUIDE DE DÉCISION POUR L'IA — QUAND APPELER QUEL TOOL
═══════════════════════════════════════════════════════════════

Le client dit "tu as une photo ?" ou "montre-moi" ou "envoie l'image"
→ send_photo  (même si une photo a déjà été envoyée — renvoie-la)

Le client dit "tu as d'autres photos ?" ou "d'autres angles ?"
→ send_photo  (pas send_variants — il parle du MÊME produit)

Le client dit "tu as d'autres couleurs ?" ou "il existe en rouge ?"
ou "autre modèle ?" ou "autre taille ?"
→ send_variants  (il veut un PRODUIT DIFFÉRENT de la même gamme)

Le client dit "adresse ?" ou "où vous êtes ?" ou "je viens chercher"
ou "comment venir ?" ou "localisation ?"
→ send_location  (même s'il a déjà demandé — renvoie la GPS)

Le client dit "ok", "deal", "je prends", "vendu", "c'est bon",
ou fait une offre >= prix minimum
→ accept_deal

Le client fait une offre < prix minimum ou dit "c'est trop cher, fais un effort"
→ counter_offer  avec un prix entre son offre et le prix affiché

Le client dit "merci bye", "je reviendrai", "pas pour l'instant",
"laisse tomber", "au revoir"
→ end_conversation

Tout autre message (négociation, question sur le produit, objection, etc.)
→ NE PAS appeler de tool — répondre en texte libre
═══════════════════════════════════════════════════════════════
"""

# ─────────────────────────────────────────────
# Schémas JSON des tools (format OpenAI/DeepSeek)
# ─────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_photo",
            "description": (
                "Envoie la photo du produit ACTUEL au client. "
                "Utilise ce tool quand le client demande UNE photo, UNE image, veut voir le produit, "
                "ou demande D'AUTRES photos/angles du MÊME produit. "
                "IMPORTANT : si le client dit 'd\\'autres photos', 'tu as d\\'autres photos ?', "
                "'envoie encore la photo', 'je veux revoir' → utilise send_photo, PAS send_variants. "
                "send_variants est réservé aux AUTRES COULEURS / TAILLES / MODÈLES différents. "
                "Exemples : 'envoie la photo', 'montre-moi', 'tu as une image?', "
                "'d\\'autres photos du produit?', 'je n\\'ai pas vu la photo', 'envoie encore'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": (
                            "Courte phrase naturelle d'accompagnement. "
                            "Varie selon le contexte : première fois → 'Voilà !' ; "
                            "re-demande → 'Je te la renvoie !' ou 'Tiens, la voilà encore !'"
                        )
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_variants",
            "description": (
                "Envoie les AUTRES variantes du produit : autres couleurs, tailles, modèles. "
                "Utilise ce tool UNIQUEMENT quand le client veut un produit DIFFÉRENT de la même gamme. "
                "NE PAS utiliser pour 'd\\'autres photos du même produit' → utilise send_photo à la place. "
                "Exemples déclencheurs : 'tu as d\\'autres couleurs?', 'il existe en rouge?', "
                "'autre taille?', 'en XL?', 'autre modèle?', 'tu as la même chose en noir?'. "
                "NE PAS déclencher pour : 'd\\'autres photos?', 'montre-moi encore', 'autre angle?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Courte phrase naturelle, ex: 'Voilà les autres modèles disponibles !'"
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_location",
            "description": (
                "Envoie la localisation GPS du magasin au client. "
                "Utilise ce tool quand le client demande où se trouve le magasin, veut venir chercher, "
                "demande l\\'adresse ou la localisation — même si la localisation a déjà été envoyée. "
                "IMPORTANT : ce tool ne confirme PAS une vente. Il envoie juste la position GPS. "
                "N\\'utilise PAS accept_deal en même temps — si le client veut venir chercher "
                "sans avoir encore dit 'ok deal', utilise send_location seul. "
                "Exemples : 'où vous êtes?', 'l\\'adresse?', 'je viens chercher', "
                "'comment venir?', 'localisation?', 'envoyez la map', 'où est le magasin?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": (
                            "Courte phrase naturelle. "
                            "Ex: 'Je t\\'envoie la localisation !' ou 'Voilà où on est !'"
                        )
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "counter_offer",
            "description": (
                "Propose un contre-prix au client pendant la négociation. "
                "Utilise ce tool quand le client fait une offre inférieure au prix minimum "
                "et qu\\'on doit négocier vers un compromis. "
                "NE PAS utiliser si le client accepte le prix ou si la vente est déjà conclue. "
                "NE PAS proposer un prix supérieur au prix affiché ni inférieur au prix minimum."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {
                        "type": "number",
                        "description": "Prix proposé en FCFA. Doit être entre le prix minimum (secret) et le prix affiché."
                    },
                    "message": {
                        "type": "string",
                        "description": "Message naturel pour présenter la contre-offre, ex: 'Je peux faire 45 000 F, c\\'est mon meilleur prix !'"
                    }
                },
                "required": ["price", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "accept_deal",
            "description": (
                "Confirme la vente et demande au client s\\'il préfère la livraison ou le retrait en magasin. "
                "Utilise ce tool quand le client accepte clairement le prix "
                "('ok', 'deal', 'je prends', 'vendu', 'd\\'accord', 'c\\'est bon', 'ok ça marche') "
                "ou quand son offre est >= au prix minimum acceptable. "
                "NE PAS utiliser quand le client demande juste la localisation sans avoir accepté le prix."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "delivery_type": {
                        "type": "string",
                        "enum": ["ask", "delivery", "pickup"],
                        "description": (
                            "'ask' = le client a accepté mais n\\'a pas précisé — lui demander. "
                            "'delivery' = le client a explicitement demandé la livraison à domicile. "
                            "'pickup' = le client a explicitement dit qu\\'il vient chercher au magasin."
                        )
                    },
                    "message": {
                        "type": "string",
                        "description": "Message naturel, ex: 'Super ! Tu préfères la livraison ou tu passes chercher ?'"
                    }
                },
                "required": ["delivery_type", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_conversation",
            "description": (
                "Termine poliment la conversation sans conclure de vente. "
                "Utilise ce tool quand le client dit au revoir, n\\'est plus intéressé, "
                "ou quand la conversation est clairement terminée sans achat. "
                "Exemples : 'merci bye', 'je reviendrai', 'pas pour l\\'instant', "
                "'laisse tomber', 'au revoir', 'c\\'est bon j\\'ai trouvé ailleurs'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message d'au revoir naturel et chaleureux, ex: 'Pas de souci, reviens quand tu veux !'"
                    }
                },
                "required": ["message"]
            }
        }
    }
]

# Noms des tools reconnus (pour validation)
TOOL_NAMES = {t["function"]["name"] for t in TOOLS}
