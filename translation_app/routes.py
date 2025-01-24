from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, send_from_directory
import os
import threading
from .utils import (
    translate_docx_with_deepl,
    improve_translation,
    create_glossary,
    convert_excel_to_csv,
)
from datetime import datetime
from flask import flash
import logging

# Création du Blueprint
translation_bp = Blueprint("translation", __name__, template_folder="../templates/translation")

# Configuration des logs
logger = logging.getLogger(__name__)

# État global de la tâche
task_status = {"status": "idle", "message": "Aucune tâche en cours.", "output_file_name": None}

def set_task_status(status, message, output_file_name=None):
    logger.info(f"Mise à jour du statut en {status} avec fichier: {output_file_name}")
    task_status.update({
        "status": status,
        "message": message,
        "output_file_name": output_file_name,
    })

@translation_bp.route("/")
def index():
    logger.info("Affichage de la page d'accueil de la traduction.")
    
    try:
        # Vérifier l'existence des dossiers et les créer si nécessaires
        if not os.path.exists(current_app.config["DEEPL_GLOSSARY_FOLDER"]):
            os.makedirs(current_app.config["DEEPL_GLOSSARY_FOLDER"])
        if not os.path.exists(current_app.config["GPT_GLOSSARY_FOLDER"]):
            os.makedirs(current_app.config["GPT_GLOSSARY_FOLDER"])

        # Récupérer les glossaires disponibles
        deepl_glossaries = os.listdir(current_app.config["DEEPL_GLOSSARY_FOLDER"])
        gpt_glossaries = os.listdir(current_app.config["GPT_GLOSSARY_FOLDER"])

        logger.info(f"Glossaires Deepl trouvés: {deepl_glossaries}")
        logger.info(f"Glossaires GPT trouvés: {gpt_glossaries}")

        return render_template(
            "index.html",
            deepl_glossaries=deepl_glossaries,
            gpt_glossaries=gpt_glossaries
        )

    except KeyError as e:
        logger.error(f"Erreur de configuration: {e}")
        return "Erreur de configuration. Vérifiez les variables de configuration.", 500
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return "Erreur interne du serveur", 500


@translation_bp.route("/upload_glossary", methods=["GET", "POST"])
def upload_glossary():
    if request.method == "POST":
        glossary_file = request.files.get("glossary_file")
        glossary_type = request.form.get("glossary_type")

        if glossary_file and glossary_type in ["deepl", "chatgpt"]:
            save_folder = current_app.config["DEEPL_GLOSSARY_FOLDER"] if glossary_type == "deepl" else current_app.config["GPT_GLOSSARY_FOLDER"]
            file_path = os.path.join(save_folder, glossary_file.filename)

            glossary_file.save(file_path)
            logger.info(f"Glossaire sauvegardé à : {file_path}")

            flash("Glossaire uploadé avec succès !", "success")
            return redirect(url_for('translation.main_menu'))
        else:
            flash("Erreur lors de l'upload du glossaire. Veuillez vérifier le fichier et le type sélectionné.", "danger")
            logger.error("Échec de l'upload du fichier. Vérifiez le type ou le fichier fourni.")

    return render_template("upload_glossary.html")
    
@translation_bp.route("/processing")
def processing():
    logger.info("Accès à la page de traitement.")
    return render_template("processing.html")

@translation_bp.route("/done")
def done():
    filename = request.args.get("filename")
    if not filename:
        logger.error("Le nom du fichier n'est pas défini dans la requête.")
        return render_template("error.html", message="Nom du fichier non spécifié.")

    file_path = os.path.join(current_app.config["DOWNLOAD_FOLDER"], filename)
    if not os.path.exists(file_path):
        logger.error(f"Le fichier traduit {filename} est introuvable.")
        return render_template("error.html", message="Le fichier traduit est introuvable.")

    return render_template("done.html", output_file_name=filename)

