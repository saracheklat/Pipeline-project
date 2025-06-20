def csv_to_google_sheet(csv_path, sheet_name="CSV_to_google_sheet", creds_json='bright-lattice-461715-r8-0c383b5d8d9f.json'):
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    try:
        credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_json, scope)
        client = gspread.authorize(credentials)

        try:
            spreadsheet = client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(sheet_name)
            print("Nouveau Google sheet créé")

        spreadsheet.share(None, perm_type='anyone', role='reader')  # accessible à tous en lecture

        with open(csv_path, 'r', encoding='utf-8') as file_obj:
            content = file_obj.read() #lecture du csv

        if content:
            client.import_csv(spreadsheet.id, data=content) #importation du contenu du csv au gsheet
            print("résultat mis à jour dans le Google Sheet")
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}"
        else:
            print("Le fichier CSV est vide.")
            return None

    except Exception as e:
        print(f"erreur lors de l'import Google Sheet : {e}")
        return None
