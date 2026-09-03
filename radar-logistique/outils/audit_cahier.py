#!/usr/bin/env python3
"""AUDIT DU CAHIER DES CHARGES — règle par règle, mécanisme par mécanisme.

« 253 tests, tous verts » ne veut rien dire. Le nombre de tests n'est pas
l'objectif. L'objectif est que le radar :

  · ne rate pas une occasion commerciale ;
  · ne transforme pas une hypothèse en fait ;
  · ne présente pas un marché fermé comme postulable ;
  · ne fasse jamais disparaître une opportunité en silence.

Cet audit rend donc quatre colonnes, pas un compteur :

    RÈGLE          ce qui est promis
    MÉCANISME      le code qui le tient — un module ET une fonction précise
    TEST           les comportements qui l'éprouvent
    ÉTAT           ✅ couvert · ⚠️ partiel · ❌ absent

Une règle sans mécanisme nommé est ❌ même si des tests passent : des tests
verts autour d'un code absent, c'est arrivé une fois avec les seize questions.
Une règle dont un seul test manque est ⚠️, jamais ✅ arrondi vers le haut.

    python3 outils/audit_cahier.py            # code non nul si une règle faiblit
    python3 outils/audit_cahier.py --detail   # ce qui manque, nommément
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# (règle, [module.symbole attendus], [fragments de noms de tests])
#
# La colonne MÉCANISME nomme des SYMBOLES, pas seulement des fichiers : un
# module qui existe mais dont la fonction a été renommée lors d'une réécriture
# ne doit pas passer pour couvert.
REGLES = [
    # ── le produit ────────────────────────────────────────────────────────
    ("le produit est un radar commercial, pas un lecteur de portails",
     ["chaine.Moteur.analyser", "adaptateur.vers_opportunite"],
     ["un_besoin_prive_trouve_par_un_moteur_de_recherche_est_une_opportunite",
      "une_page_d_entreprise_est_une_opportunite",
      "une_tournee_de_bourse_de_fret_est_une_opportunite"]),
    ("aucun capteur n'est indispensable",
     ["registre.Registre", "chaine.traiter"],
     ["sans_ted_le_radar_produit_toujours_un_resultat_commercial",
      "sans_google_le_radar_continue",
      "sans_aucune_source_publique_le_radar_continue",
      "une_seule_source_suffit_a_faire_tourner_le_moteur"]),
    ("aucun capteur ne domine le radar",
     ["rapport.construire"],
     ["aucune_source_ne_represente_plus_de_la_moitie_des_occasions",
      "plusieurs_sources_differentes_apparaissent_dans_capter"]),
    ("aucune priorité de source déclarée d'avance",
     ["registre.Rendement.priorite"],
     ["toutes_les_priorites_initiales_sont_non_mesurees",
      "source_non_consultee_n_a_pas_de_priorite"]),

    # ── les quatre dimensions ─────────────────────────────────────────────
    ("A · le type d'information ne décide pas seul de l'état",
     ["procedure.Vocabulaire.lire_type"],
     ["un_etat_explicite_bat_la_rubrique_du_portail",
      "une_rubrique_contredite_par_le_texte_suit_le_texte",
      "un_appel_a_projets_n_est_ni_postulable_ni_jete"]),
    ("B · huit états de procédure, normalisés",
     ["procedure.Etat", "procedure.lire"],
     ["date_depassee_sans_attribution_est_ferme_pas_attribue",
      "les_formulations_d_attribution_sont_comprises",
      "une_preinformation_va_dans_developper_et_surveille",
      "un_marche_infructueux_est_une_occasion_d_etre_connu"]),
    ("C · FAIT / SIGNAL / HYPOTHÈSE, sans prime au fait",
     ["nature.qualifier"],
     ["la_nature_ne_se_deduit_jamais_de_la_source",
      "la_nature_ne_change_pas_le_score",
      "on_ne_depose_pas_de_dossier_sur_une_hypothese"]),
    ("D · l'état pilote l'action, jamais le score",
     ["classification.classer", "score.Bareme.calculer"],
     ["l_etat_ne_change_pas_le_score",
      "un_etat_inconnu_donne_verifier_jamais_postuler",
      "ferme_va_dans_developper_et_dit_attribution_non_publiee"]),

    # ── comprendre, pas reconnaître ───────────────────────────────────────
    ("interprétation sémantique, indépendante de tout portail",
     ["procedure.interpreter_formulation", "procedure.MARQUEURS"],
     ["les_formulations_ouvertes_sont_comprises",
      "les_formulations_de_fermeture_sont_comprises",
      "le_module_ne_connait_aucun_portail"]),
    ("négations et formulations indirectes",
     ["procedure._nie", "procedure._porte"],
     ["les_negations_ne_sont_pas_ignorees",
      "une_attribution_annoncee_n_est_pas_une_attribution",
      "un_depot_logistique_n_est_pas_un_depot_d_offre",
      "une_selection_en_cours_n_est_ni_ouverte_ni_attribuee"]),
    ("FR / NL / EN / DE",
     ["procedure.MARQUEURS"],
     ["le_neerlandais_est_compris", "le_francais_est_compris",
      "l_anglais_et_l_allemand_sont_compris"]),
    ("INCONNU n'est jamais promu en POSTULABLE",
     ["procedure._trancher"],
     ["absence_totale_de_statut_donne_inconnu_jamais_postulable",
      "expression_non_interpretable_ne_devient_jamais_postulable",
      "une_expression_non_interpretable_ne_devient_jamais_postulable"]),
    ("un document ne conclut jamais sur la procédure",
     ["procedure.lire"],
     ["award_dans_un_document_annexe_ne_conclut_pas"]),

    # ── preuves et contradictions ─────────────────────────────────────────
    ("hiérarchie des preuves, configurable par source",
     ["procedure.RANGS_CONFIGURABLES", "procedure.Vocabulaire.rang"],
     ["la_hierarchie_est_configurable_par_source",
      "un_rang_inconnu_dans_la_configuration_est_refuse",
      "la_hierarchie_departage_quand_il_n_y_a_pas_de_conflit_fort"]),
    ("deux preuves fortes contradictoires = INCONNU",
     ["procedure._trancher"],
     ["statut_structuré_ouvert_contre_texte_ferme_donne_inconnu",
      "deux_preuves_de_meme_rang_contradictoires_donnent_inconnu"]),
    ("une date ne fabrique jamais un statut",
     ["procedure.lire", "procedure._seulement_temporel"],
     ["la_date_ne_bat_jamais_une_attribution",
      "date_depassee_sans_attribution_est_ferme_pas_attribue",
      "attribution_publiee_bat_une_ancienne_date_limite"]),

    # ── lots ──────────────────────────────────────────────────────────────
    ("chaque lot porte son propre état",
     ["lots.eclater", "lots.lots_de"],
     ["un_marche_attribue_avec_quatre_lots_donne_quatre_etats",
      "un_lot_attribue_dans_un_marche_ouvert_reste_attribue",
      "un_lot_encore_ouvert_dans_un_marche_attribue"]),
    ("lot par lot, et prestation ≠ fourniture",
     ["lots.eclater", "role.DetecteurDeRole"],
     ["seul_le_lot_compatible_est_notifie", "fourniture_et_livraison_de_poissons",
      "exigence_de_lot_est_lue_avec_la_carte_de_la_source"]),

    # ── fil de vie ────────────────────────────────────────────────────────
    ("une opportunité, un fil de vie",
     ["transitions.constater", "transitions.fil_de_vie"],
     ["trois_observations_donnent_une_opportunite_et_deux_transitions",
      "une_collecte_identique_ne_cree_aucun_evenement",
      "la_fiche_montre_le_fil_de_vie"]),
    ("les transitions déclenchent des actions commerciales",
     ["transitions.REGLES", "transitions.appliquer"],
     ["postulable_vers_ferme_annule_les_alertes_postuler_en_attente",
      "ferme_vers_attribue_bascule_en_developper_et_alerte",
      "annonce_vers_postulable_est_une_alerte_forte",
      "infructueux_vers_postulable_annonce_une_nouvelle_chance"]),
    ("une correction de lecture n'est pas un mouvement du marché",
     ["transitions.REVISION", "transitions.Transition.alerte"],
     ["une_correction_de_vocabulaire_ne_fait_pas_croire_a_un_changement",
      "une_transition_vers_inconnu_n_alerte_jamais"]),
    ("tout ce qui est recalculé est réécrit",
     ["chaine.RECALCULEES", "chaine._ecrire_opportunite"],
     ["moteur_et_action_sont_bien_recalcules"]),

    # ── vocabulaire ───────────────────────────────────────────────────────
    ("vocabulaire par source, jamais inventé, jamais propagé",
     ["procedure.memoriser", "procedure.vocabulaire_appris"],
     ["une_expression_inconnue_est_conservee_avec_son_contexte",
      "une_expression_apprise_ne_se_propage_pas_a_une_autre_source",
      "le_yaml_ecrit_a_la_main_prime_sur_la_memoire"]),
    ("vocabulaire versionné, révisable, traçable",
     ["procedure.reviser", "procedure.version_vocabulaire", "procedure.concerne"],
     ["chaque_revision_incremente_la_version",
      "une_revision_archive_l_ancienne_lecture_sans_l_effacer",
      "on_sait_quelles_fiches_dependent_d_une_expression",
      "la_langue_est_enregistree_jamais_devinee"]),

    # ── économie ──────────────────────────────────────────────────────────
    ("la source n'entre jamais dans le score",
     ["score.Bareme.calculer"],
     ["meme_economie_source_differente_score_identique",
      "meilleure_economie_source_differente_meilleur_score",
      "le_score_ne_depend_pas_de_la_source"]),
    ("fiabilité de l'information ≠ valeur économique",
     ["fiabilite.evaluer", "fiabilite.Niveau"],
     ["une_information_peu_fiable_garde_toute_sa_valeur_economique",
      "une_contradiction_fait_baisser_la_fiabilite_pas_le_score",
      "le_rapport_croise_fiabilite_et_score_sans_les_confondre"]),
    ("l'économie prime sur le montant",
     ["score.Bareme._marge", "score.Bareme._taille"],
     ["petit_contrat_recurrent_proche_bat", "marge_reste_non_mesuree"]),
    ("ma taille n'est jamais un rejet",
     ["capacite.Capacites", "classification.BLOCAGES_DE_TAILLE"],
     ["trop_gros_pour_moi_seul_donne_prospect", "aucun_de_ces_cas_n_est_un_rejet"]),
    ("🟣 six conditions, formation ≠ obligation légale",
     ["construction.evaluer"],
     ["metier_inconnu_avec_formation", "formation_n_efface_pas_une_obligation"]),
    ("aucun mot-clé manquant ne rejette",
     ["activite.Ontologie.analyser", "decouverte.Generateur"],
     ["metier_inconnu_n_est_jamais_rejete",
      "aucun_mot_cle_connu_ne_donne_jamais_un_rejet",
      "le_domaine_se_confirme_par_cpv_ou_par_vocabulaire"]),

    # ── intégrité ─────────────────────────────────────────────────────────
    ("DEMO et RÉEL structurellement séparés",
     ["mode.verifier", "mode.estampiller"],
     ["fixture_est_refusee_en_reel", "deux_modes_n_utilisent_jamais_la_meme_base",
      "aucune_fixture_n_entre_dans_le_flux_reel"]),
    ("livre de comptes, arrêt sur perte",
     ["comptes.Livre.verifier", "comptes.ReconciliationImpossible"],
     ["disparition_sans_motif_fait_echouer", "brutes_non_ventilees_font_echouer",
      "trajet_complet_ne_perd_aucune_ligne"]),
    ("déduplication à trois niveaux",
     ["deduplication.Index.rapprocher", "deduplication.Confiance"],
     ["sans_date_commune_reste_un_doublon_possible",
      "avec_meme_echeance_est_un_doublon_probable",
      "un_meme_besoin_vu_sur_trois_sources_garde_ses_trois_provenances"]),
    ("données manquantes jamais inventées",
     ["statut.parse_date", "adaptateur._nombre"],
     ["aucune_date_n_est_jamais_inventee", "montant_absent_n_est_jamais_invente",
      "nombre_illisible_est_signale_jamais_mis_a_zero"]),
    ("sources réellement consultées",
     ["registre.Etat", "registre.Source.consultee"],
     ["source_est_jamais_consultee_par_defaut",
      "une_source_jamais_consultee_est_nommee_pas_omise"]),
    ("jamais une boîte noire",
     ["questions.interroger", "fiche.Fiche.en_texte"],
     ["journal_repond_aux_seize_questions", "chaque_rejet_porte_son_motif",
      "la_fiabilite_est_affichee_avec_son_motif",
      "chaque_transition_conserve_sa_preuve_et_son_origine"]),
    ("le rapport montre les occasions avant les sources",
     ["rapport.Rapport._occasions"],
     ["les_occasions_passent_avant_les_statistiques_de_source",
      "le_rendement_est_observe_jamais_declare",
      "sans_opportunite_le_rapport_le_dit"]),
    ("une donnée réelle mal formée ne perd rien",
     ["adaptateur._nombre", "adaptateur._entier"],
     ["montant_publie_en_texte_ne_fait_pas_perdre_le_cycle",
      "trajet_complet_ne_perd_aucune_ligne"]),
    ("le cœur ignore les capteurs — vérifié par l'AST",
     ["chaine.Moteur", "modele.Opportunite"],
     ["aucun_module_du_coeur_n_importe_un_adaptateur",
      "aucun_nom_de_portail_dans_le_code_du_coeur"]),
    ("le même besoin par six capteurs donne le même résultat",
     ["chaine.Moteur.analyser"],
     ["meme_classification_economique", "meme_score", "meme_bilan_de_capacite",
      "une_seule_opportunite_apres_deduplication"]),
    ("retirer n'importe quel capteur ne casse rien",
     ["chaine.traiter"],
     ["retirer_n_importe_quel_capteur_ne_casse_rien",
      "sans_aucun_moteur_de_recherche_le_radar_produit_encore"]),
    ("symétrie public / privé, sans nomenclature publique",
     ["role.DetecteurDeRole.analyser", "deduplication.cpv_incompatible"],
     ["le_prive_dit_prestation_avec_ses_propres_mots",
      "un_cpv_absent_n_empeche_plus_la_fusion_certaine",
      "deux_cpv_de_familles_differentes_interdisent_encore_la_fusion",
      "un_resultat_brave_n_est_pas_etiquete_google"]),
    ("les quatre dimensions ne se mélangent jamais",
     ["nature.qualifier", "procedure.Lecture.etat_affiche"],
     ["hors_procedure_n_est_pas_un_signal",
      "le_rapport_range_les_signaux_par_nature_pas_par_etat",
      "un_besoin_exprime_directement_est_un_fait"]),
    ("le banc d'essai n'est pas en forme d'appel d'offres",
     ["chaine.Moteur.analyser"],
     ["le_banc_d_essai_n_est_plus_majoritairement_public",
      "chaque_famille_produit_au_moins_une_opportunite"]),
    ("douze familles de besoin, aucune indispensable",
     ["chaine.traiter"],
     ["le_radar_tourne_sans_aucune_famille_publique",
      "le_radar_tourne_sans_aucune_famille_privee",
      "retirer_n_importe_quelle_famille_ne_casse_rien"]),
    ("cent besoins d'un seul type suffisent au radar",
     ["rapport.construire"],
     ["cent_besoins_prives_produisent_un_radar_complet",
      "cent_appels_d_offres_produisent_un_radar_complet",
      "les_deux_lots_donnent_les_memes_scores"]),
    ("le même besoin sous six formes : capacité, économie et score identiques",
     ["chaine.Moteur.analyser", "score.Bareme.calculer"],
     ["capacite_identique", "economie_identique", "score_identique",
      "la_fiabilite_suit_les_PREUVES_pas_l_officialite"]),
    ("même économie, natures différentes : score et capacité identiques",
     ["chaine.Moteur.analyser"],
     ["le_score_est_identique", "la_valeur_economique_ligne_a_ligne_est_identique",
      "la_capacite_est_identique", "ce_qui_change_est_exactement_ce_qui_doit_changer"]),
    ("le score réagit vraiment à l'économie",
     ["score.Bareme.calculer"],
     ["chaque_variable_economique_a_un_effet_mesurable",
      "un_montant_hors_cible_fait_baisser_le_score",
      "une_exigence_hors_capacite_fait_baisser_le_score"]),
    ("l'adéquation mesure l'aptitude, pas la verbosité",
     ["score.Bareme.calculer", "activite.Correspondance"],
     ["un_intitule_precis_vaut_autant_qu_un_texte_bavard",
      "un_domaine_sans_specialite_vaut_moins_qu_un_metier_reconnu",
      "un_metier_etranger_ne_gagne_aucun_point_d_adequation"]),
    ("trois cas d'exigence, jamais confondus",
     ["score.Bareme.calculer"],
     ["les_trois_cas_d_exigence_sont_distincts",
      "une_exigence_juridiquement_inaccessible_annule_l_accessibilite"]),
    ("l'absence d'information n'est jamais un avantage",
     ["score.Bareme.calculer"],
     ["une_annonce_muette_ne_bat_pas_une_annonce_couverte",
      "le_demarrage_non_publie_n_est_pas_un_demarrage_immediat",
      "deux_opportunites_excellentes_plafonnent_ensemble"]),
    ("le rapport s'organise par famille de besoin",
     ["rapport.famille_de", "rapport.FAMILLES_ORDRE"],
     ["les_sept_familles_sont_toujours_affichees",
      "la_famille_se_lit_sur_le_besoin_pas_sur_la_source",
      "les_marches_publics_ne_sont_pas_la_famille_majoritaire"]),
    ("le rapport est un produit commercial, pas un compteur d'avis",
     ["rapport.Rapport._occasions"],
     ["le_rapport_porte_les_cinq_blocs_du_produit"]),
    ("sonder mesure ce que la chaîne traitera",
     ["sondage.sonder"],
     ["sonder_annonce_les_memes_categories_que_la_chaine",
      "sonder_compte_les_lots_pas_seulement_les_marches"]),
]


def _symboles_du_module(nom: str) -> set:
    chemin = RACINE / "radar" / f"{nom}.py"
    if not chemin.exists():
        return set()
    texte = chemin.read_text(encoding="utf-8")
    trouves = set(re.findall(r"^(?:class|def) (\w+)", texte, re.M))
    trouves |= set(re.findall(r"^    (?:async )?def (\w+)", texte, re.M))
    trouves |= set(re.findall(r"^(\w+) *[:=]", texte, re.M))
    return trouves


def _mecanisme_present(chemin: str) -> bool:
    """« module.Classe.methode » ou « module.fonction » — le symbole doit exister."""
    morceaux = chemin.split(".")
    symboles = _symboles_du_module(morceaux[0])
    if not symboles:
        return False
    return all(m in symboles for m in morceaux[1:])


def auditer(detail: bool = False) -> int:
    tests = (RACINE / "tests" / "test_radar.py").read_text(encoding="utf-8")
    noms = set(re.findall(r"def (test_\w+)", tests))

    lignes, trous, partiels = [], [], []
    for regle, mecanismes, fragments in REGLES:
        manquants = [m for m in mecanismes if not _mecanisme_present(m)]
        couverts = [f for f in fragments if any(f in t for t in noms)]
        absents = [f for f in fragments if f not in couverts]

        if manquants:
            etat = "❌ absent"
            trous.append((regle, manquants, absents))
        elif absents:
            etat = "⚠️ partiel"
            partiels.append((regle, [], absents))
        else:
            etat = "✅ couvert"
        lignes.append((regle, mecanismes[0], f"{len(couverts)}/{len(fragments)}", etat))

    largeur = max(len(l[0]) for l in lignes)
    print(f"{'RÈGLE':<{largeur}}  {'MÉCANISME':<34} {'TEST':>6}  ÉTAT")
    print("─" * (largeur + 54))
    for regle, meca, test, etat in lignes:
        print(f"{regle:<{largeur}}  {meca:<34} {test:>6}  {etat}")

    couvertes = sum(1 for l in lignes if l[3].startswith("✅"))
    print()
    print(f"{couvertes}/{len(REGLES)} règles couvertes · "
          f"{len(partiels)} partielle(s) · {len(trous)} absente(s)")

    if detail or trous or partiels:
        for titre, groupe in (("MÉCANISME ABSENT", trous),
                              ("TEST MANQUANT", partiels)):
            for regle, manquants, absents in groupe:
                print(f"\n{titre} — {regle}")
                for m in manquants:
                    print(f"   code   : {m} introuvable")
                for a in absents:
                    print(f"   test   : {a}")

    if trous or partiels:
        print("\nUne règle qui faiblit n'est pas rattrapée par le nombre de tests.")
        return 1
    print("\nChaque règle tient par un mécanisme NOMMÉ et par ses tests de")
    print("comportement. Le nombre de tests n'est pas l'objectif.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--detail", action="store_true")
    sys.exit(auditer(p.parse_args().detail))
