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

load_dotenv()  

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))  




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
    """Marque un fichier comme traité"""
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


def send_email(reciever_email):
    subject = "DEPOT TP"
    message = "Bonjour \n" "veillez deposer un fichier au bon format svp"
    try : 
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() #securiser l'envoie des mail
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

def send_email_with_attachment(receiver_email, attachment_path):
    subject = "Résultats TP"
    body = "Bonjour,\n\nVeuillez trouver ci-joint vos résultats.\n\nCordialement"
    
    try:
        message = MIMEMultipart()
        message["From"] = SENDER_EMAIL
        message["To"] = receiver_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain"))

        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(attachment_path)}")
        message.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(message)
        server.quit()

        print(f"Mail avec pièce jointe envoyé à {receiver_email}")
    except Exception as e:
        print(f"Erreur envoi de mail à {receiver_email} : {e}")


def calcul_loss(folder_std, ref_file):
    """
    Calcule MAE et MSE entre les prédictions d'un dossier étudiant et un fichier de référence CSV
    """
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

    # Lister les fichiers dans le dossier étudiant
    for file in os.listdir(folder_std):
        file_path = os.path.join(folder_std, file)
        if os.path.isdir(file_path):
            continue

        # Si le fichier a déjà été traité, on passe au suivant
        if is_file_processed(folder_std, file):
            print(f"Fichier {file} déjà traité - aucun mail ne sera envoyé")
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

        # nouveau fichier valide
        has_new_valid_files = True

        # calcul des métriques MAE et MSE
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

    return resultats, has_new_valid_files

def main(zip_path, ref_file, mail_path):
    """
    Fonction principale pour le traitement des fichiers csv et l'envoi des emails
    """
    # Extraction de l'archive
    folder = extract_zip(zip_path)
    if not folder:
        print("echec de l'extraction du fichier ZIP")
        return

    resultats = []
    emails_bons_format = set()
    emails_mauvais_format = set()
    emails_deja_traites = set()

    # Chargement des emails des etudiants à partir du fichier CSV
    try:
        df_mails = pd.read_csv(mail_path)
        dict_mails = dict(zip(df_mails["Nom"].str.lower().str.strip(), df_mails["Email"]))
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier emails: {str(e)}")
        return

    # Traitement de chaque dossier étudiant
    for folder_etu in os.listdir(folder):
        folder_etu_path = os.path.join(folder, folder_etu)
        if not os.path.isdir(folder_etu_path):
            continue

        # Récupération email étudiant
        nom_etu = folder_etu.split("_")[0].strip().lower()
        mail_etu = dict_mails.get(nom_etu)
        

        # Calcul des métriques
        resultat_etu, has_new_valid_files = calcul_loss(folder_etu_path, ref_file)
        
        # Vérification des fichiers
        has_any_valid_file = has_new_valid_files or any(
            is_file_processed(folder_etu_path, f) 
            for f in os.listdir(folder_etu_path) 
            if not os.path.isdir(os.path.join(folder_etu_path, f))
        )
        
        # Classification des étudiants
        if has_new_valid_files:
            resultats.extend(resultat_etu)
            emails_bons_format.add(mail_etu)
        elif not has_any_valid_file:
            emails_mauvais_format.add(mail_etu)
        else:
            emails_deja_traites.add(mail_etu)

    # Sauvegarde des résultats
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

    # Envoi des résultats aux étudiants avec fichiers valides
    if emails_bons_format:
        print("envoi des résultats aux étudiants")
        for email in emails_bons_format:
            try:
                send_email_with_attachment(email, RESULTS_FILE)
                print(f"{email}")
            except Exception as e:
                print(f"echec pour {email}: {str(e)}")
    else:
        print("aucun étudiant avec nouveau fichier valide")

    # envoi de mail aux étudiants avec fichiers mal formatés
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