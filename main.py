# Ce script :
# 1) Se connecte automatiquement à UniversiTice via Firefox (avec selenium)
# 2) Scrape les mails des étudiants et les sauvegarde
# 3) Télécharge le fichier zip des dépots étudiants
# 4) Extrait le ZIP et calcule les MAE et MSE pour chaque fichier CSV soumis
# 5) Envoie un mail aux étudiants avec leurs résultats (si activé dans config.json)

import os
import time
import csv
import json
import glob
import hashlib
import pandas as pd
import smtplib
from zipfile import ZipFile
from email.mime.text import MIMEText
from sklearn.metrics import mean_absolute_error, mean_squared_error
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# chargement des variables d'environnement 
load_dotenv()

# Charger config JSON
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

SEND_MAILS = CONFIG.get("send_mails", True)
COURSE_NAME = CONFIG.get("course_name", "Bac à sable")
REF_FILE_PATH = CONFIG.get("ref_file")
DOWNLOAD_DIR = CONFIG.get("download_dir")
RESULTS_FILE = CONFIG.get("results_file")
EMAILS_FILE = CONFIG.get("emails_file")
EXTRACTION_DIR = os.path.join(DOWNLOAD_DIR, "depots_TP")

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
MODELES = ["GNN", "GCN", "GIT", "GAT", "GIN", "GRAPHSAGE"]


# Configure Firefox pour que les téléchargements aillent dans le bon dossier 
def setup_driver(download_dir):
    options = Options()
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", download_dir)
    options.set_preference("browser.download.useDownloadDir", True)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip,text/csv")
    options.set_preference("pdfjs.disabled", True)
    return webdriver.Firefox(service=Service("geckodriver"), options=options)

# Se connecte à universitice (identifiants dans .env)
def login(driver, wait):
    driver.get("https://universitice.univ-rouen.fr/")
    wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-login"))).click()
    wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn"))).click()
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(os.getenv("UNIV_USERNAME"))
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(os.getenv("UNIV_PASSWORD") + Keys.ENTER)
    time.sleep(3)

# va dans le menu et clique sur le nom du cours
def navigate_to_course(driver, wait, course_name):
    wait.until(EC.element_to_be_clickable((By.ID, "main-navigation1"))).click()
    wait.until(EC.element_to_be_clickable((By.ID, "main-navigation12"))).click()
    wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, course_name))).click()

# va dans Participants pour voir la liste des étudiants inscris au cours
def go_to_participants(driver, wait):
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Participants"))).click()

# Récupère tous les noms et emails dans le tableau des participants , écrit le fichier mails.csv
def scrape_and_save_emails(driver, wait, output_path=EMAILS_FILE):
    print("Scraping des participants...")
    time.sleep(3)
    rows = driver.find_elements(By.CSS_SELECTOR, "table#participants tbody tr")
    data = []
    for row in rows:
        try:
            a_tag = row.find_element(By.CSS_SELECTOR, "th.cell.c1 a")
            try:
                initials = a_tag.find_element(By.CLASS_NAME, "userinitials").text.strip()
            except:
                initials = ""
            full_text = a_tag.text.strip()
            nom = full_text[len(initials):].strip() if initials and full_text.startswith(initials) else full_text
            email = row.find_element(By.CSS_SELECTOR, "td.cell.c3").text.strip()
            data.append((nom, email))
        except:
            continue
    with open(output_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["nom_complet", "email"])
        writer.writerows(data)
    print(f"{len(data)} adresses email enregistrées dans {output_path}")

# Clique sur l'activité "Dépots fichier .csv" , clique sur travaux remix et télécharge tous les travaux
def download_depots(driver, wait):
    print("[INFO] Accès à l'activité Dépots fichier .csv...")
    try:
        wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Dépots fichier .csv"))).click()
        wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "travaux remis"))).click()
        wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Télécharger"))).click()
        print("[OK] Téléchargement lancé.")
    except Exception as e:
        print(f"[ERREUR] Échec du téléchargement : {e}")

# Trouve le fichier zip le plus récent téléchargé et l'extrait dans depots_TP
def get_latest_zip(download_dir):
    zips = glob.glob(os.path.join(download_dir, "*.zip"))
    return max(zips, key=os.path.getctime) if zips else None

# extrait le fichier zip le plus récent téléchargé dans depots_TP
def extract_zip(file):
    try:
        os.makedirs(EXTRACTION_DIR, exist_ok=True)
        with ZipFile(file, 'r') as zipf:
            zipf.extractall(EXTRACTION_DIR)
        print(f"Extraction réussie dans {EXTRACTION_DIR}")
        return EXTRACTION_DIR
    except Exception as e:
        print(f"Erreur : Extraction : {e}")
        return None

