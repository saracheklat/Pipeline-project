# emailer.py

import os
import json
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

SEND_MAILS = CONFIG.get("send_mails", True)
GOOGLE_SHEET_URL = CONFIG.get("google_sheet_url", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def send_email(receiver_email, subject, message):
    if not SEND_MAILS:
        print(f"MAIL OFF :  {subject} -> {receiver_email}")
        return
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            if GOOGLE_SHEET_URL:
                message += f"\n\nVous pouvez consulter tous les résultats ici : {GOOGLE_SHEET_URL}"
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = SENDER_EMAIL
            msg['To'] = receiver_email
            server.send_message(msg)
        print(f"[OK] Mail envoyé à {receiver_email}")
    except Exception as e:
        print(f"ERREUR : Envoi mail : {e}")
