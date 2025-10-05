# Energy PDF Report

Ce composant personnalisé Home Assistant ajoute un service `energy_pdf_report.generate` permettant de générer un rapport PDF à partir des statistiques du tableau de bord Énergie. Le fichier PDF inclut une synthèse par catégorie ainsi qu'un détail de toutes les statistiques utilisées.

Le résumé met désormais en avant la consommation totale estimée (production + importations + décharge − exportations − charge) et la part non suivie, calculée en soustrayant la consommation des appareils suivis du total estimé.

## Installation rapide
1. Copier le dossier `energy_pdf_report` dans le répertoire `custom_components` de votre installation Home Assistant.
2. Redémarrer Home Assistant.
3. Depuis **Paramètres → Appareils et services → Ajouter une intégration**, sélectionner **Energy PDF Report** pour créer l'entrée de configuration.
4. Le service `energy_pdf_report.generate` devient alors disponible dans l'outil Développeur > Services et peut être utilisé dans vos automatisations.


## Paramètres du service
- `start_date` *(optionnel)* : date locale de début (format `YYYY-MM-DD`). Par défaut la période courante (jour, semaine ou mois) est utilisée. Les valeurs provenant d'objets `date`, `datetime` ou de chaînes de caractères sont automatiquement converties.
- `end_date` *(optionnel)* : date locale de fin (format `YYYY-MM-DD`). Si omis, la fin est déduite de la granularité. Les objets `datetime` sont convertis en date avant le traitement.

- `period` *(optionnel)* : granularité des statistiques (`day`, `week` ou `month`). Si omis, la valeur définie dans les options de l'intégration est appliquée (par défaut `day`).
- `filename` *(optionnel)* : nom du fichier PDF à générer (l'extension `.pdf` est ajoutée automatiquement si nécessaire). Si omis, le modèle défini dans les options de l'intégration est utilisé.
- `output_dir` *(optionnel)* : répertoire de sortie relatif au dossier de configuration ou chemin absolu. Par défaut, celui défini dans les options de l'intégration (initialement `www/energy_reports`).

- `dashboard` *(optionnel)* : identifiant ou nom du tableau de bord Énergie à analyser. Si omis, le tableau actif par défaut est utilisé.

- `co2_enabled` *(optionnel)* : booléen permettant d'activer ou de désactiver la section CO₂ pour cet appel. Si le paramètre est absent, la valeur configurée dans les options de l'intégration est utilisée.
- `price_enabled` *(optionnel)* : booléen permettant d'activer ou de désactiver la section coûts pour cet appel. Si le paramètre est absent, la valeur configurée dans les options de l'intégration est utilisée.

Le fichier généré est également signalé via une notification persistante dans Home Assistant, qui mentionne le tableau de bord utilisé lorsque ce paramètre est précisé.

> ℹ️ Le nombre de statistiques indiqué dans le rapport correspond simplement aux identifiants uniques présents dans vos préférences du tableau de bord Énergie. L'intégration n'impose aucune limite : toutes les statistiques disponibles sont prises en compte.

## Options de configuration

Depuis la page **Paramètres → Appareils et services**, ouvrez l'intégration **Energy PDF Report** puis choisissez **Options** pour personnaliser les valeurs par défaut suivantes :

- **Répertoire de sortie** : dossier utilisé pour stocker les rapports lorsqu'aucun répertoire n'est fourni au service.
- **Période par défaut** : granularité (`day`, `week`, `month`) appliquée si l'appel au service ne précise pas de période.
- **Modèle de nom de fichier** : patron utilisé pour générer automatiquement le nom du PDF lorsqu'aucun nom n'est fourni (variables disponibles : `{start}`, `{end}`, `{period}`, `{language}`).

Ces options sont immédiatement prises en compte lors du prochain appel au service, sans nécessiter de redémarrage de Home Assistant.


## Support Unicode

Le rapport PDF embarque la police DejaVu Sans (regular et bold) compressée dans
le code du composant. Lors de la génération, les fichiers TTF sont extraits dans
un répertoire temporaire, enregistrés auprès de FPDF puis immédiatement
nettoyés. Cette approche garantit l'affichage correct des caractères accentués
et des symboles internationaux sans nécessiter de fichiers binaires dans le
dépôt.

