import os
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from zipfile import ZipFile
import shutil
import hashlib
import json
from emailer import send_email 
from dotenv import load_dotenv
from google_sheet import csv_to_google_sheet

load_dotenv()  
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

RESULTS_FILE = CONFIG["results_file"]
HASH_STORE_FILE = CONFIG["hash_file"]

def extract_zip(zip_file):
    extract_directory = os.path.splitext(zip_file)[0]
    if os.path.exists(extract_directory):
        shutil.rmtree(extract_directory)
    os.makedirs(extract_directory, exist_ok=True)

    try:
        with ZipFile(zip_file, 'r') as zipf:
            zipf.extractall(path=extract_directory)
        print(f"Extraction réussie dans {extract_directory}")
        return extract_directory
    except FileNotFoundError:
        print(f"Fichier introuvable : {zip_file}")
    except Exception as e:
        print(f"Erreur lors de l'extraction : {e}")
        return None

def calculate_hash(file_path, algorithm='sha256'):
    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def is_file_processed(folder_std, file):
    file_path = os.path.join(folder_std, file)
    hash_file = calculate_hash(file_path)
    if os.path.exists(HASH_STORE_FILE):
        df = pd.read_csv(HASH_STORE_FILE)
        processed_files = set(df['hashes']) 
    else:
        processed_files = set()
    return hash_file in processed_files

def mark_file_processed(folder_std, file):
    file_path = os.path.join(folder_std, file)
    hash_file = calculate_hash(file_path)
    if os.path.exists(HASH_STORE_FILE):
        df = pd.read_csv(HASH_STORE_FILE)
        processed_files = set(df['hashes'])  
    else:
        processed_files = set()
    if hash_file not in processed_files:
        processed_files.add(hash_file)
    df = pd.DataFrame(processed_files, columns=["hashes"])
    df.to_csv(HASH_STORE_FILE, index=False)

def calcul_loss(folder_std, ref_file):
    # lecture du fichier de reference
    try:
        df_ref = pd.read_csv(ref_file, sep=';')
        df_ref.dropna(inplace=True)
    except FileNotFoundError:
        print("Le fichier de référence est introuvable")
        return [], False
    except pd.errors.ParserError:
        print("Erreur lors de la lecture du fichier de référence")
        return [], False

    resultats = []
    nom_etudiant = os.path.basename(folder_std).split('_')[0].strip()
    has_new_valid_files = False

    for file in os.listdir(folder_std):
        file_path = os.path.join(folder_std, file)
        if is_file_processed(folder_std, file):
            print(f"Fichier {file} déjà traité")
            continue
        try:
            df_etu = pd.read_csv(file_path, sep=';')
            if df_etu.shape[1] == 1:
                df_etu = pd.read_csv(file_path, sep=',', header=None)
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier {file_path} : {e}")
            continue 
        if df_etu.shape[0] != df_ref.shape[0]:
            print(f"Nombre de lignes incorrect dans {file_path} ({df_etu.shape[0]})")
            continue 
        has_new_valid_files = True
        ligne = {"Nom étudiant": nom_etudiant, "Fichier": file}

        # metrique individuelle
        for i in range(3):
            y_true = df_ref.iloc[:, i]
            y_pred = df_etu.iloc[:, i]
            ligne[f"prop{i+1}_mae_"] = mean_absolute_error(y_true, y_pred)
            ligne[f"prop{i+1}_mse"] = mean_squared_error(y_true, y_pred)

        # multi-target
        for i in range(3):
            y_true = df_ref.iloc[:, i]
            y_pred = df_etu.iloc[:, i]
            ligne[f"prop{i+1}_mae_multi"] = mean_absolute_error(y_true, y_pred)
            ligne[f"prop{i+1}_mse_multi"] = mean_squared_error(y_true, y_pred)

    
        resultats.append(ligne)
        mark_file_processed(folder_std, file)
    return resultats, has_new_valid_files

def main(zip_path, ref_file, mail_path):
    folder = extract_zip(zip_path)
    if not folder:
        print("echec de l'extraction du fichier ZIP")
        return

    resultats = []
    emails_bons_format = set()
    emails_mauvais_format = set()
    emails_deja_traites = set()

    try:
        df_mails = pd.read_csv(mail_path)
        dict_mails = dict(zip(df_mails["Nom"].str.lower().str.strip(), df_mails["Email"]))
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier emails: {e}")
        return

    for folder_etu in os.listdir(folder):
        folder_etu_path = os.path.join(folder, folder_etu)
        if not os.path.isdir(folder_etu_path):
            continue
        nom_etu = folder_etu.split("_")[0].strip().lower()
        mail_etu = dict_mails.get(nom_etu)
        resultat_etu, has_new_valid_files = calcul_loss(folder_etu_path, ref_file)
        has_any_valid_file = has_new_valid_files or any(
            is_file_processed(folder_etu_path, f)
            for f in os.listdir(folder_etu_path)
            if not os.path.isdir(os.path.join(folder_etu_path, f))
        )
        if has_new_valid_files:
            resultats.extend(resultat_etu)
            emails_bons_format.add(mail_etu)
        elif not has_any_valid_file:
            emails_mauvais_format.add(mail_etu)
        else:
            emails_deja_traites.add(mail_etu)

    if resultats:
        try:
            df_resultats = pd.DataFrame(resultats)

            # la baseline 
            baseline = {
                "Nom étudiant": "Référence",
                "Fichier": "Baseline GCN",
                "prop1_mae_": 0.7756,
                "prop1_mse": 0.77,
                "prop2_mae_": 1.1361,
                "prop2_mse": 1.13,
                "prop3_mae_": 0.0078,
                "prop3_mse": 0.007,
                "prop1_mae_multi": 0.8628,
                "prop1_mse_multi": 0.86,
                "prop2_mae_multi": 1.0652,
                "prop2_mse_multi": 1.06,
                "prop3_mae_multi": 0.0129,
                "prop3_mse_multi": 0.012,
            }
            df_resultats = pd.concat([pd.DataFrame([baseline]), df_resultats], ignore_index=True)

            if os.path.exists(RESULTS_FILE):
                df_old = pd.read_csv(RESULTS_FILE)
                df_resultats = pd.concat([df_old, df_resultats], ignore_index=True)
            df_resultats.to_csv(RESULTS_FILE, index=False)
            print("résultat sauvegardé avec succès")
        except Exception as e:
            print(f"erreur lors de la sauvegarde des résultats{e}")
    else:
        print("aucun nouveau résultat à sauvegarder")

    #ENVOI DES MAILS D'AVERTISSEMENT 
    if emails_mauvais_format:
        print("Envoi des avertissements:")
        for email in emails_mauvais_format:
            try:
                subject = "DEPOT TP"
                message = "Bonjour,\nVeuillez déposer un fichier au bon format svp."
                send_email(email, subject, message)
                print(f"{email}")
            except Exception as e:
                print(f"echec pour {email}: {str(e)}")
    else:
        print("aucun avertissement à envoyer")

    sheet_link = csv_to_google_sheet(RESULTS_FILE)

    #ENVOI DU LIEN GOOGLE SHEET 
    if sheet_link and emails_bons_format:
        print("Envoi du lien Google Sheet aux étudiants avec bons fichiers")
        for email in emails_bons_format:
            try:
                subject = "Lien vers les résultats du TP"
                message = f"Bonjour,\n\nVoici le lien vers les résultats du TP :\n{sheet_link}\n\nCordialement"
                send_email(email, subject, message)
                print(f"Lien Google Sheet envoyé à {email}")
            except Exception as e:
                print(f"Erreur lors de l'envoi du lien à {email} : {e}")
