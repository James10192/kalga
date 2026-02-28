# Memory Injection — Règles d'implémentation

Règles dérivées de la recherche (2024-2025) sur les systèmes de mémoire LLM en production
(Mem0, LangChain, OpenAI sliding window, Anthropic context compaction, Factory.ai).

## Architecture mémoire dans Kalga

Trois couches de mémoire distinctes, chacune avec un rôle précis dans le prompt :

| Couche | Scope | Où injecter | Quand |
|--------|-------|------------|-------|
| **STM** (short-term) | Intra-session, compression des anciens messages | `user_message`, bloc 2 | Si `len(history) > COMPRESSION_THRESHOLD` (actuellement 12) |
| **LTM** (long-term) | Inter-sessions, faits sémantiques durables | Via épisodique | Lecture: à chaque tour (sauf 1er msg) |
| **Épisodique** | Inter-sessions, résumés de sessions passées | `user_message`, bloc 1 | Si client connu (faits ou résumés en DB) |

## Règle 1 — Placement dans le prompt

**La mémoire dynamique va dans le `user_message`, jamais dans le `system_prompt`.**

- `system_prompt` = instructions statiques (identité, brief produit, règles prix, guide outils)
- `user_message` = contexte dynamique per-tour (mémoire + historique + message actuel)

Référence : OpenAI community guidelines, Anthropic prompt engineering docs.

## Règle 2 — Ordre des blocs dans `user_message`

Ordre obligatoire (du plus ancien au plus récent) :

```
1. [MÉMOIRE CLIENT — SESSIONS PRÉCÉDENTES]   ← épisodique (LTM + sessions)
2. [RÉSUMÉ DES ÉCHANGES PRÉCÉDENTS]          ← STM summary (anciens msgs compressés)
3. [DERNIERS MESSAGES] ou CONVERSATION EN COURS:  ← STM recent (msgs verbatim)
4. Le client dit maintenant: "..."            ← message actuel
5. ÉTAT: ... | Offre actuelle: ...            ← contexte métier
```

Justification : le modèle reçoit le contexte du plus lointain au plus proche, ce qui correspond
à l'ordre chronologique naturel — pattern validé par Microsoft Surface Duo, Factory.ai, Mem0.

## Règle 3 — Blocs séparés, jamais fusionnés

Summary STM et messages récents = **deux blocs distincts avec labels différents**.

- Summary → `[RÉSUMÉ DES ÉCHANGES PRÉCÉDENTS]`
- Récents verbatim (quand STM actif) → `[DERNIERS MESSAGES]`
- Récents verbatim (pas de compression) → `CONVERSATION EN COURS:`

Ne jamais mettre le résumé et les messages bruts dans le même bloc sans séparateur.

Référence : LangChain `SummarizationMiddleware`, Factory.ai "anchored summary" pattern.

## Règle 4 — Condition d'activation STM

N'utiliser `stm_recent` (fenêtre compressée) que si `stm_summary is not None`.

```python
# BON
history_source = stm_recent if stm_summary is not None and stm_recent is not None \
    else conversation_history[-45:]

# MAUVAIS — on perdrait des messages si STM ne compresse pas
history_source = stm_recent or conversation_history[-45:]
```

Quand STM ne compresse pas (`stm_summary=None`), `stm_recent` = les 8 derniers seulement.
Utiliser `stm_recent` dans ce cas ferait perdre les messages entre 9 et 45.

## Règle 5 — Épisodique : jamais au premier message

```python
if not is_first_message and episodic_context:
    parts.append(episodic_context)
```

Le contexte épisodique ne s'injecte pas au premier message d'une session :
- Évite de surcharger le prompt d'introduction
- Le client n'a pas encore interagi — inutile de rappeler l'historique avant qu'il parle

## Règle 6 — Format des labels

Pour DeepSeek (et GPT-4) : `[UPPERCASE ENTRE CROCHETS]` — convention bien comprise.
Pour Claude : préférer les balises XML `<conversation_summary>`, `<recent_messages>`.

Ne pas utiliser de Markdown headers (`##`) dans les blocs mémoire injectés — ils peuvent
être interprétés comme des instructions plutôt que comme des données.

## Règle 7 — Extraction LTM (asynchrone)

L'extraction LTM doit toujours être `asyncio.create_task()` — non-bloquant.
Elle se déclenche quand `new_status in ("pending_delivery", "pending_pickup", "ended", "agreed")`.

Ne jamais attendre (`await`) l'extraction LTM dans le chemin critique de réponse.

## Fichiers concernés

- `kalga-api/app/services/ai/deepseek_client.py` — `build_agentic_messages()` : construction du prompt
- `kalga-api/app/services/ai/conversation_ai.py` — `generate_response()` : orchestration mémoire
- `kalga-api/app/services/ai/memory/stm.py` — compression intra-session
- `kalga-api/app/services/ai/memory/ltm.py` — extraction et persistence inter-sessions
- `kalga-api/app/services/ai/memory/episodic.py` — récupération contexte inter-sessions
