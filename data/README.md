# SOTTO Data Structure

Cette structure contient toutes les données nécessaires au fonctionnement de Sotto.

## Organisation

### service/
- tables.json : État actuel des tables
- orders.json : Commandes en cours
- status.json : Status global du service

### context/
- current_mode.json : Mode actuel et transitions
- active_adaptations.json : Adaptations actives

### restaurant/
- layout.json : Configuration spatiale
- equipment.json : Équipements disponibles
- staff.json : Personnel et rôles

### analytics/
- patterns.json : Patterns identifiés
- performance.json : Métriques de performance
- feedback.json : Retours et évaluations

### learning/
- restaurant_profile.json : Profil établissement
- adaptations.json : Adaptations apprises

## Usage
Ces fichiers sont automatiquement gérés par Sotto pour maintenir l'état du système et optimiser son fonctionnement.
