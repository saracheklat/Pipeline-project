import os
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from zipfile import ZipFile
import shutil
import hashlib

REF_FILE_PATH = "/home/sara/Documents/GitHub/Pipeline/ref.csv"
HASH_STORE_FILE = "/home/sara/Documents/GitHub/Pipeline/hashes.csv"
RESULTS_FILE = "/home/sara/Documents/GitHub/Pipeline/resultats.csv"

def extract_zip(zip_file):
    """Extrait le contenu du zip dans un dossier nommé comme le zip"""
    extract_directory = os.path.splitext(zip_file)[0]
    if os.path.exists(extract_directory):
        shutil.rmtree(extract_directory)  # Supprime le dossier s'il existe déjà
    os.makedirs(extract_directory, exist_ok=True)  # Crée le dossier

    try:
        with ZipFile(zip_file, 'r') as zipf:
            zipf.extractall(path=extract_directory)  # Extraction dans le dossier
        print(f"Extraction réussie dans {extract_directory}")
        return extract_directory
    except FileNotFoundError:
        print(f"Fichier introuvable : {zip_file}")
    except Exception as e:
        print(f"Erreur lors de l'extraction : {e}")
        return None

def calculate_hash(file_path, algorithm='sha256'):
    """Calcule le hash d'un fichier"""
    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def is_file_processed(folder_std, file):
    """Vérifie si un fichier a déjà été traité en vérifiant son hash dans le CSV"""
    file_path = os.path.join(folder_std, file)
    hash_file = calculate_hash(file_path)

    # Charger les hashes déjà présents dans le fichier CSV
    if os.path.exists(HASH_STORE_FILE):
        df = pd.read_csv(HASH_STORE_FILE)
        processed_files = set(df['hashes'])  # Utilise un set pour les hashes existants
    else:
        processed_files = set()  # Si le fichier n'existe pas, on considère qu'aucun fichier n'est traité

    # Vérifie si le hash est déjà dans le set
    return hash_file in processed_files

def mark_file_processed(folder_std, file):
    """Marque un fichier comme traité en ajoutant son hash au CSV"""
    file_path = os.path.join(folder_std, file)
    hash_file = calculate_hash(file_path)

    # Charger les hashes déjà présents dans le fichier CSV
    if os.path.exists(HASH_STORE_FILE):
        df = pd.read_csv(HASH_STORE_FILE)
        processed_files = set(df['hashes'])  # Utilise un set pour les hashes existants
    else:
        processed_files = set()  # Si le fichier n'existe pas, on considère qu'aucun fichier n'est traité

    # Ajouter le hash au set
    if hash_file not in processed_files:
        processed_files.add(hash_file)

    # Sauvegarder les nouveaux hashes dans le fichier CSV
    df = pd.DataFrame(processed_files, columns=["hashes"])
    df.to_csv(HASH_STORE_FILE, index=False)

def calcul_loss(folder_std, ref_file):
    """
    Calcule MAE et MSE entre les prédictions d'un dossier étudiant et un fichier de référence CSV
    """

    try:
        df_ref = pd.read_csv(ref_file, sep=';')
        df_ref.dropna(inplace=True)
    except FileNotFoundError:
        print("Le fichier de référence n'existe pas")
        return
    except pd.errors.ParserError:
        print("Erreur lors de la lecture du fichier de référence")
        return

    resultats = []
    nom_etudiant = os.path.basename(folder_std).split('_')[0].strip()

    # Lister les fichiers dans le dossier étudiant
    for file in os.listdir(folder_std):
        file_path = os.path.join(folder_std, file)
        if os.path.isdir(file_path):
            continue

        # Si le fichier a déjà été traité, on le saute
        if is_file_processed(folder_std, file):
            print(f"Fichier {file} déjà traité")
            continue

        try:
            df_etu = pd.read_csv(file_path, sep=';')
            if df_etu.shape[1] == 1:
                df_etu = pd.read_csv(file_path, sep=',', header=None)
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier {file_path}")
            continue  # Ignore ce fichier

        if df_etu.shape[0] != df_ref.shape[0]:
            print(f"Nombre de lignes incorrect dans {file_path} ({df_etu.shape[0]})")
            continue  # Ignore ce fichier

        # Calcul des métriques MAE et MSE
        ligne = {"Nom étudiant": nom_etudiant, "Fichier": file}
        for index in [0, 1, 2]:
            num = f"prop{index + 1}"
            col_etu = df_etu.iloc[:, index]
            col_ref = df_ref.iloc[:, index]

            ligne[f"{num}_mae"] = mean_absolute_error(col_ref, col_etu)
            ligne[f"{num}_mse"] = mean_squared_error(col_ref, col_etu)
        resultats.append(ligne)

        # Marquer le fichier comme traité après calcul des métriques
        mark_file_processed(folder_std, file)

    return resultats

def main(zip_path, ref_file):
    folder = extract_zip(zip_path)
    resultats = []

    if folder:
        for folder_etu in os.listdir(folder):
            folder_etu_path = os.path.join(folder, folder_etu)
            if os.path.isdir(folder_etu_path):
                resultat_etu = calcul_loss(folder_etu_path, ref_file)
                if resultat_etu:
                    resultats.extend(resultat_etu)

    # Sauvegarder les résultats dans le fichier CSV
    try:
        if resultats:
            df_resultats = pd.DataFrame(resultats)
            # Lire les résultats existants
            if os.path.exists(RESULTS_FILE):
                df_old = pd.read_csv(RESULTS_FILE)
                df_resultats = pd.concat([df_old, df_resultats], ignore_index=True)
            df_resultats.to_csv(RESULTS_FILE, index=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des résultats : {e}")
