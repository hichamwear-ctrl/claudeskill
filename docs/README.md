# Documentation du projet

Sources de vérité du projet, par ordre de priorité selon le sujet.

| Document | Rôle | Prime sur |
|---|---|---|
| [`Architecture_Technique.md`](./Architecture_Technique.md) | Architecture technique v1.0 (stack, modèle de données cible, RLS, API, temps réel, sécurité, DevOps) | les **choix techniques** |
| [`SPEC_FONCTIONNELLE_V1.md`](./SPEC_FONCTIONNELLE_V1.md) | Spécification fonctionnelle V1 validée (catalogue, machine à états, tarification, paiement simulé, notifications, évolutivité) | les **règles métier** |

## Principes transverses (V1)

- **Démonstration** de bout en bout ; **paiement simulé** derrière l'interface
  `PaymentProvider` (Stripe branchable sans refonte).
- **Mono-intervenant**, attribution auto, acceptation immédiate — architecture
  multi-intervenant préservée.
- **Aucune règle métier codée en dur** : catalogue, tarifs, délais, textes,
  zones, horaires et seuils vivent en base et sont **administrables**.

## État du développement

- **Socle technique : livré et gelé** — voir [`../supabase/README.md`](../supabase/README.md).
- **Métier : non démarré** — plan d'étapes M1→M14 dans l'historique de décision ;
  démarrage à `M1 — Référentiel & zones` après validation de cette documentation.
