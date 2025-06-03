import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Définir les permissions nécessaires pour accéder à Google Sheets et Google Drive
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# Charger les informations d'identification du service
credentials = ServiceAccountCredentials.from_json_keyfile_name('bright-lattice-461715-r8-0c383b5d8d9f.json', scope)
client = gspread.authorize(credentials)

# Ouvrir le Google Sheet cible par son nom
spreadsheet = client.open('CSV-to-Google-Sheet')

# Lire le contenu du fichier CSV
with open('ref.csv', 'r') as file_obj:
    content = file_obj.read()

# Vérifie que le contenu du CSV est bien lu
print("Contenu du CSV:", content)

# Si le contenu est bien lu et contient des données
if content:
    # Importer le CSV dans le Google Sheet
    client.import_csv(spreadsheet.id, data=content)
else:
    print("Le fichier CSV est vide ou n'a pas pu être lu correctement.")
