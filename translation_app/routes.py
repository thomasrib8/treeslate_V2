from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, send_from_directory
import os
import threading
from .utils import (
    translate_docx_with_deepl,
    improve_translation,
    create_glossary,
    convert_excel_to_csv,
)
import logging

# Création du Blueprint
translation_bp = Blueprint("translation", __name__, template_folder="../templates/translation")

# Configuration des logs
logger = logging.getLogger(__name__)

# État global de la tâche
task_status = {"status": "idle", "message": "Aucune tâche en cours.", "output_file_name": None}

def set_task_status(status, message, output_file_name=None):
    """
    Met à jour le statut de la tâche.
    """
    global task_status
    task_status.update({
        "status": status,
        "message": message,
        "output_file_name": output_file_name,
    })
    logger.info(f"Statut mis à jour : {task_status}")

@translation_bp.route("/")
def index():
    logger.info("Affichage de la page d'accueil de la traduction.")
    return render_template("index.html")

@translation_bp.route("/processing")
def processing():
    """
    Affiche la page de traitement.
    """
    logger.info("Accès à la page de traitement.")
    return render_template("processing.html")

@translation_bp.route("/done")
def done():
    """
    Affiche la page de fin lorsque le traitement est terminé.
    """
    filename = request.args.get("filename", "improved_output.docx")
    file_path = os.path.join(current_app.config["DOWNLOAD_FOLDER"], filename)
    if not os.path.exists(file_path):
        logger.error("Le fichier traduit est introuvable.")
        return render_template("error.html", message="Le fichier traduit est introuvable.")
    return send_from_directory(current_app.config["DOWNLOAD_FOLDER"], filename, as_attachment=True)

@translation_bp.route("/check_status")
def check_status():
    return jsonify(task_status)

@translation_bp.route("/process", methods=["POST"])
def process():
    """
    Démarre le traitement en arrière-plan.
    """
    input_file = request.files["input_file"]
    input_path = os.path.join(current_app.config["UPLOAD_FOLDER"], input_file.filename)
    input_file.save(input_path)

    glossary_csv = request.files.get("glossary_csv")
    glossary_csv_path = None
    if glossary_csv:
        glossary_csv_path = os.path.join(current_app.config["UPLOAD_FOLDER"], glossary_csv.filename)
        glossary_csv.save(glossary_csv_path)
        if glossary_csv_path.endswith(".xlsx"):
            glossary_csv_path = convert_excel_to_csv(glossary_csv_path, glossary_csv_path.replace(".xlsx", ".csv"))

    output_file_name = request.form.get("output_file_name", "improved_output.docx")
    final_output_path = os.path.join(current_app.config["DOWNLOAD_FOLDER"], output_file_name)

    # Capture du contexte d'application Flask
    app = current_app._get_current_object()

    def background_task():
        with app.app_context():
            try:
                set_task_status("processing", "Traduction en cours...")
                logger.info("Début du processus de traduction.")

                translate_docx_with_deepl(
                    api_key=app.config["DEEPL_API_KEY"],
                    input_file_path=input_path,
                    output_file_path=final_output_path,
                    target_language=request.form["target_language"],
                    source_language=request.form["source_language"],
                    glossary_id=create_glossary(app.config["DEEPL_API_KEY"], glossary_csv_path) if glossary_csv_path else None,
                )

                improve_translation(
                    input_file=final_output_path,
                    glossary_path=glossary_csv_path,
                    output_file=final_output_path,
                    language_level=request.form["language_level"],
                    source_language=request.form["source_language"],
                    target_language=request.form["target_language"],
                    group_size=int(request.form["group_size"]),
                    model=request.form["gpt_model"],
                )

                set_task_status("done", "Traduction terminée", output_file_name)
                logger.info("Traduction terminée avec succès.")
            except Exception as e:
                set_task_status("error", f"Erreur lors du traitement : {str(e)}")
                logger.error(f"Erreur dans le traitement : {e}")

    thread = threading.Thread(target=background_task)
    thread.start()

    return redirect(url_for("translation.processing"))

@translation_bp.route("/error")
def error():
    """
    Affiche une page d'erreur en cas de problème.
    """
    return render_template("error.html", error_message=task_status.get("message", "Une erreur est survenue."))

@translation_bp.route("/download/<filename>")
def download_file(filename):
    """
    Permet le téléchargement du fichier traduit.
    """
    return send_from_directory(current_app.config["DOWNLOAD_FOLDER"], filename, as_attachment=True)
