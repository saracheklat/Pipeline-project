# scraper.py : 
# Ce script automatise la connexion à UniversiTice via Selenium, récupère les adresses emails des étudiants inscrits à un cours donné qu'il stocke dans un fichier .csv, 
# puis télécharge l'archive ZIP contenant leurs dépôts soumis sur l'activité "Dépots fichier .csv".


import os  # permet d'intéragir avec le système de fichiers et les variables d'environnement 
import time # Fournit des fonctions pour manipuler le temps (délai, pause)
import csv # Sert à lire et écrire des fichier csv (utilisé dans ce script pour écrire mails.csv)
import json # Permet de lire et manipuler des fichiers JSON (utilisé ici pour lire le fichier config.json contenant des parmaètres...)

# dotenv permet de charger des variables d'environnement depuis un fichier .env 
# load_dotenv "charge" les variables d'environnement pour qu'elle soient accessibles via os.getenv(...)
from dotenv import load_dotenv 

# SELENIUM - AUTOMATISATION DU NAVIGATEUR 
from selenium import webdriver # importe l'objet principal permettant de controler un navigateur (ici firefox), on crée ici un webdriver.Firefox(...)
from selenium.webdriver.firefox.options import Options # Permet de personnaliser FireFox avant de le lancer 
from selenium.webdriver.firefox.service import Service # Sert à définir le chemin vers le binaire de geckodriver (le serveur qui pilote Firefox)
from selenium.webdriver.common.by import By # Définit la manière dont selenium localise un élément sur une page (By.ID, By.CLASS_NAME,...)
from selenium.webdriver.common.keys import Keys # Permet de simuler l'appui sur une touche du clavier (keys.ENTER...)
from selenium.webdriver.support.ui import WebDriverWait # Permet de créer une attente active jusqu'à ce qu'un élément apparaisse
from selenium.webdriver.support import expected_conditions as EC # Fournit les conditions pratiques à utiliser avec WebDriverWait 
from selenium.common.exceptions import TimeoutException

# - Appelle la fonction load_dotenv() fournie par dotenv
# - Lit automatiquement un fichier .env situé dans le répertoire courant
# - Toutes les variables définies dans .env sont injectées dans l'environnement du script
load_dotenv()

# OUverture (puis fermeture à la fin du bloc 'with' du fichier config.json)
with open("config.json", "r", encoding="utf-8") as f: 
    CONFIG = json.load(f)  #load convertit le contenu json en un dictionnaire Python stocké dans CONFIG 

DOWNLOAD_DIR = CONFIG["download_dir"]  # Sert à indiquer à firefox ou enregistrer les fichiers téléchargés automatiquement
COURSE_NAME = CONFIG["course_name"]    # Sert à naviguer vers le bon cours sur UniversiTice 
EMAILS_FILE = CONFIG["emails_file"]    # Indique le fichier de sortie dans lequel on va sauvegarder la liste des noms + mails des étudiants 


def wait_for_download(download_dir, timeout=30):
    """Attend que le fichier ZIP soit complètement téléchargé."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        files = os.listdir(download_dir)
        zip_files = [f for f in files if f.endswith('.zip')]
        crdownload_files = [f for f in files if f.endswith('.crdownload')]
        if zip_files and not crdownload_files:
            # prend le dernier zip
            zip_path = max([os.path.join(download_dir, f) for f in zip_files], key=os.path.getmtime)
            return zip_path
        time.sleep(1)
    return None

# Configuration de Firefox avec des options spécifiques , lancement d'une instance de Firefox controlée par selenium , retour du pilote (driver)
def setup_driver(download_dir):
    options = Options()  # création d'un objet Options qui permet de personnaliser le comportement de Firefox 
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", download_dir)
    options.set_preference("browser.download.useDownloadDir", True)  # Firefox utilise automatiquement le dossier défini (download_dir) sans demander 
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip,text/csv")
    options.set_preference("pdfjs.disabled", True)  #désactive l'ouverture automatique des PDF dans Firefox 
    return webdriver.Firefox(service=Service("geckodriver"), options=options)

# Connexion à universitice avec les identifiants définis dans .env
# paramètres : 
# - driver : l'objet Firefox Webdriver controlé par selenium
# - wait : un objet WebDriverWait qui permet d'attendre que certains éléments soient visibles ou cliquables  
def login(driver, wait):
    driver.get("https://universitice.univ-rouen.fr/")
    time.sleep(5)
    wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-login"))).click()
    wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn"))).click()
    time.sleep(5)
    try:
        wait.until(EC.presence_of_element_located((By.ID, "username")))
    except TimeoutException:
        print("Champ username introuvable !")
    driver.find_element(By.ID, "username").send_keys(os.getenv("UNIV_USERNAME"))
    driver.find_element(By.ID, "password").send_keys(os.getenv("UNIV_PASSWORD") + Keys.ENTER)


def navigate_to_course(driver, wait, course_name):
    wait.until(EC.element_to_be_clickable((By.ID, "main-navigation1"))).click()
    wait.until(EC.element_to_be_clickable((By.ID, "main-navigation12"))).click()
    wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, course_name))).click()

def go_to_participants(driver, wait):
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Participants"))).click()

def get_email(driver, wait):
        time.sleep(2)
        rows = driver.find_elements(By.CSS_SELECTOR, "tr")
        data = []

        for i, row in enumerate(rows):
            tds = row.find_elements(By.TAG_NAME, "td")

            #  filtre les lignes qui n'ont pas les bonnes colonnes
            classes_td = [td.get_attribute("class") for td in tds]
            if not any("cell c2" in td_class for td_class in classes_td):
                continue

            try:
                nom = row.find_element(By.CSS_SELECTOR, "td.cell.c2").text.strip()
                email = row.find_element(By.CSS_SELECTOR, "td.cell.c4.email").text.strip()
                data.append((nom, email))
            except Exception as e:
                print(f"Erreur à la ligne {i} : {e}")

        # Sauvegarde dans un fichier CSV 
        output_path = "mails.csv"
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Nom", "Email"])
            writer.writerows(data)

        print(f"mails sauvegardés avec succès dans : {output_path}")


def download_depots(driver, wait, download_dir):
    print("Accès à l'activité Dépots fichier .csv...")
    try:
        wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Dépots fichier .csv"))).click()
        wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "travaux remis"))).click()
        print("Téléchargement lancé.")
        wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Télécharger"))).click()
        # Utilise ici la fonction d’attente !
        zip_path = wait_for_download(download_dir, timeout=60)
        return zip_path
    except Exception as e:
        print(f"ERREUR : Échec du téléchargement : {e}")
        return None

def run_scraping():
    driver = setup_driver(DOWNLOAD_DIR)
    wait = WebDriverWait(driver, 13)
    zip_path = None
    try:
        login(driver, wait)
        navigate_to_course(driver, wait, COURSE_NAME)
        zip_path = download_depots(driver, wait, DOWNLOAD_DIR)
        get_email(driver, wait)
        time.sleep(2)
    except Exception as e:
        print(e)
    driver.quit()
    return zip_path
