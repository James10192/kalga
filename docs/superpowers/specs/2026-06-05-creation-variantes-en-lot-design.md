# Création de variantes en lot — Design

**Date** : 2026-06-05
**Statut** : Implémenté (branche `feature/variantes-en-lot`, 32 tests verts)
**Périmètre** : `kalga-api` — module `merchant_commands` + nouveau module IA `color_detection`

---

## 1. Problème

Aujourd'hui, ajouter des variantes d'un produit se fait **strictement une par une** : pour chaque
variante il faut donner un nom, envoyer une photo, puis répondre « oui » pour continuer
(voir `handlers/variant_creation.py`). Pour un marchand qui vend un article décliné en **20 variantes
au même prix** (20 couleurs, 20 tailles, 20 modèles, 20 parfums…), ce flux est inutilisable :
40+ allers-retours WhatsApp.

**Objectif** : permettre de créer N variantes (jusqu'à ~30) partageant le **même prix** en une seule
opération, quel que soit le **type** de variante.

## 2. Insight clé

Deux besoins distincts sont mélangés dans la demande initiale :

1. **Créer vite plusieurs variantes au même prix** = création en lot. Facile, fiable, universel.
2. **« L'IA détecte la couleur »** = nommage automatique depuis une photo. Difficile, incertain,
   et **valable uniquement pour les variantes de type couleur**.

On résout (1) sans dépendre de (2). La détection couleur est une **assistance opportuniste** au
moment du nommage, jamais une autorité. Sa valeur **croît avec le volume** : pré-nommer 20 couleurs
puis valider d'un coup d'œil fait gagner un temps réel.

## 3. Périmètre

**Inclus**
- Création en lot par **liste texte** (mode A) — universel, tout type de variante.
- Création en lot par **lot de photos + nommage assisté** (mode B) — couleurs pré-suggérées par
  algorithme, autres types nommés à la main, dans une étape de validation unique.
- Commande autonome `variantes #K0xx ...` pour un produit existant (+ alias `couleurs`).
- Toutes les variantes partagent `price`, `min_price`, `description` du produit de base.

**Exclu (YAGNI)**
- Prix / prix minimum différent par variante.
- Stock initial par variante (réglé après via les commandes `stock` existantes).
- Détection fiable sur articles multicolores / à motifs (signalée, non garantie).
- Détection doré / argenté au pixel (limite physique assumée — voir §6).
- Modèle vision LLM (approche « C » — évolution future, §9).

## 4. Modèle de données

**Aucune migration de schéma.** Une variante est déjà une ligne `products` partageant un `group_id`
et portant un `variant_name` ; le nom complet est `"{nom_base} - {variant_name}"`
(cf. `handlers/variant_creation.py` et `product_repo.create`).

La création en lot insère N lignes avec le **même** `group_id`, `price`, `min_price`, `description`,
et un `variant_name` distinct par variante. La photo est soit celle du produit de base (mode A),
soit la photo envoyée pour chaque variante (mode B).

**Seul ajout persistance** : `ProductRepository.create_variants_batch(...)` qui insère les N variantes
dans **une seule transaction atomique**. Le code actuel (`product_repo.create`, lignes ~58-75)
recalcule `MAX(code)+1` et `commit` à **chaque** appel : appelé N fois en boucle, cela produit
N transactions et un risque de collision de code. La méthode batch calcule le prochain code **une
fois** puis incrémente, et garantit le tout-ou-rien.

## 5. Flux conversationnels

### Point d'entrée enrichi (`ASK_VARIANT`)

Après création du produit de base, l'étape propose trois chemins :

```
✅ Produit créé! Sac à main (#K012)

🎨 Tu as d'autres variantes (couleurs, tailles, modèles) ?
 • Tape la liste : ex. "rouge, bleu, noir"   → je les crée d'un coup (même prix)
 • Ou envoie les photos puis écris "fini"    → je détecte les couleurs si possible
 • Ou "non" pour terminer
```

Commande autonome pour un produit existant : `variantes #K012 XL, L, M` (alias `couleurs`).

### Mode A — liste texte (moteur universel)

```
Marchand : XL, L, M, S
Bot      : ✅ 4 variantes créées pour Maillot :
           • XL (#K013) • L (#K014) • M (#K015) • S (#K016)
           Toutes au même prix (15 000 F).
           💡 Pour changer la photo d'une variante : "modifier #K013"
```

Parsing : découpe sur virgules / retours à la ligne, `trim`, dédoublonnage, plafond ~30. Les
variantes héritent de la photo du produit de base. Aucune IA nécessaire — fonctionne pour tout type.

### Mode B — lot de photos + nommage assisté (états `VARIANT_BATCH_PHOTOS`, `VARIANT_BATCH_CONFIRM`)

```
Bot      : 📸 Envoie tes photos une par une, puis écris "fini".
Marchand : [photo][photo][photo]           ← bufferisées en silence (anti-ban)
Marchand : fini
Bot      : J'ai reçu 3 photos. Donne-moi le nom de chacune :
           1. Rouge   ✅  (couleur détectée)
           2. Bleu    ✅  (couleur détectée)
           3. ?           (à nommer)
           → "ok" pour valider, ou nomme/corrige : ex. "3=édition limitée, 1=bordeaux"
Marchand : 3=édition limitée
Bot      : ✅ 3 variantes créées avec photos : Rouge (#K013)…
```

- Chaque photo arrive comme un `MerchantMessage` séparé (`image_path`) → bufferisée côté serveur dans
  `session.data["batch_photos"]`. **Le bridge n'est pas modifié.**
- Pour chaque photo : `detect_color(bytes)` propose un nom + une confiance. Couleur sûre → pré-remplie ;
  sinon `?` à nommer.
- L'étape de validation gère aussi bien « tout pré-rempli » (couleurs) que « tout à nommer » (tailles,
  modèles). La détection n'est **jamais** l'autorité finale.

