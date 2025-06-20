# evaluator.py

import os
import time
import glob
import json
import hashlib
import pandas as pd
from zipfile import ZipFile
from sklearn.metrics import mean_absolute_error, mean_squared_error
from dotenv import load_dotenv

from scraper import run_scraping
from emailer import send_email
from google_sheet import update_google_sheet_from_csv 

# Chargement des configs
load_dotenv()
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

REF_FILE_PATH = CONFIG["ref_file"]
DOWNLOAD_DIR = CONFIG["download_dir"]
RESULTS_FILE = CONFIG["results_file"]
EMAILS_FILE = CONFIG["emails_file"]
EXTRACTION_DIR = os.path.join(DOWNLOAD_DIR, "depots_TP")
MODELES = ["GNN", "GCN", "GIT", "GAT", "GIN", "GRAPHSAGE"]

def get_latest_zip(download_dir):
    zips = glob.glob(os.path.join(download_dir, "*.zip"))
    return max(zips, key=os.path.getctime) if zips else None

def extract_zip(file):
    try:
        os.makedirs(EXTRACTION_DIR, exist_ok=True)
        with ZipFile(file, 'r') as zipf:
            zipf.extractall(EXTRACTION_DIR)
        print(f"[OK] Extraction dans {EXTRACTION_DIR}")
        return EXTRACTION_DIR
    except Exception as e:
        print(f"[ERREUR] Extraction ZIP : {e}")
        return None

def hash_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def extract_modele_from_filename(filename):
    upper = filename.upper()
    for m in MODELES:
        if m in upper:
            return m
    return None

def check_csv_format(file_path, expected_lines):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lignes = f.readlines()
        if len(lignes) not in [expected_lines, expected_lines + 1]:
            return False
        for ligne in lignes[1:]:
            if ligne.count(';') != 3:
                return False
            parts = ligne.strip().split(';')
            if len(parts) != 4:
                return False
            float(parts[0]); float(parts[1]); float(parts[2])
            if not (parts[3].startswith('[') and parts[3].endswith(']')):
                return False
        return True
    except:
        return False

def load_previous_results():
    if os.path.exists(RESULTS_FILE):
        try:
            return pd.read_csv(RESULTS_FILE)
        except:
            pass
    return pd.DataFrame(columns=[
        'nom_etudiant', 'modele', 'nom_fichier',
        'prop1_mae', 'prop1_mse',
        'prop2_mae', 'prop2_mse',
        'prop3_mae', 'prop3_mse',
        'hash'
    ])

def load_email_dict():
    try:
        df = pd.read_csv(EMAILS_FILE)
        df["nom_complet"] = df["nom_complet"].astype(str).str.strip().str.lower()
        return dict(zip(df["nom_complet"], df["email"].str.strip()))
    except:
        return {}

def calcul_loss(root, ref_file):
    if not os.path.exists(ref_file):
        print("[ERREUR] Fichier de référence manquant.")
        return
    df_ref = pd.read_csv(ref_file, sep=';')
    expected_lines = len(df_ref)

    prev = load_previous_results()
    updated = prev.copy()
    emails = load_email_dict()

    for folder in os.listdir(root):
        folder_path = os.path.join(root, folder)
        if not os.path.isdir(folder_path):
            continue

        nom_complet = folder.split('_')[0].strip()
        email = emails.get(nom_complet.lower())
        if not email:
            print(f"[WARN] Mail introuvable pour {nom_complet}")
            continue

        for file in os.listdir(folder_path):
            path = os.path.join(folder_path, file)
            if not file.endswith(".csv"):
                send_email(email, "[Université] Mauvais format", f"Le fichier {file} n'est pas un CSV valide.")
                continue

            if not check_csv_format(path, expected_lines):
                send_email(email, "[Université] Format incorrect", f"Le fichier {file} a un format invalide.")
                continue

            modele = extract_modele_from_filename(file)
            if not modele:
                send_email(email, "[Université] Modèle manquant", f"Modèle non détecté dans {file}.")
                continue

            file_hash = hash_file(path)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    n_lines = sum(1 for _ in f)
                header = None if n_lines == expected_lines else 0
                df_etu = pd.read_csv(path, sep=';', header=header)
                if header is None:
                    df_etu.columns = ['prop1', 'prop2', 'prop3', 'allprop']

                mae1 = mean_absolute_error(df_ref['prop1'], df_etu['prop1'])
                mse1 = mean_squared_error(df_ref['prop1'], df_etu['prop1'])
                mae2 = mean_absolute_error(df_ref['prop2'], df_etu['prop2'])
                mse2 = mean_squared_error(df_ref['prop2'], df_etu['prop2'])
                mae3 = mean_absolute_error(df_ref['prop3'], df_etu['prop3'])
                mse3 = mean_squared_error(df_ref['prop3'], df_etu['prop3'])

                result = {
                    'nom_etudiant': nom_complet,
                    'modele': modele,
                    'nom_fichier': file,
                    'prop1_mae': mae1, 'prop1_mse': mse1,
                    'prop2_mae': mae2, 'prop2_mse': mse2,
                    'prop3_mae': mae3, 'prop3_mse': mse3,
                    'hash': file_hash
                }

                updated = updated[~(
                    (updated['nom_etudiant'] == nom_complet) &
                    (updated['modele'] == modele) &
                    (updated['nom_fichier'] == file)
                )]
                updated = pd.concat([updated, pd.DataFrame([result])], ignore_index=True)

                message = (f"Bonjour {nom_complet},\n\nVoici vos résultats pour {file} (modèle {modele}) :\n"
                           f"prop1 MAE : {mae1:.4f}, MSE : {mse1:.4f}\n"
                           f"prop2 MAE : {mae2:.4f}, MSE : {mse2:.4f}\n"
                           f"prop3 MAE : {mae3:.4f}, MSE : {mse3:.4f}\n\nCordialement,\nL’équipe pédagogique")
                send_email(email, "[Université] Résultats calculés", message)

            except Exception as e:
                send_email(email, "[Université] Erreur interne", f"Erreur pendant le traitement de {file} : {e}")

    updated.to_csv(RESULTS_FILE, index=False)
    print(f"[OK] Résultats mis à jour : {RESULTS_FILE}")

if __name__ == "__main__":
    run_scraping()
    latest_zip = get_latest_zip(DOWNLOAD_DIR)
    if latest_zip:
        print(f"[INFO] ZIP détecté : {latest_zip}")
        dossier = extract_zip(latest_zip)
        if dossier:
            calcul_loss(dossier, REF_FILE_PATH)

    # Ajout de la mise à jour du Google Sheet
    update_google_sheet_from_csv()
