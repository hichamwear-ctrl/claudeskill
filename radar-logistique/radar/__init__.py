"""Radar de contrats logistiques.

Règle de conception n°1 — le filtre porte sur l'ACTIONNABILITÉ, jamais sur le
jugement. Une annonce n'est écartée que si un fait vérifiable établit qu'on ne
peut plus y répondre : échéance dépassée, marché déjà attribué, avis purement
informatif. « Est-ce une bonne affaire » reste la décision de l'exploitant.

Règle n°2 — les coûts d'erreur sont asymétriques. Rater un marché ouvert coûte
un contrat ; recevoir un marché clôturé coûte trente secondes. En cas de doute,
l'annonce est livrée et signalée.
"""
