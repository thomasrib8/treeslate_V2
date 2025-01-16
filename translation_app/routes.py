from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, send_from_directory, session
import os
import threading
import uuid
from .utils import (
    translate_docx_with_deepl,
    improve_translation,
    create_glossary,
    convert_excel_to_csv,
    read_glossary,
)
import logging
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")

# Création du Blueprint
translation_bp = Blueprint("translation", __name__, template_folder="../templates/translation")

# Configuration des logs
logger = logging.getLogger(__name__)

# Dictionnaire pour suivre le statut des traitements par utilisateur
progress_store = {}

# Middleware pour assigner un ID utilisateur unique à chaque session
@translation_bp.before_request
def assign_user_id():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

def get_user_progress():
    user_id = session.get("user_id")
    return progress_store.setdefault(user_id, {"status": "idle", "message": "Aucune tâche en cours."})

def set_user_progress(status, message, output_file_name=None):
    user_id = session.get("user_id")
    progress_store[user_id] = {
        "status": status,
        "message": message,
        "output_file_name": output_file_name,
    }

@translation_bp.route("/")
def index():
    """
    Page principale de l'application de traduction.
    """
    logger.debug("Page principale (index) affichée.")
    return render_template("index.html")

@translation_bp.route("/processing")
def processing():
    """
    Page intermédiaire affichant "Traduction en cours...".
    """
    progress = get_user_progress()
    logger.debug(f"Accès à la page de traitement. Statut actuel : {progress['status']}")
    if progress["status"] == "error":
        return redirect(url_for("translation.index"))
    return render_template("processing.html")

@translation_bp.route("/done")
def done():
    """
    Page finale affichant "Traduction terminée".
    """
    progress = get_user_progress()
    output_file_name = progress.get("output_file_name", "improved_output.docx")
    return render_template("done.html", output_file_name=output_file_name)

@translation_bp.route("/downloads/<filename>")
def download_file(filename):
    """
    Permet à l'utilisateur de télécharger le fichier traduit.
    """
    download_path = current_app.config["DOWNLOAD_FOLDER"]
    file_path = os.path.join(download_path, filename)
    logger.debug(f"Demande de téléchargement pour : {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"Fichier non trouvé : {file_path}")
        return "File not found", 404

    return send_from_directory(download_path, filename, as_attachment=True)

@translation_bp.route("/check_status")
def check_status():
    """
    Vérifie le statut du traitement en cours.
    """
    progress = get_user_progress()
    logger.debug(f"Statut actuel renvoyé : {progress}")
    return jsonify(progress)

@translation_bp.route("/process", methods=["POST"])
def process():
    """
    Démarre le processus principal de traitement en arrière-plan.
    """
    app_context = current_app._get_current_object()

    def background_process(app_context, input_path, final_output_path, **kwargs):
        progress = get_user_progress()
        with app_context.app_context():
            try:
                set_user_progress("in_progress", "Traitement en cours...")
                logger.debug("Début du traitement en arrière-plan.")

                # Création du glossaire si nécessaire
                glossary_id = None
                if kwargs.get("glossary_csv_path"):
                    logger.debug(f"Création du glossaire avec le fichier : {kwargs['glossary_csv_path']}")
                    glossary_id = create_glossary(
                        api_key=app_context.config["DEEPL_API_KEY"],
                        name="MyGlossary",
                        source_lang=kwargs["source_language"],
                        target_lang=kwargs["target_language"],
                        glossary_path=kwargs["glossary_csv_path"],
                    )

                # Traduction du fichier source
                translated_output_path = os.path.join(app_context.config["UPLOAD_FOLDER"], "translated.docx")
                translate_docx_with_deepl(
                    api_key=app_context.config["DEEPL_API_KEY"],
                    input_file_path=input_path,
                    output_file_path=translated_output_path,
                    target_language=kwargs["target_language"],
                    source_language=kwargs["source_language"],
                    glossary_id=glossary_id,
                )

                # Amélioration de la traduction avec OpenAI
                improve_translation(
                    input_file=translated_output_path,
                    glossary_path=kwargs.get("glossary_gpt_path"),
                    output_file=final_output_path,
                    language_level=kwargs["language_level"],
                    source_language=kwargs["source_language"],
                    target_language=kwargs["target_language"],
                    group_size=kwargs["group_size"],
                    model=kwargs["gpt_model"],
                )

                set_user_progress("done", "Traitement terminé avec succès.", output_file_name=os.path.basename(final_output_path))
                logger.debug("Traitement terminé avec succès.")

            except Exception as e:
                set_user_progress("error", f"Une erreur est survenue : {str(e)}")
                logger.error(f"Erreur dans le traitement : {e}")

    # Téléchargement des fichiers
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

    glossary_gpt = request.files.get("glossary_gpt")
    glossary_gpt_path = None
    if glossary_gpt:
        glossary_gpt_path = os.path.join(current_app.config["UPLOAD_FOLDER"], glossary_gpt.filename)
        glossary_gpt.save(glossary_gpt_path)

    # Préparation du fichier de sortie
    output_file_name = request.form.get("output_file_name", "improved_output.docx")
    final_output_path = os.path.join(current_app.config["DOWNLOAD_FOLDER"], output_file_name)

    thread_args = {
        "glossary_csv_path": glossary_csv_path,
        "glossary_gpt_path": glossary_gpt_path,
        "source_language": request.form["source_language"],
        "target_language": request.form["target_language"],
        "language_level": request.form["language_level"],
        "group_size": int(request.form["group_size"]),
        "gpt_model": request.form["gpt_model"],
    }

    threading.Thread(target=background_process, args=(app_context, input_path, final_output_path), kwargs=thread_args).start()

    return redirect(url_for("translation.processing"))
