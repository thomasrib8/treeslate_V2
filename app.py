from flask import Flask, render_template, jsonify
from flask_session import Session
from translation_app.routes import translation_bp
from calculator_app.routes import calculator_bp
import os
from config import DevelopmentConfig

# Initialisation de l'application Flask
app = Flask(__name__)

# Charger la configuration depuis config.py
app.config.from_object(DevelopmentConfig)

# Créer les dossiers nécessaires si non existants
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["DOWNLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

# Initialiser Flask-Session
if app.config.get("SESSION_TYPE") == "filesystem":
    Session(app)

# Enregistrer les blueprints
app.register_blueprint(translation_bp, url_prefix="/translation")
app.register_blueprint(calculator_bp, url_prefix="/calculator")

# État global de la tâche (remplacé par des sessions dans les blueprints)
task_status = {"status": "idle", "message": "Aucune tâche en cours."}

@app.route("/")
def main_menu():
    """
    Menu principal avec deux boutons et un tableau listant les fichiers traduits.
    """
    try:
        files = []
        for filename in os.listdir(app.config["DOWNLOAD_FOLDER"]):
            filepath = os.path.join(app.config["DOWNLOAD_FOLDER"], filename)
            if os.path.isfile(filepath):
                files.append({
                    "name": filename,
                    "path": filepath,
                    "creation_date": os.path.getctime(filepath),
                })
        # Trier les fichiers par date de création (du plus récent au plus ancien)
        files.sort(key=lambda x: x["creation_date"], reverse=True)
    except Exception as e:
        files = []
        app.logger.error(f"Erreur lors du chargement des fichiers : {e}")

    return render_template("main_menu.html", files=files)

@app.route('/check_status', methods=['GET'])
def check_status():
    """
    Retourne le statut actuel de la tâche.
    """
    global task_status
    return jsonify(task_status)

@app.route('/set_status/<string:status>', methods=['POST'])
def set_status(status):
    """
    Met à jour le statut global de la tâche.
    """
    global task_status
    if status in ["done", "processing", "idle", "error"]:
        task_status["status"] = status
        task_status["message"] = {
            "done": "Traduction terminée.",
            "processing": "Traitement en cours.",
            "idle": "Aucune tâche en cours.",
            "error": "Une erreur est survenue."
        }.get(status, "Statut inconnu.")
        return jsonify({"message": "Statut mis à jour avec succès."})
    return jsonify({"message": "Statut invalide."}), 400

if __name__ == "__main__":
    # Définir le port pour le déploiement
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=app.config.get("DEBUG", False), host="0.0.0.0", port=port)
