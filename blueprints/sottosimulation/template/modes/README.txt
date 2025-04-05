# SOTTOSIMULATION MODES

Ce répertoire contient les définitions des différents modes de simulation :

MODES OPÉRATIONNELS :
- simulation_standard.txt  - Service restaurant normal
- simulation_rush.txt     - Périodes haute intensité
- simulation_urgence.txt  - Situations d'urgence

MODES FORMATION/TEST :
- simulation_formation.txt - Scénarios d'apprentissage
- simulation_debug.txt    - Tests et validation
- simulation_analysis.txt - Analyse performance
- simulation_calibration.txt - Calibration système

STRUCTURE DES FICHIERS :
Chaque fichier de mode définit :
1. CARACTÉRISTIQUES
   - Description du mode
   - Paramètres spécifiques
   - Conditions d'activation

2. COMPORTEMENTS SIMULÉS
   - Actions du personnel
   - Réactions des clients
   - Événements générés

3. MÉCANISMES DE TRANSITION
   - Conditions de transition
   - Modes accessibles
   - Procédures de changement

4. MÉTRIQUES ET VALIDATION
   - Indicateurs de performance
   - Critères de succès
   - Points de contrôle

UTILISATION :
- Les transitions entre modes sont gérées via map.json
- Chaque mode peut être activé manuellement ou automatiquement
- Les conditions de transition sont surveillées en continu
- Les métriques sont collectées pour analyse
