"""
Agentic Tool Definitions
========================
Définit les tools exposés à DeepSeek via function calling.
DeepSeek utilise le même format qu'OpenAI (compatible).

L'IA décide ELLE-MÊME quel tool appeler selon le contexte.
Le bot exécute ensuite le tool localement.

Tools disponibles :
- send_photo              : envoyer la photo du produit actuel (1ère demande ou re-demande)
- send_variants           : envoyer d'AUTRES modèles/couleurs/tailles (≠ photo du même produit)
- send_location           : envoyer la localisation GPS du marchand
- counter_offer           : proposer un contre-prix pendant la négociation
- accept_deal             : confirmer la vente et demander livraison ou retrait
- end_conversation        : terminer la conversation poliment
- request_human_takeover  : passer la main à un humain (litige, réclamation)
- send_payment_info       : envoyer les infos de paiement du marchand
- collect_delivery_address: demander et enregistrer l'adresse de livraison
"""

# ─────────────────────────────────────────────
# Guide de décision injecté dans le system prompt
# ─────────────────────────────────────────────

TOOL_DECISION_GUIDE = """
═══════════════════════════════════════════════════════════════
GUIDE DE DÉCISION — QUAND APPELER QUEL TOOL
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
→ NE PAS utiliser accept_deal en même temps si le deal n'est pas encore conclu

Le client ACCEPTE FERMEMENT un prix déjà annoncé ("ok je prends", "deal",
"vendu", "c'est bon je prends", "ça marche pour 10 000") OU fait une offre >= prix minimum
→ accept_deal

⚠️ NE PAS conclure (accept_deal) si, dans le MÊME message, le client :
  • demande encore une photo / d'autres modèles → send_photo / send_variants D'ABORD
  • propose un NOUVEAU prix plus bas → counter_offer
  • dit juste "oui"/"ok" en réponse à une question d'intérêt ("ça t'intéresse ?")
    SANS qu'un prix précis n'ait été accepté → réponds en texte, ne conclus pas
Toujours satisfaire la demande (photo, modèle, négociation) AVANT de conclure la vente.

Le client fait une offre < prix minimum ou dit "c'est trop cher, fais un effort"
→ counter_offer  avec un prix entre son offre et le prix affiché

Le client dit "merci bye", "je reviendrai", "pas pour l'instant",
"au revoir", "c'est bon j'ai trouvé ailleurs"
→ end_conversation

Le client dit "je veux parler à quelqu'un", "passez-moi un responsable",
"j'ai un problème", "litige", "réclamation"
→ request_human_takeover

Le client demande "comment payer ?", "Orange Money ?", "Wave ?",
"numéro de paiement", "compte"
→ send_payment_info

Après accept_deal avec delivery_type="delivery", si le client donne ou confirme
une adresse de livraison
→ collect_delivery_address

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
                "Utilise ce tool quand le client accepte clairement un PRIX DÉJÀ ANNONCÉ "
                "('ok je prends', 'deal', 'vendu', 'c\\'est bon je prends', 'ça marche pour ce prix') "
                "ou quand son offre est >= au prix minimum acceptable. "
                "NE PAS utiliser si le client demande une photo / d\\'autres modèles, "
                "ou propose un NOUVEAU prix plus bas (→ counter_offer), "
                "ou demande juste la localisation sans avoir accepté le prix. "
                "Un simple 'oui'/'ok' en réponse à 'ça t\\'intéresse ?' n\\'est PAS une acceptation de prix."
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
    },
    {
        "type": "function",
        "function": {
            "name": "request_human_takeover",
            "description": (
                "Passe la conversation à un humain (le marchand) quand la situation dépasse le bot. "
                "Utilise ce tool quand le client a un litige, une réclamation, un problème technique, "
                "ou demande explicitement à parler à une personne réelle. "
                "Exemples : 'je veux parler à quelqu\\'un', 'passez-moi un responsable', "
                "'j\\'ai un problème', 'litige', 'réclamation', 'c\\'est pas normal'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Raison du transfert, ex: 'réclamation client', 'question technique', 'litige'"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message rassurant au client, ex: 'Je transmets ton message au vendeur, il te répond très vite !'"
                    }
                },
                "required": ["reason", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_payment_info",
            "description": (
                "Envoie les informations de paiement du marchand (Orange Money, Wave, espèces, etc.). "
                "Utilise ce tool quand le client demande comment payer, le numéro de paiement, "
                "ou les moyens de paiement acceptés. "
                "Exemples : 'comment payer ?', 'Orange Money ?', 'Wave ?', "
                "'numéro de paiement', 'compte', 'je paye comment ?'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Courte intro naturelle, ex: 'Voici comment payer !' ou 'On accepte ces moyens de paiement :'"
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "collect_delivery_address",
            "description": (
                "Demande ou enregistre l\\'adresse de livraison du client après confirmation de la vente. "
                "Utilise ce tool UNIQUEMENT après accept_deal avec delivery_type='delivery', "
                "quand le client donne une adresse ou quand le bot doit la demander. "
                "NE PAS utiliser si le client n\\'a pas encore accepté le prix."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Adresse fournie par le client. Vide si on est en train de la demander."
                    },
                    "message": {
                        "type": "string",
                        "description": "Message naturel, ex: 'Parfait ! Donne-moi ton adresse de livraison ?' ou 'Noté, on livrera à cette adresse !'"
                    }
                },
                "required": ["message"]
            }
        }
    }
]

# Noms des tools reconnus (pour validation)
TOOL_NAMES = {t["function"]["name"] for t in TOOLS}
