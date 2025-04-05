# SottoSimulation Data Structure

Cette structure contient toutes les données nécessaires à la simulation.

## Organisation

### analysis/
Données d'analyse et métriques de performance
- responses.json : Suivi des réponses
- metrics.json : Métriques de performance
- improvements.json : Suggestions d'amélioration

### events/
Définition des événements par mode
- standard/ : Événements service normal
- rush/ : Événements période rush
- emergency/ : Événements urgence

### message_templates/
Templates de messages pour la simulation
- standard.json : Messages service standard

### simulation_profiles/
Profils des agents simulés
- staff.json : Profils personnel
- clients.json : Profils clients

### generation_rules/
Règles de génération comportements
- behavior_rules.json : Règles comportementales
