import os
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from zipfile import ZipFile
import shutil

REF_FILE_PATH = "/home/sara/Documents/GitHub/Pipeline/ref.csv"

def extract_zip(zip_file):
    """
    Extrait le contenu du zip dans un dossier nommé comme le zip
    """
    extract_directory = os.path.splitext(zip_file)[0]
    if os.path.exists(extract_directory):
        shutil.rmtree(extract_directory) #supprime le fichier zip déja téléchargé
    os.makedirs(extract_directory, exist_ok=True)  # créer le dossier s'il n'existe pas

    try:
        with ZipFile(zip_file, 'r') as zipf:
            zipf.extractall(path=extract_directory)  # Extraction dans le dossier
        print(f"Extraction reussie dans {extract_directory}")
        return extract_directory
    except FileNotFoundError:
        print(f"Fichier introuvable : {zip_file}")
    except Exception as e:
        print(f"Erreur lors de l'extraction : {e}")
        return None
    
def calcul_loss(folder_std, ref_file):
    """
    Calcule MAE et MSE entre les prédictions d'un dossier étudiant et un fichier de référence csv
    """

    try: 
        df_ref = pd.read_csv(ref_file, sep=';')
        df_ref.dropna(inplace=True)
    except FileNotFoundError: 
        print("le fichier de reference n'existe pas")
        return 
    except pd.errors.ParserError as e:
        print(f"erreur ")
        return 

    resultats = []

    
    nom_etudiant = os.path.basename(folder_std).split('_')[0].strip() 
  

    for file in os.listdir(folder_std):
        file_path = os.path.join(folder_std, file)
        if os.path.isdir(file_path):
            continue
        try:
            df_etu = pd.read_csv(file_path, sep= ';')
            if df_etu.shape[1] == 1:
                df_etu = pd.read_csv(file_path, sep=',', header=None)
        except Exception as e:
            print(f"erreur lors de la lecture du fichier {file_path}")
            continue #ignore pour l'instant

        if df_etu.shape[0] != df_ref.shape[0]:
            print(f"nombre de lignes incorrect dans {file_path} ({df_etu.shape[0]})")
            continue #ignore pour l'instant

        #Calcul metriques
        ligne = {"Nom étudiant": nom_etudiant, "Fichier": file}
        for index in [0,1,2]:
            num =f"prop{index+1}"
            col_etu = df_etu.iloc[:, index]
            col_ref = df_ref.iloc[:, index]

            ligne[f"{num}_mae"] = mean_absolute_error(col_ref, col_etu)
            ligne[f"{num}_mse"] = mean_squared_error(col_ref, col_etu)
        resultats.append(ligne)
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
    try:
        df_resultats = pd.DataFrame(resultats)
        df_resultats.to_csv("resultats.csv", index=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des résultats : {e}")

