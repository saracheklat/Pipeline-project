
# Pipeline d'extraction et d'évaluation automatique des travaux étudiants :mortar_board:


Ce projet permet d'automatiser le téléchargement des travaux remis par les étudiants sur Universitice, extraire le fichier de depot ZIP, calculer les métriques MAE (Mean Absolute Error) et MSE (Mean Squared Error) pour évaluer les prédictions des étudiants par rapport à une référence .

## Fonctionnalités principales

* Téléchargement automatique des travaux au format ZIP depuis Universitice via un bot Selenium

* Extraction du fichier ZIP avec suppression automatique des dossiers ancients

* Calcul des métriques MAE et MSE pour chaque fichier csv avec gestion des erreurs de lecture

* Gestion de l'historique des fichiers via hash pour éviter le retraitement des fichiers

* Sauvegarde des résultats dans un fichier CSV
  
* Envoie automatique des résultats par mail
## :closed_lock_with_key: Variables d'environnement


créez un fichier .env à la racine du projet et ajoutez ces variables d'environnement


`UNIV_USERNAME=votre_identifiant`
`UNIV_PASSWORD=ton_mot_de_passe`


## :wrench: Installation

```bash
  git clone https://github.com/Pipeline-project.git
  cd Pipeline-project
```

 créer et activer un environnement virtuel
```bash
  python -m venv venv
  source venv/bin/activate
``
  
### installer les dépendences
```bash
  pip install -r requirements.txt
  
```
    

## Configuration


Dans le fichier loss.py, personnalisez les chemins suivants :

    * REF_FILE_PATH : chemin du fichier csv de référence

    * HASH_STORE_FILE : fichier csv pour stocker les anciens hash

    * RESULTS_FILE : chemin du fichier csv de sauvegarde

Dans la classe UniversiticeDownloader (downloader.py), configurez :

    download_dir : dossier ou le fichier de depot ZIP sera téléchargé
    
## :alarm_clock: Automatisation avec cron

Vous planifier l'execution automatique du script avec cron 

ouvrir l'éditeur nano : 
```bash
    export EDITOR=nano
    export VISUAL=nano
    crontab -e
```
Ajouter la ligne suivante (execution tous les jours à 8h00):

```cron
    00 08 * * * /home/sara/miniconda3/bin/python3 /home/sara/Documents/GitHub/Pipeline/main.py >> /home/sara/Documents/GitHub/Pipeline/main.log 2>&1
```
## Requirements

```bash
pip install -r requirements.
```
## :arrow_forward: Execution

```bash
python main.py
```
Le script réalise les étapes suivantes : 

1. Connexion à Universitice 
2. Navigation vers le cour 
3. Téléchargement du fichier ZIP contenant les dossiers des étudiants
4. Extraction du fichier ZIP
5. :bar_chart: Calcul des métriques MAE et MSE par rapport à un fichier de référence 
6. Sauvegarde des résultats dans resultats.csv
7. Suppression du fichier ZIP téléchargé 

## Installation

```bash
git clone https://github.com/Pipeline-project.git

cd Pipeline-projectpython -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

## Structure du projet
Pipeline-project/
│
├── main.py                 # Script principal de téléchargement et d'évaluation
├── downloader.py           # Classe UniversiticeDownloader (bot Selenium)
├── loss.py                 # Fonctions d'extraction, calcul des métriques et gestion des hashes
├── .env                    # Fichier contenant les variables d'environnement
├── requirements.txt        # Dépendances Python
├── ref.csv                 # Fichier référence
├── resultats.csv           # Résultats des évaluations
└── hashes.csv              # Historique des hash des fichiers traités              


