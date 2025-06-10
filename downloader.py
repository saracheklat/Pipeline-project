import os
import time
from dotenv import load_dotenv
import pandas as pd
import csv
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

load_dotenv(dotenv_path='/home/sara/Documents/GitHub/Pipeline/.env')


class UniversiticeDownloader:
    def __init__(self):
        self.download_dir = "/home/sara/Documents/GitHub/Pipeline"  #le chemin du dossier de téléchargement
        self.driver = self._configure_driver()
        self.wait = WebDriverWait(self.driver, 10)

    def _configure_driver(self):
        # Options de Chrome
        options = Options()

        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        
        #options.add_argument("--headless=new") 
        options.add_experimental_option("prefs", prefs)
        return webdriver.Chrome( options=options)

    def login(self):
        self.driver.get("https://universitice.univ-rouen.fr/")
        time.sleep(5)
        self._click_element(By.CLASS_NAME, "btn-login")
        self._click_element(By.CLASS_NAME, "btn")
        time.sleep(5)
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        except TimeoutException:
            print("Champ username introuvable !")
        self._fill_input(By.ID, "username", os.getenv("UNIV_USERNAME"))
        self._fill_input(By.ID, "password", os.getenv("UNIV_PASSWORD") + Keys.ENTER)

    def navigate_to_course(self, course_name):
        self._hover_and_click(By.ID, "main-navigation1")
        self._hover_and_click(By.ID, "main-navigation12")
        self._click_element(By.PARTIAL_LINK_TEXT, course_name)

    def expand_section(self, by, value, section_plt):
        try:
            depot = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((by, value)))
            depot.click()
        except TimeoutException:
            self._click_element(By.PARTIAL_LINK_TEXT, section_plt)
            depot.click()

    def download_file(self, file_link_text):
        self._click_element(By.PARTIAL_LINK_TEXT, file_link_text)

    def _click_element(self, by, value):
        element = self.wait.until(EC.element_to_be_clickable((by, value)))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(1)  
        element.click()

    def _fill_input(self, by, value, text):
        element = self.wait.until(EC.element_to_be_clickable((by, value)))
        element.send_keys(text)

    def _hover_and_click(self, by, value):
        element = self.wait.until(EC.element_to_be_clickable((by, value)))
        ActionChains(self.driver).move_to_element(element).click().perform()

    def get_downloaded_zip_path(self):
        """
        Retourne le chemin complet du dernier fichier zip téléchargé
        """
        for file in os.listdir(self.download_dir):
            if file.endswith(".zip"):
                return os.path.join(self.download_dir, file) #chemin complet du fichier zip téléchargé
        return None
    
    def close(self):
        time.sleep(2)
        self.driver.quit()
    
    def get_email(self):
        time.sleep(2)
        rows = self.driver.find_elements(By.CSS_SELECTOR, "tr")
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

         