def send_email(receiver_email, subject, message):
    if not SEND_MAILS:
        print(f"Email désactivé : {subject} -> {receiver_email}")
        return
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = SENDER_EMAIL
            msg['To'] = receiver_email
            server.send_message(msg)
        print(f"Mail envoyé à {receiver_email}")
    except Exception as e:
        print(f"Envoi mail : {e}")

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

def check_csv_format(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lignes = f.readlines()
        df_ref = pd.read_csv(REF_FILE_PATH, sep=';')
        expected_lines = len(df_ref)
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
            if parts[3][1:-1].count(',') != 2:
                return False
        return True
    except:
        return False

# Lit résultats.csv
def load_previous_results():
    if os.path.exists(RESULTS_FILE):
        try:
            return pd.read_csv(RESULTS_FILE)
        except:
            pass
    return pd.DataFrame(columns=['nom_etudiant', 'modele', 'nom_fichier',
                                 'prop1_mae', 'prop1_mse', 'prop2_mae', 'prop2_mse', 'prop3_mae', 'prop3_mse', 'hash'])
# Lit mails.csv
def load_email_dict():
    try:
        df = pd.read_csv(EMAILS_FILE)
        df["nom_complet"] = df["nom_complet"].astype(str).str.strip().str.lower()
        return dict(zip(df["nom_complet"], df["email"].str.strip()))
    except:
        return {}

def calcul_loss(root, ref_file):
    if not os.path.exists(ref_file):
        print("Erreur : Fichier de référence introuvable.")
        return
    df_ref = pd.read_csv(ref_file, sep=';')
    prev = load_previous_results()
    updated = prev.copy()
    emails = load_email_dict()

    for folder in os.listdir(root):
        folder_path = os.path.join(root, folder)
        if not os.path.isdir(folder_path): continue

        nom_complet = folder.split('_')[0].strip()
        email = emails.get(nom_complet.lower())
        if not email:
            print(f"Erreur : mail introuvable pour {nom_complet}")
            continue

        for file in os.listdir(folder_path):
            path = os.path.join(folder_path, file)
            if not file.endswith(".csv"):
                send_email(email, "[Université] Mauvais format", f"Le fichier {file} n'est pas un CSV valide.")
                continue

            if not check_csv_format(path):
                send_email(email, "[Université] Format incorrect", f"Le fichier {file} a un format invalide.")
                continue

            modele = extract_modele_from_filename(file)
            if not modele:
                send_email(email, "[Université] Modèle manquant", f"Modèle non détecté dans {file}.")
                continue

            file_hash = hash_file(path)

            with open(path, 'r', encoding='utf-8') as f:
                n_lines = sum(1 for _ in f)
            header = None if n_lines == len(df_ref) else 0
            df_etu = pd.read_csv(path, sep=';', header=header)
            if header is None:
                df_etu.columns = ['prop1', 'prop2', 'prop3', 'allprop']

            try:
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
                    (updated['nom_fichier'] == file))]
                updated = pd.concat([updated, pd.DataFrame([result])], ignore_index=True)

                message = (f"Bonjour {nom_complet},\n\nVoici vos résultats pour {file} (modèle {modele}) :\n"
                           f"prop1 MAE : {mae1:.4f}, MSE : {mse1:.4f}\n"
                           f"prop2 MAE : {mae2:.4f}, MSE : {mse2:.4f}\n"
                           f"prop3 MAE : {mae3:.4f}, MSE : {mse3:.4f}\n\nCordialement,\nL’équipe pédagogique")
                send_email(email, "[Université] Résultats calculés", message)

            except Exception as e:
                send_email(email, "[Université] Erreur interne", f"Erreur lors du traitement de {file} : {e}")

    updated.to_csv(RESULTS_FILE, index=False)
    print(f"Résultats sauvegardés dans {RESULTS_FILE}")


if __name__ == "__main__":
    print("Lancement de la pipeline Selenium...")
    driver = setup_driver(DOWNLOAD_DIR)
    wait = WebDriverWait(driver, 10)

    try:
        login(driver, wait)
        navigate_to_course(driver, wait, COURSE_NAME)
        go_to_participants(driver, wait)
        scrape_and_save_emails(driver, wait)
        driver.back(); time.sleep(2)
        download_depots(driver, wait)
        time.sleep(10)
    finally:
        driver.quit()

    latest_zip = get_latest_zip(DOWNLOAD_DIR)
    if latest_zip:
        print(f"Fichier ZIP détecté : {latest_zip}")
        dossier = extract_zip(latest_zip)
        if dossier:
            calcul_loss(dossier, REF_FILE_PATH)
    else:
        print("Erreur : Aucun ZIP trouvé pour traitement.")