@translation_bp.route("/check_status")
def check_status():
    if task_status.get("status") == "done" and task_status.get("output_file_name"):
        response = jsonify({
            "status": "done",
            "output_file_name": task_status["output_file_name"],
            "redirect_url": url_for("translation.done", filename=task_status["output_file_name"])
        })
        set_task_status("idle", "Aucune tâche en cours.")
        return response
    elif task_status.get("status") == "error":
        return jsonify({
            "status": "error",
            "message": task_status["message"]
        })
    return jsonify(task_status)

@translation_bp.route("/process", methods=["POST"])
def process():
    try:
        input_file = request.files["input_file"]
        input_path = os.path.join(current_app.config["UPLOAD_FOLDER"], input_file.filename)
        input_file.save(input_path)
        logger.info(f"Fichier source enregistré à : {input_path}")

        glossary_csv_path = request.form.get("deepl_glossary")
        glossary_gpt_path = request.form.get("gpt_glossary")

        if glossary_csv_path:
            glossary_csv_path = os.path.join(current_app.config["DEEPL_GLOSSARY_FOLDER"], glossary_csv_path)

        if glossary_gpt_path:
            glossary_gpt_path = os.path.join(current_app.config["GPT_GLOSSARY_FOLDER"], glossary_gpt_path)

        form_data = {
            "target_language": request.form["target_language"],
            "source_language": request.form["source_language"],
            "language_level": request.form["language_level"],
            "group_size": int(request.form["group_size"]),
            "gpt_model": request.form["gpt_model"],
        }

        output_file_name = request.form.get("output_file_name", "improved_output.docx")
        final_output_path = os.path.join(current_app.config["DOWNLOAD_FOLDER"], output_file_name)

        app = current_app._get_current_object()

        def background_task():
            with app.app_context():
                try:
                    set_task_status("processing", "Traduction en cours...")
                    logger.info("Début du processus de traduction.")

                    glossary_id = None
                    if glossary_csv_path:
                        glossary_id = create_glossary(
                            app.config["DEEPL_API_KEY"],
                            f"Glossary_{form_data['source_language']}_to_{form_data['target_language']}",
                            form_data["source_language"],
                            form_data["target_language"],
                            glossary_csv_path
                        )
                        logger.info(f"Glossaire Deepl utilisé : {glossary_csv_path}")

                    translate_docx_with_deepl(
                        api_key=app.config["DEEPL_API_KEY"],
                        input_file_path=input_path,
                        output_file_path=final_output_path,
                        target_language=form_data["target_language"],
                        source_language=form_data["source_language"],
                        glossary_id=glossary_id,
                    )

                    improve_translation(
                        input_file=final_output_path,
                        glossary_path=glossary_gpt_path,
                        output_file=final_output_path,
                        language_level=form_data["language_level"],
                        source_language=form_data["source_language"],
                        target_language=form_data["target_language"],
                        group_size=form_data["group_size"],
                        model=form_data["gpt_model"],
                    )

                    set_task_status("done", "Traduction terminée", os.path.basename(final_output_path))
                    logger.info(f"Traduction terminée avec succès : {os.path.basename(final_output_path)}")
                except Exception as e:
                    set_task_status("error", f"Erreur lors du traitement : {str(e)}")
                    logger.error(f"Erreur dans le traitement : {e}")

        thread = threading.Thread(target=background_task)
        thread.start()

        return redirect(url_for("translation.processing"))
    except Exception as e:
        logger.error(f"Erreur lors de l'upload du fichier : {str(e)}")
        set_task_status("error", "Erreur lors de l'upload du fichier.")
        return redirect(url_for("translation.error"))

@translation_bp.route('/download/<filename>')
def download_file(filename):
    download_folder = current_app.config["DOWNLOAD_FOLDER"]
    return send_from_directory(download_folder, filename, as_attachment=True)

@translation_bp.route("/main_menu")
def main_menu():
    download_folder = current_app.config["DOWNLOAD_FOLDER"]
    translated_files = []

    if os.path.exists(download_folder):
        for filename in os.listdir(download_folder):
            file_path = os.path.join(download_folder, filename)
            created_at = datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            translated_files.append({'filename': filename, 'created_at': created_at})

    return render_template("main_menu.html", translated_files=translated_files)
