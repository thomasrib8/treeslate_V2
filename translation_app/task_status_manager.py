import json
import os

# Définir le chemin du fichier pour stocker l'état de la tâche
STATUS_FILE = "task_status.json"

# Fonction pour charger l'état depuis le fichier
def load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as file:
            return json.load(file)
    else:
        # État initial par défaut
        return {"status": "idle", "message": "Aucune tâche en cours.", "output_file_name": None}

# Fonction pour enregistrer l'état dans le fichier
def save_status(status, message, output_file_name=None):
    task_status = {
        "status": status,
        "message": message,
        "output_file_name": output_file_name
    }
    with open(STATUS_FILE, "w") as file:
        json.dump(task_status, file)
    return task_status
