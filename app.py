from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, current_app
from flask_httpauth import HTTPBasicAuth
import os
import threading
import logging
from translation_app.utils import translate_docx_with_deepl
from translation_app.routes import translation_bp
from calculator_app.routes import calculator_bp
from datetime import datetime
from config import DevelopmentConfig
from marketing_app.routes import marketing_bp

# Initialisation de l'application Flask
app = Flask(__name__)
auth = HTTPBasicAuth()

# Exemple d'utilisateurs autorisés
users = {
    "admin": "Roue2021*",
    "thomas": "Roue2021*",
    "florian": "Roue2021*",
    "victor": "Roue2021*"
}

# Charger la configuration depuis config.py
app.config.from_object(DevelopmentConfig)

# Configuration des logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Créer les dossiers nécessaires si non existants
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["DOWNLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["MARKETING_FOLDER"], exist_ok=True)
os.makedirs(app.config["DEEPL_GLOSSARY_FOLDER"], exist_ok=True)
os.makedirs(app.config["GPT_GLOSSARY_FOLDER"], exist_ok=True)

# Enregistrer les blueprints
app.register_blueprint(translation_bp, url_prefix="/translation")
app.register_blueprint(calculator_bp, url_prefix="/calculator")
app.register_blueprint(marketing_bp, url_prefix="/marketing")

# Dictionnaire pour suivre le statut des tâches
task_status = {
    "status": "idle",
    "message": "Aucune tâche en cours.",
    "output_file_name": None
}

def set_task_status(status, message, output_file_name=None):
    """
    Met à jour le statut global de la tâche.
    """
    task_status["status"] = status
    task_status["message"] = message
    task_status["output_file_name"] = output_file_name
    logger.info(f"Statut mis à jour : {task_status}")

def start_translation_process(input_file_path, output_file_path):
    """
    Fonction de traitement en arrière-plan pour la traduction.
    Utilisation correcte du contexte Flask.
    """
    app_context = app.app_context()
    app_context.push()
    try:
        set_task_status("processing", "Traduction en cours...")

        if not os.path.exists(input_file_path):
            raise FileNotFoundError(f"Le fichier {input_file_path} est introuvable.")

        translate_docx_with_deepl(
            api_key=current_app.config["DEEPL_API_KEY"],
            input_file_path=input_file_path,
            output_file_path=output_file_path,
            target_language="EN"
        )

        set_task_status("done", "Traduction terminée.", os.path.basename(output_file_path))
        logger.info("Traduction terminée avec succès.")
    except Exception as e:
        set_task_status("error", f"Erreur lors du traitement : {str(e)}")
        logger.error(f"Erreur dans le traitement : {e}")
    finally:
        app_context.pop()

# Fonction d'authentification
@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username
    return None

@app.route('/')
@auth.login_required
def main_menu():
    translated_files = []
    marketing_files = []
    download_folder = current_app.config.get("DOWNLOAD_FOLDER")
    marketing_folder = app.config["MARKETING_FOLDER"]

    # Fichiers pour la traduction
    if os.path.exists(download_folder):
        for filename in os.listdir(download_folder):
            file_path = os.path.join(download_folder, filename)
            created_at = datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            translated_files.append({'filename': filename, 'created_at': created_at})

    # Fichiers pour le marketing
    if os.path.exists(marketing_folder):
        for filename in os.listdir(marketing_folder):
            file_path = os.path.join(marketing_folder, filename)
            if os.path.isfile(file_path):
                created_at = os.path.getctime(file_path)
                marketing_files.append({
                    "filename": filename,
                    "created_at": datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')
                })

    return render_template(
        'main_menu.html',
        translated_files=translated_files,
        marketing_files=marketing_files
    )

@app.route("/upload", methods=["POST"])
@auth.login_required
def upload_file():
    """
    Endpoint pour téléverser un fichier et lancer la traduction.
    """
    if "file" not in request.files:
        return jsonify({"message": "Aucun fichier fourni"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "Nom de fichier invalide"}), 400

    input_file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    output_file_path = os.path.join(app.config["DOWNLOAD_FOLDER"], f"translated_{file.filename}")
    
    file.save(input_file_path)
    logger.info(f"Fichier téléchargé : {input_file_path}")

    # Lancer la traduction dans un thread séparé
    thread = threading.Thread(target=start_translation_process, args=(input_file_path, output_file_path))
    thread.start()

    return redirect(url_for("check_status"))

@app.route("/check_status")
@auth.login_required
def check_status():
    """
    Retourne le statut actuel de la tâche.
    """
    return jsonify(task_status)

@app.route("/set_status/<string:status>", methods=["POST"])
@auth.login_required
def set_status(status):
    """
    Met à jour le statut global de la tâche.
    """
    if status in ["done", "processing", "idle", "error"]:
        set_task_status(status, {
            "done": "Traduction terminée.",
            "processing": "Traitement en cours.",
            "idle": "Aucune tâche en cours.",
            "error": "Une erreur est survenue."
        }.get(status, "Statut inconnu."))
        return jsonify({"message": "Statut mis à jour avec succès."})
    return jsonify({"message": "Statut invalide."}), 400

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/download/<filename>")
@auth.login_required
def download_file(filename):
    """
    Permet de télécharger un fichier traduit.
    """
    download_path = app.config["DOWNLOAD_FOLDER"]
    if not os.path.exists(os.path.join(download_path, filename)):
        return jsonify({"message": "Fichier non trouvé."}), 404
    
    return send_from_directory(download_path, filename, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=app.config.get("DEBUG", False), host="0.0.0.0", port=port)
