from downloader import UniversiticeDownloader
from selenium.webdriver.common.by import By
import time
import os
import loss
import csv


REF_FILE = "/home/sara/Documents/GitHub/Pipeline/ref.csv" #chemin du fichier csv référence
MAIL_PATH = "/home/sara/Documents/GitHub/Pipeline/mails.csv" 


def wait_for_download(download_dir, timeout=12):
    """ attend que le fichier soit compelètement téléchargé """
    end_time = time.time() + timeout
    while time.time() < end_time:
        files = os.listdir(download_dir)
        zip_files = [f for f in files if f.endswith('.zip')]
        crdownload_files = [f for f in files if f.endswith('.crdownload')]
        if zip_files and not crdownload_files:
            zip = max([os.path.join(download_dir, f) for f in zip_files], key=os.path.getmtime)
            return zip
        time.sleep(1)
    return None

if __name__ == "__main__":
    downloader = UniversiticeDownloader()
    try:
        downloader.login()
        downloader.navigate_to_course("Bac à sable")
        downloader.expand_section(by="xpath", value='//a[contains(@href, "view.php?id=1167786")]', section_plt="TEST Pipeline ")
        downloader._click_element(By.PARTIAL_LINK_TEXT, "travaux remis")
        downloader._click_element(By.PARTIAL_LINK_TEXT, "Télécharger")

        zip_path = wait_for_download(downloader.download_dir)
        if zip_path:
            print(f"Fichier ZIP téléchargé : {zip_path}")

            # extraction des mails
            downloader.get_email()
            loss.main(zip_path, REF_FILE, MAIL_PATH)

            #Suppression du fichier zip téléchargé    
            os.remove(zip_path)
        else:
            print("Aucun fichier zip trouvé")

    finally:
        downloader.close()
