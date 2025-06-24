import os
import time
import json
from scraper import run_scraping
from evaluator import main as evaluation_main

DOWNLOAD_DIR = "downloads"  



if __name__ == "__main__":
    print("[PIPELINE] Lancement du téléchargement ZIP et extraction des mails")
    zip_path = run_scraping()
    if not zip_path:
        print("erreur lors du téléchargement ZIP")
        exit(1)

    print(f"[PIPELINE] ZIP téléchargé avec succes : {zip_path}")
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    evaluation_main(zip_path, config["ref_file"], config["emails_file"])
    #suppression du ZIP
    try:
        os.remove(zip_path)
    except Exception as e:
        print(f"[ERREUR] erreur lors de la suppression de ZIP : {e}")
