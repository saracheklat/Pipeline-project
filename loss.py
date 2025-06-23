import os
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from zipfile import ZipFile
import shutil
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from google_sheets import csv_to_google_sheet

load_dotenv()  

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))  

REF_FILE_PATH = "/home/sara/Documents/GitHub/Pipeline/ref.csv"
HASH_STORE_FILE = "/home/sara/Documents/GitHub/Pipeline/hashes.csv"
RESULTS_FILE = "/home/sara/Documents/GitHub/Pipeline/resultats.csv"

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

def send_email(reciever_email):
    subject = "DEPOT TP"
    message = "Bonjour \n veillez deposer un fichier au bon format svp"
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        obj_mail = MIMEText(message)
        obj_mail['Subject'] = subject
        obj_mail['From'] = SENDER_EMAIL
        obj_mail['To'] = reciever_email
        server.send_message(obj_mail)
        server.quit()
        print(f"email envoyé à {reciever_email}")
    except smtplib.SMTPException as e:
        print(f"erreur lors de l'envoi du mail à  {reciever_email}: {e}")

def calcul_loss(folder_std, ref_file):
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
            print(f"Erreur lors de la lecture du fichier {file_path}")
            continue 
        if df_etu.shape[0] != df_ref.shape[0]:
            print(f"Nombre de lignes incorrect dans {file_path} ({df_etu.shape[0]})")
            continue 
        has_new_valid_files = True
        ligne = {"Nom étudiant": nom_etudiant, "Fichier": file}
        for index in [0, 1, 2]:
            num = f"prop{index + 1}"
            col_etu = df_etu.iloc[:, index]
            col_ref = df_ref.iloc[:, index]
            ligne[f"{num}_mae"] = mean_absolute_error(col_ref, col_etu)
            ligne[f"{num}_mse"] = mean_squared_error(col_ref, col_etu)
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
            if os.path.exists(RESULTS_FILE):
                df_old = pd.read_csv(RESULTS_FILE)
                df_resultats = pd.concat([df_old, df_resultats], ignore_index=True)
            df_resultats.to_csv(RESULTS_FILE, index=False)
            print("résultat sauvegardé avec succès")
        except Exception as e:
            print(f"erreur lors de la sauvegarde des résultats{e}")
    else:
        print("aucun nouveau résultat à sauvegarder")

    if emails_mauvais_format:
        print("Envoi des avertissements:")
        for email in emails_mauvais_format:
            try:
                send_email(email)
                print(f"{email}")
            except Exception as e:
                print(f"echec pour {email}: {str(e)}")
    else:
        print("aucun avertissement à envoyer")

    sheet_link = csv_to_google_sheet(RESULTS_FILE)

    if sheet_link and emails_bons_format:
        print("Envoi du lien Google Sheet aux étudiants avec bons fichiers...")
        for email in emails_bons_format:
            try:
                subject = "Lien vers les résultats du TP"
                body = f"Bonjour,\n\nVoici le lien vers les résultats du TP :\n{sheet_link}\n\nCordialement"
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                message = MIMEText(body)
                message["From"] = SENDER_EMAIL
                message["To"] = email
                message["Subject"] = subject
                server.send_message(message)
                server.quit()
                print(f"Lien Google Sheet envoyé à {email}")
            except Exception as e:
                print(f" Erreur lors de l'envoi du lien à {email} : {e}")
