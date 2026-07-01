# Documentation du projet

Sources de vérité du projet, par ordre de priorité selon le sujet.

| Document | Rôle | Prime sur |
|---|---|---|
| [`PRD.md`](./PRD.md) | Product Requirements : vision, personas, périmètre V1, exigences (F/NF), phasage | l'**intention produit** |
| [`Architecture_Technique.md`](./Architecture_Technique.md) | Architecture technique v1.0 (stack, modèle de données cible, RLS, API, temps réel, sécurité, DevOps) | les **choix techniques** |
| [`SPEC_FONCTIONNELLE_V1.md`](./SPEC_FONCTIONNELLE_V1.md) | Spécification fonctionnelle V1 validée (catalogue, machine à états, tarification, paiement simulé, notifications, évolutivité) | les **règles métier** |
| [`CONVERSATION_ENGINE.md`](./CONVERSATION_ENGINE.md) | **Cœur du produit** : moteur conversationnel piloté par la donnée (intentions, slots, contexte, multi‑services, IA↔opérateur) | le **dialogue & la collecte du besoin** |
| [`BUSINESS_RULES.md`](./BUSINESS_RULES.md) | Référence exhaustive des règles métier (validation opérateur, cas d'exploitation, décisions AUTO/OP/ADMIN) | les **règles métier détaillées** |
| [`DATA_MODEL.md`](./DATA_MODEL.md) | Modèle de données piloté par la donnée (tables cœur + config/règles/contenu, généricité, RLS, index, traçabilité) | le **modèle de données** |
| [`API_SPEC.md`](./API_SPEC.md) | Contrats d'API (PostgREST, RPC, Edge Functions, Realtime), autorisations, conventions | les **contrats d'API** |
| [`UX_SPEC.md`](./UX_SPEC.md) | Spécification UX / écrans V1 (écrans client/intervenant/admin, parcours, composants, cas d'erreur, états vides, règles UX) | l'**expérience & les écrans** |

## Principes transverses (V1)

- **Moteur de demandes (P0)** : l'utilisateur décrit son besoin en langage
  naturel ; le système le classe (IA + règles, piloté par la donnée) et pose des
  questions dynamiques. **Aucune liste de catégories** ; ajouter un métier =
  enrichir les données, jamais le code.
- **Contrôle humain obligatoire (v1.1)** : aucune mission n'est créée ni payée
  automatiquement. Toute demande passe par une **décision opérateur** (accepter /
  refuser / demander des infos) avant acceptation et avant tout paiement.
- **Démonstration** de bout en bout ; **paiement simulé** derrière l'interface
  `PaymentProvider` (Stripe branchable sans refonte), **débloqué après acceptation**.
- **Mono-intervenant**, attribution auto, acceptation immédiate — architecture
  multi-intervenant préservée.
- **Aucune règle métier codée en dur** : catalogue, tarifs, délais, textes,
  zones, horaires et seuils vivent en base et sont **administrables**.

## État du développement

- **Socle technique : livré et gelé** — voir [`../supabase/README.md`](../supabase/README.md).
- **Métier : non démarré** — plan d'étapes M1→M14 dans l'historique de décision ;
  démarrage à `M1 — Référentiel & zones` après validation de cette documentation.