### Garde-fous transverses
- `annuler` à tout moment (déjà géré par `service._handle_creation_step`).
- Verrou de session existant (`session_manager.get_lock`) → protège le buffer des race conditions.
- Plafond ~30 variantes ; dédoublonnage des noms ; `fini` sans photo → on redemande.

## 6. Module de détection couleur — `services/ai/color_detection.py`

**Interface unique, pure, testable** (abstraction permettant de brancher un modèle vision plus tard) :

```python
@dataclass
class ColorGuess:
    name: str            # "bordeaux"
    confidence: float    # 0..1
    is_multicolor: bool
    reason: str          # trace debug

def detect_color(image_bytes: bytes) -> ColorGuess
```

**Pipeline (PIL + numpy uniquement — median-cut natif Pillow, pas de sklearn) :**

1. **Downscale** ~200 px (`thumbnail`) — couleur indépendante de la résolution ; calcul en
   millisecondes, CPU, bien moins coûteux que CLIP.
2. **Quantification median-cut** : `Image.quantize(colors=8, method=MEDIANCUT)` → 8 clusters + comptes.
3. **Suppression du fond** : échantillonnage des 4 coins pour estimer la couleur de fond ; on écarte
   les clusters proches du fond OU à la fois très clairs et très désaturés (papier, ombre) — **sauf**
   si tous les clusters sont achromatiques (vrai article blanc/noir/gris).
4. **Conversion sRGB → Lab** (formule standard D65, numpy déterministe). Le Lab reflète la perception
   humaine, pas le RGB.
5. **Classement** des clusters restants par `pixels × pondération de chroma` → cluster dominant.
6. **Nommage par ΔE2000 (CIEDE2000)** vers une palette FR d'ancres (~24 : rouge, bordeaux, rose,
   orange, jaune, moutarde, vert, kaki, turquoise, bleu, bleu marine, bleu ciel, violet, marron,
   camel, beige, taupe, noir, blanc, gris, doré, argenté…), chacune avec sa coordonnée Lab.

**Confiance** :
- `ΔE` vers l'ancre la plus proche : <~10 = sûr ; >~25 = `⚠️`.
- `dominance` = part du cluster dominant parmi les pixels non-fond.
- **Achromatique** : chroma très basse → nommage par la luminance (noir/gris/blanc).
- **Multicolore** : ≥2 clusters non-fond comparables et de teintes éloignées → `is_multicolor=True` + ⚠️.

**Limites connues (dette assumée)** :
- Doré / argenté = texture/reflets, non détectables au pixel → **toujours** confiance basse, laissés à
  la correction marchand.
