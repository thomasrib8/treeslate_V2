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

# Variable globale pour suivre le statut du traitement
progress = {"status": "idle", "message": ""}

@translation_bp.route("/")
def index():
    """
    Page principale de l'application de traduction.
    """
    logger.debug("Page principale (index) affichée.")
    return render_template("translation/index.html")


@translation_bp.route("/processing")
def processing():
    """
    Page intermédiaire affichant "Traduction en cours...".
    """
    logger.debug("Page de traitement en cours affichée.")
    return render_template("translation/processing.html")


@translation_bp.route("/done")
def done():
    """
    Page finale affichant "Traduction terminée".
    """
    output_file_name = progress.get("output_file_name", "improved_output.docx")
    return render_template("translation/done.html", output_file_name=output_file_name)


@translation_bp.route("/downloads/<filename>")
def download_file(filename):
    """
    Permet à l'utilisateur de télécharger le fichier traduit.
    """
    download_path = current_app.config["DOWNLOAD_FOLDER"]
    file_path = os.path.join(download_path, filename)
    logger.debug(f"Request to download file: {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return "File not found", 404

    return send_from_directory(download_path, filename, as_attachment=True)


@translation_bp.route("/check_status")
def check_status():
    """
    Vérifie le statut du traitement en cours.
    """
    logger.debug(f"Statut du traitement demandé : {progress}")
    return jsonify(progress)


@translation_bp.route("/process", methods=["POST"])
def process():
    """
    Démarre le processus principal de traitement en arrière-plan.
    """
    def background_process(input_path, final_output_path, **kwargs):
        global progress
        try:
            progress["status"] = "in_progress"
            progress["message"] = "Traitement en cours..."
            logger.debug("Début du traitement en arrière-plan.")

            glossary_id = None
            if kwargs.get("glossary_csv_path"):
                logger.debug(f"Création du glossaire avec le fichier : {kwargs['glossary_csv_path']}")
                glossary_id = create_glossary(
                    api_key=current_app.config["DEEPL_API_KEY"],
                    name="MyGlossary",
                    source_lang=kwargs["source_language"],
                    target_lang=kwargs["target_language"],
                    glossary_path=kwargs["glossary_csv_path"],
                )

            translated_output_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "translated.docx")
            translate_docx_with_deepl(
                api_key=current_app.config["DEEPL_API_KEY"],
                input_file_path=input_path,
                output_file_path=translated_output_path,
                target_language=kwargs["target_language"],
                source_language=kwargs["source_language"],
                glossary_id=glossary_id,
            )

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

            progress["status"] = "done"
            progress["message"] = "Traitement terminé avec succès."
            progress["output_file_name"] = os.path.basename(final_output_path)
            logger.debug("Traitement terminé avec succès.")

        except Exception as e:
            progress["status"] = "error"
            progress["message"] = f"Une erreur est survenue : {str(e)}"
            logger.error(f"Erreur dans le traitement : {e}")

    input_file = request.files["input_file"]
    input_path = os.path.join(current_app.config["UPLOAD_FOLDER"], input_file.filename)
    input_file.save(input_path)
    logger.debug(f"Fichier principal téléchargé : {input_path}")

    glossary_csv = request.files.get("glossary_csv")
    glossary_csv_path = None
    if glossary_csv:
        glossary_csv_path = os.path.join(current_app.config["UPLOAD_FOLDER"], glossary_csv.filename)
        glossary_csv.save(glossary_csv_path)
        logger.debug(f"Glossaire CSV téléchargé : {glossary_csv_path}")

        if glossary_csv_path.endswith(".xlsx"):
            glossary_csv_path = convert_excel_to_csv(glossary_csv_path, glossary_csv_path.replace(".xlsx", ".csv"))
            logger.debug(f"Glossaire Excel converti en CSV : {glossary_csv_path}")

    glossary_gpt = request.files.get("glossary_gpt")
    glossary_gpt_path = None
    if glossary_gpt:
        glossary_gpt_path = os.path.join(current_app.config["UPLOAD_FOLDER"], glossary_gpt.filename)
        glossary_gpt.save(glossary_gpt_path)
        logger.debug(f"Glossaire GPT téléchargé : {glossary_gpt_path}")

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

    threading.Thread(target=background_process, args=(input_path, final_output_path), kwargs=thread_args).start()

    return redirect(url_for("translation.processing"))
