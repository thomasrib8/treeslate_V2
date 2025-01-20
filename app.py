from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, send_from_directory
import os
import threading
import logging
from utils import translate_docx_with_deepl

# Création du Blueprint
translation_bp = Blueprint("translation", __name__, template_folder="../templates/translation")

# Configuration des logs
logger = logging.getLogger(__name__)

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
    """
    with current_app.app_context():
        try:
            set_task_status("processing", "Traduction en cours...")

            # Simulation du processus de traduction
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

@translation_bp.route("/")
def index():
    """
    Affiche la page d'accueil de l'application de traduction.
    """
    logger.info("Affichage de la page d'accueil de la traduction.")
    return render_template("index.html")

@translation_bp.route("/processing")
def processing():
    """
    Affiche la page de traitement de la traduction.
    """
    logger.info("Accès à la page de traitement.")
    return render_template("processing.html")

@translation_bp.route("/done")
def done():
    """
    Affiche la page de fin de traitement lorsque la traduction est terminée.
    """
    filename = request.args.get("filename", "output.docx")
    return render_template("done.html", filename=filename)

@translation_bp.route("/process", methods=["POST"])
def process():
    """
    Démarre le processus de traduction.
    """
    input_file = request.files["input_file"]
    input_path = os.path.join(current_app.config["UPLOAD_FOLDER"], input_file.filename)
    input_file.save(input_path)

    output_file_name = request.form.get("output_file_name", "translated_output.docx")
    output_path = os.path.join(current_app.config["DOWNLOAD_FOLDER"], output_file_name)

    logger.info("Début du processus de traduction.")
    
    # Lancer la traduction dans un thread séparé
    thread = threading.Thread(target=start_translation_process, args=(input_path, output_path))
    thread.start()

    return redirect(url_for("translation.processing"))

@translation_bp.route("/check_status")
def check_status():
    """
    Vérifie le statut de la traduction en cours.
    """
    return jsonify(task_status)

@translation_bp.route("/download/<filename>")
def download(filename):
    """
    Permet de télécharger le fichier de sortie une fois la traduction terminée.
    """
    download_path = current_app.config["DOWNLOAD_FOLDER"]
    return send_from_directory(download_path, filename, as_attachment=True)

@translation_bp.route("/error")
def error():
    """
    Affiche une page d'erreur en cas de problème.
    """
    return render_template("error.html", message=task_status["message"])