- Articles à motifs / bicolores → `is_multicolor`, nommage non garanti.
- Choix CIEDE2000 (vs ΔE94 plus simple) retenu pour la précision sur ancres proches
  (rouge/bordeaux, beige/camel/taupe).

## 7. Composants & fichiers

| Composant | Type | Responsabilité unique | Connaît |
|---|---|---|---|
| `services/ai/color_detection.py` | **nouveau** | bytes → `ColorGuess` | rien du produit/session |
| `handlers/bulk_variant_creation.py` | **nouveau** | orchestration liste / lot photos / validation | session, flux |
| `ProductRepository.create_variants_batch` | **nouvelle méthode** | insertion N variantes atomique | DB |

**Fichiers modifiés** :
- `database/repositories/product_repo.py` → `create_variants_batch(...)`.
- `modules/merchant_commands/schemas.py` → +2 `CreationStep` (`VARIANT_BATCH_PHOTOS`,
  `VARIANT_BATCH_CONFIRM`), +1 `CommandAction` (`VARIANTS_BATCH_CREATED`).
- `handlers/product_creation.py` `_handle_ask_variant` → routage liste / `photos` / `oui` (legacy) / `non`.
- `modules/merchant_commands/service.py` → enregistrement des nouveaux steps vers le nouveau handler ;
  commande `variantes #K0xx ...` (regex calquée sur `variante`).
- `handlers/__init__.py` → export du nouveau handler.

`requirements.txt` : **inchangé** (Pillow + numpy déjà présents).
`session_manager.py` : **inchangé** (`ProductSession.data` est un dict, buffer dans
`data["batch_photos"]`).

Le nouveau handler utilise `ProductRepository` directement (recommandé pour le nouveau code) et
récupère le `group_id` via `db.generate_group_id()` (déjà utilisé ailleurs), pour rester cohérent.

## 8. Cas limites & erreurs

- Liste vide / que des stop-words → on redemande.
- > plafond (~30) → on prend les premières + avertissement explicite.
- Doublons de noms → dédoublonnés + avertissement.
- Photo illisible / `detect_color` échoue → nom « à préciser », confiance 0, ⚠️.
- Échec d'insertion → **rollback** de la transaction, rien créé, message clair.
- `fini` avec 0 photo → on redemande.
- Correction `3=beige` hors plage / mal formée → message d'aide, on redemande.
- Anti-ban : photos bufferisées **en silence** (un seul accusé sur la 1ʳᵉ), pas de réponse par photo.

## 9. Plan de tests

- `test_color_detection.py` — swatches unis générés en PIL → nom attendu ; **article rouge sur fond
  blanc → « rouge »** (test clé du filtrage de fond) ; noir/blanc/gris → achromatique ; bicolore →
  `is_multicolor` ; bytes corrompus → dégradé propre. Déterministe, zéro réseau.
- `test_product_repo_batch.py` — N lignes, codes séquentiels, champs partagés, **rollback** sur échec.
- `test_bulk_variants_handler.py` — simulation des steps mode A (parse liste) et mode B
  (buffer → récap → correction → création).

*La convention de tests exacte de `kalga-api` sera confirmée au moment du plan (dossier `tests/` à
localiser).* 

## 10. Évolution future (hors périmètre)

- **Approche C — modèle vision LLM** : `detect_color` étant une fonction pure à signature stable, on
  pourra remplacer son implémentation par un appel vision (DeepSeek-VL ou autre) sans toucher au
  reste — uniquement si la précision sur motifs/métallisés devient un besoin réel et que le coût est
  validé.
- Raccourci dédié `photo #K0xx` pour enrichir une variante (sucre syntaxique au-dessus du flux
  `modifier #K0xx` déjà existant).

---

## Sources (détection couleur)
- [Real-time Color Palette Extractor — K-means, LAB, ΔE2000 (DEV)](https://dev.to/ertugrulmutlu/real-time-image-color-palette-extractor-a-deep-dive-into-k-means-lab-and-de2000-4eoi)
- [Dominant Color Extraction: A Practical Guide (BVDART)](https://bvdart.nl/en/articles/dominant-color-extraction-in-practice)
- [Dominant Color Detection on Online Fashion Retrievals (Medium)](https://medium.com/@melih.kacaman/dominant-color-detection-on-online-fashion-retrievals-5fb1bc1ab763)
