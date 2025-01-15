from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_from_directory, current_app
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import os
import threading
import logging
from .utils import (
    translate_docx_with_deepl,
    improve_translation,
    create_glossary,
    convert_excel_to_csv,
    get_translated_files,  # Fonction pour récupérer les fichiers traduits
    save_translation_metadata  # Fonction pour sauvegarder les métadonnées des fichiers traduits
)

bp = Blueprint("translation_app", __name__, template_folder="templates")
auth = HTTPBasicAuth()

# Authentification
users = {
    "admin": generate_password_hash("Roue2021*")
}

@auth.verify_password
def verify_password(username, password):
    """
    Vérifie si le nom d'utilisateur et le mot de passe sont corrects.
    """
    if username in users and check_password_hash(users.get(username), password):
        return username

# Variable globale pour suivre le statut du traitement
progress = {"status": "idle", "message": ""}

# Logger
logger = logging.getLogger("translation_app")

@bp.route("/")
@auth.login_required
def main_menu():
    """
    Page principale affichant les options et le tableau des fichiers traduits.
    """
    translated_files = get_translated_files()
    return render_template("main_menu.html", translated_files=translated_files)

@bp.route("/processing")
@auth.login_required
def processing():
    """
    Page de traitement en cours.
    """
    return render_template("processing.html")

@bp.route("/done")
@auth.login_required
def done():
    """
    Page indiquant que la traduction est terminée.
    """
    output_file_name = progress.get("output_file_name", "improved_output.docx")
    return render_template("done.html", output_file_name=output_file_name)

@bp.route("/downloads/<filename>")
@auth.login_required
def download_file(filename):
    """
    Télécharge le fichier traduit.
    """
    download_path = current_app.config["DOWNLOAD_FOLDER"]
    return send_from_directory(download_path, filename, as_attachment=True)

@bp.route("/check_status")
@auth.login_required
def check_status():
    """
    Vérifie le statut du traitement en cours.
    """
    return jsonify(progress)

@bp.route("/process", methods=["POST"])
@auth.login_required
def process():
    """
    Démarre le processus de traduction.
    """
    def background_process(input_path, final_output_path, **kwargs):
        global progress
        try:
            progress["status"] = "in_progress"
            progress["message"] = "Traitement en cours..."

            # Gestion du glossaire
            glossary_id = None
            if kwargs.get("glossary_csv_path"):
                glossary_id = create_glossary(
                    api_key=current_app.config["DEEPL_API_KEY"],
                    name="MyGlossary",
                    source_lang=kwargs["source_language"],
                    target_lang=kwargs["target_language"],
                    glossary_path=kwargs["glossary_csv_path"],
                )

            # Traduction avec DeepL
            translated_output_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "translated.docx")
            translate_docx_with_deepl(
                api_key=current_app.config["DEEPL_API_KEY"],
                input_file_path=input_path,
                output_file_path=translated_output_path,
                target_language=kwargs["target_language"],
                source_language=kwargs["source_language"],
                glossary_id=glossary_id,
            )

            # Amélioration avec ChatGPT
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

            # Sauvegarde des métadonnées
            save_translation_metadata(final_output_path)

            progress["status"] = "done"
            progress["message"] = "Traitement terminé avec succès."
            progress["output_file_name"] = os.path.basename(final_output_path)

        except Exception as e:
            progress["status"] = "error"
            progress["message"] = f"Une erreur est survenue : {str(e)}"
            logger.error(f"Erreur dans le traitement : {e}")

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

    return redirect(url_for("translation_app.processing"))
