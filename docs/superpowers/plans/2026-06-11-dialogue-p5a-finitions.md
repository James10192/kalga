# Refonte dialogue — Phase 5a : Finitions — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** v2 devient le moteur par défaut, et les capacités v1 restantes y sont portées : geste fidélité, mémoire client (LTM) dans la voix, réponse vocale aux vocaux, briefs resserrés (conclusion + catalogue).

**Architecture:** Aucun nouveau module — extensions ciblées de `engine`/`orchestrator`/`speech`/`deepseek_adapter` + branche v2 de `chat_service`. P5b (suppression de l'ancien moteur) suivra séparément.

**Spec :** `docs/superpowers/specs/2026-06-11-refonte-moteur-dialogue-design.md` §12 (P5) + dettes tracées des plans P4.x.

---

## Task 1: v2 par défaut

- `core/config.py` : `dialogue_engine: str = "v2"` (retour v1 = une ligne d'env).
- Test : `test_dialogue_engine_v2.py` — `test_v2_is_default()` : `Settings(dialogue_engine="v2")` par défaut — vérifier `app_settings.dialogue_engine == "v2"` sans monkeypatch... (l'env de test n'ayant pas DIALOGUE_ENGINE, lire `Settings()` frais). Les tests v1 existants gardent leur monkeypatch explicite.
- Commit : `feat(dialogue): v2 devient le moteur par défaut`

## Task 2: Geste fidélité porté en v2

- `orchestrator.run_pipeline(..., floor_override: Optional[float] = None)` → `floor_price = floor_override or effective_min/min`.
- `engine.respond(..., floor_override=None)` → propage.
- `chat_service` branche v2 : calcul du plancher effectif (formule v1, conversation_ai §ajustement fidélité) à partir de `negotiation_context` déjà disponible :
```python
            v2_floor = None
            if negotiation_context and negotiation_context.get('loyalty_discount', 0) > 0 \
                    and negotiation_context.get('is_returning'):
                base_min = product.get('effective_min_price') or product['min_price']
                price_range = product['price'] - base_min
                v2_floor = max(base_min - price_range * (negotiation_context['loyalty_discount'] / 100),
                               base_min * 0.95)
```
  passé à `dialogue_respond(..., floor_override=v2_floor)`.
- Tests : orchestrator avec `floor_override=17900` → une offre 17 900 est ACCEPTÉE (alors que min produit = 18 000) ; sans override → contre-offre.
- Commit : `feat(dialogue): geste fidélité porté en v2 (plancher ajusté client connu)`

## Task 3: Mémoire client (LTM) dans la voix

- `engine.respond(..., memory_extra: Optional[str] = None)` → `memory_block = (memory_extra + "\n" si fourni) + historique récent`.
- `chat_service` branche v2 : 3 premiers faits LTM :
```python
            v2_memory = None
            try:
                facts = await self.client_history.get_memory_facts(
                    merchant['id'], message.client_phone) or []
                lines = [f["fact"] for f in facts[:3] if f.get("fact")]
                if lines:
                    v2_memory = "Ce qu'on sait du client : " + " ; ".join(lines)
            except Exception:
                pass
```
- Test : `engine.respond` avec `memory_extra="client fidèle, aime le rouge"` + FakeLLM → `fake.speak_briefs[0]["memory"]` contient la phrase.
- Commit : `feat(dialogue): faits LTM injectés dans la voix v2`

## Task 4: Réponse vocale aux vocaux

- `chat_service` branche v2 : `use_voice = "[🎤 Vocal transcrit" in message.message` (le client a parlé → on lui répond en vocal ; la section TTS existante fait le reste).
- Test e2e : monkeypatch `app.services.tts_service.text_to_ogg` → `b"OGG"` ; message `"[🎤 Vocal transcrit (fr)]: c'est combien ?"` → `resp.audio_base64` non vide.
- Commit : `feat(dialogue): réponse vocale quand le client envoie un vocal (v2)`

## Task 5: Briefs resserrés (conclusion + catalogue)

- `speech.build_brief` : si `CONFIRM_DEAL` au plan → `brief["must"] = "Terminer par la question : livraison ou tu passes chercher ?"` ; si action catalogue → `brief["note"] = "Une liste exacte de produits sera ajoutée automatiquement après ton message — n'énumère AUCUN produit toi-même."`
- `deepseek_adapter.speak` : insérer `OBLIGATOIRE : {must}` et `NOTE : {note}` dans le prompt si présents.
- Tests : briefs contiennent must/note ; prompt adapter les transporte (StubDS).
- Commit : `fix(dialogue): brief verrouille la question de conclusion + cohérence catalogue`

## Task 6: Vérification + push

- Suite complète ≈ 295 verts + import app + spec §12 : P5 → « P5a ✅ (P5b : suppression v1 à venir) » + push.

## Notes P5b (séparé, destructif)

- Porter le chemin « message 100 % système » ([📸 recherche visuelle…]) en v2 avant de supprimer v1.
- Supprimer : `generate_response` (conversation_ai), `engine/` FSM, `deal_guard`, doublons `detectors` ; migrer leurs tests.
- Verrou par conversation côté API (le bridge sérialise déjà).
