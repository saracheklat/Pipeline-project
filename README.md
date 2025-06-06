
# Pipeline d'extraction et d'évaluation automatique des travaux étudiants


Ce projet permet d'automatiser le téléchargement des travaux remis par les étudiants sur Universitice, extraire le fichier de depot ZIP, calculer les métriques MAE et MSE pour évaluer les prédictions soumises par rapport à une référence.
## Fonctionnalités principales

Téléchargement automatique : bot Selenium 

Extraction du fichier ZIP avec suppression des dossiers existants

Calcul des métriques MAE et MSE avec gestion des erreurs de lecture de fichiers csv

Gestion de l'historique des fichiers via hash pour éviter le retraitement

Sauvegarde des résultats dans un fichier CSV.
## Variables d'environnement


créez un fichier .env à la racine du projet et ajoutez ces variables d'environnement


`UNIV_USERNAME=votre_identifiant`
`UNIV_PASSWORD=ton_mot_de_passe`


## Installation

Install my-project with npm

```bash
  git clone https://github.com/Pipeline-project.git
  cd Pipeline-project
```

# créer et activer un environnement virtuel
  python -m venv venv
  source venv/bin/activate
  
# installer les dépen
  pip install -r requirements.txt
  
```
    





## Configuration


Dans le fichier loss.py, vous pouvez personnaliser les chemins suivants :

    REF_FILE_PATH : chemin du fichier référence

    HASH_STORE_FILE : fichier pour stocker les anciens hash

    RESULTS_FILE : chemin du fichier csv de sauvegarde

Dans UniversiticeDownloader, configurez :

    download_dir : dossier de téléchargement du ZIP.
## Automatisation avec cron

Vous planifier l'execution automatique su script avec cron

ouvrir l'éditeur nano
```bash
    export EDITOR=nano
    export VISUAL=nano
    crontab -e


```cron
    28 11 * * * /home/sara/miniconda3/bin/python3 /home/sara/Documents/GitHub/Pipeline/main.py >> /home/sara/Documents/GitHub/Pipeline/main.log 2>&1

## Requirements

pip install -r requirements.txt
## Execution

python main.py

Connexion à Universitice
Téléchargement automatique du fichier ZIP contenant les dossiers des étudiants
Calcul des métriques MAE et MSE par rapport à un fichier de référence
Sauvegarde des résultats dans resultats.csv
## Installation

git clone https://github.com/Pipeline-project.git

cd Pipeline-projectpython -m venv venv
source venv/bin/activate
pip install -r requirements.txt
