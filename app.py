from flask import Flask, render_template, redirect, url_for, jsonify
from translation_app.routes import translation_bp
from calculator_app.routes import calculator_bp
import os
from flask_session import Session

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration des dossiers
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER

# Configuration de la clé secrète pour Flask
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change_me_for_production")

# Configuration des clés API pour DeepL et OpenAI
app.config["DEEPL_API_KEY"] = os.getenv("DEEPL_API_KEY", "")
app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

# Configuration Flask-Session (sessions côté serveur)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_session/"
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
Session(app)

# Enregistrement des blueprints
app.register_blueprint(translation_bp, url_prefix="/translation")
app.register_blueprint(calculator_bp, url_prefix="/calculator")

# État de la tâche global (remplacé par des sessions dans un vrai projet)
task_status = {"status": "idle", "message": "Aucune tâche en cours."}

@app.route("/")
def main_menu():
    """
    Menu principal avec deux boutons et tableau des fichiers traduits.
    """
    try:
        files = []
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
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
    Met à jour le statut de la tâche.
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
    # Port pour déploiement (par défaut 5000)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
