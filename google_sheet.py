# google_sheet.py

import json
import os
import hashlib
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Charger la config
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

GOOGLE_SHEET_URL = CONFIG["google_sheet_url"]
RESULTS_FILE = CONFIG["results_file"]
HASH_FILE = RESULTS_FILE + ".hash"

def hash_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def update_google_sheet_from_csv():
    print("[INFO] Vérification des modifications de resultats.csv...")

    current_hash = hash_file(RESULTS_FILE)
    previous_hash = None

    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, 'r') as f:
            previous_hash = f.read().strip()

    if current_hash == previous_hash:
        print("[INFO] Aucun changement détecté dans resultats.csv. Aucune mise à jour du Sheet.")
        return

    print("[INFO] Changements détectés. Mise à jour du Google Sheet...")

    # Authentification
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    # Charger le CSV
    df = pd.read_csv(RESULTS_FILE)
    df = df.drop(columns=["hash"])


    # Ouvrir la feuille
    sheet = client.open_by_url(GOOGLE_SHEET_URL)
    worksheet = sheet.get_worksheet(0)  # première feuille

    # Effacer toutes les lignes à partir de A3 (on garde lignes 1 et 2)
    current_row_count = len(worksheet.get_all_values())
    if current_row_count > 2:
        worksheet.batch_clear([f"A3:Z{current_row_count}"])

    # Ajouter les nouvelles lignes à partir de A3
    worksheet.append_rows(df.values.tolist(), table_range="A3")

    # Sauvegarder le nouveau hash
    with open(HASH_FILE, 'w') as f:
        f.write(current_hash)

    print("Google Sheet mis à jour avec les nouveaux résultats.")
