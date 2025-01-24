from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, send_from_directory, flash
import os
import threading
from .utils import (
    translate_docx_with_deepl,
    improve_translation,
    create_glossary,
)
from datetime import datetime
from docx import Document
import chardet  # MODIFICATION
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
    
def detect_encoding(file_path):  # MODIFICATION
    """Détecte l'encodage d'un fichier donné."""
    with open(file_path, 'rb') as f:
        raw_data = f.read(4096)
        result = chardet.detect(raw_data)
        return result['encoding']

@translation_bp.route("/")
def index():
    logger.info("Affichage de la page d'accueil de la traduction.")
    try:
        os.makedirs(current_app.config["DEEPL_GLOSSARY_FOLDER"], exist_ok=True)
        os.makedirs(current_app.config["GPT_GLOSSARY_FOLDER"], exist_ok=True)

        logger.info(f"Accès au dossier Deepl : {os.access(current_app.config['DEEPL_GLOSSARY_FOLDER'], os.R_OK)}")
        logger.info(f"Accès au dossier GPT : {os.access(current_app.config['GPT_GLOSSARY_FOLDER'], os.R_OK)}")

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
        try:
            glossary_file = request.files.get("glossary_file")
            glossary_type = request.form.get("glossary_type")

            if not glossary_file:
                flash("Aucun fichier sélectionné.", "danger")
                logger.error("Aucun fichier sélectionné.")
                return redirect(url_for('translation.upload_glossary'))

            if glossary_type not in ["deepl", "chatgpt"]:
                flash("Type de glossaire invalide.", "danger")
                logger.error("Type de glossaire invalide sélectionné.")
                return redirect(url_for('translation.upload_glossary'))

            save_folder = current_app.config["DEEPL_GLOSSARY_FOLDER"] if glossary_type == "deepl" else current_app.config["GPT_GLOSSARY_FOLDER"]
            os.makedirs(save_folder, exist_ok=True)  # MODIFICATION
            file_path = os.path.join(save_folder, glossary_file.filename)  # MODIFICATION

            allowed_extensions = {".csv", ".xlsx", ".docx"}
            if not glossary_file.filename.lower().endswith(tuple(allowed_extensions)):
                flash("Format de fichier non autorisé.", "danger")
                logger.error("Format de fichier non autorisé.")
                return redirect(url_for('translation.upload_glossary'))

            glossary_file.save(file_path)   # Enregistrer le fichier sur le serveur
            logger.info(f"Glossaire sauvegardé avec succès : {file_path}")
            flash("Glossaire uploadé avec succès !", "success")

            return redirect(url_for('translation.main_menu'))

        except Exception as e:
            flash("Une erreur est survenue lors de l'upload.", "danger")
            logger.error(f"Erreur lors de l'upload du glossaire : {str(e)}")
            return redirect(url_for('translation.upload_glossary'))

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

@translation_bp.route("/process", methods=["POST"])
def process():
    try:
        input_file = request.files["input_file"]
        input_path = os.path.join(current_app.config["UPLOAD_FOLDER"], input_file.filename)
        input_file.save(input_path)
        logger.info(f"Fichier source enregistré à : {input_path}")

        glossary_csv_name = request.form.get("deepl_glossary")
        glossary_gpt_name = request.form.get("gpt_glossary")

        # Construction des chemins complets des glossaires
        glossary_csv_path = os.path.join(current_app.config["DEEPL_GLOSSARY_FOLDER"], glossary_csv_name) if glossary_csv_name else None
        glossary_gpt_path = os.path.join(current_app.config["GPT_GLOSSARY_FOLDER"], glossary_gpt_name) if glossary_gpt_name else None

        # Vérification de l'existence du glossaire GPT
        if glossary_gpt_path and not os.path.exists(glossary_gpt_path):
            logger.error(f"Glossary GPT introuvable : {glossary_gpt_path}")
            flash(f"Le fichier de glossaire GPT {glossary_gpt_name} est introuvable.", "danger")
            return redirect(url_for("translation.index"))

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
                    if glossary_csv_path and os.path.exists(glossary_csv_path):
                        glossary_id = create_glossary(
                            app.config["DEEPL_API_KEY"],
                            f"Glossary_{form_data['source_language']}_to_{form_data['target_language']}",
                            form_data["source_language"],
                            form_data["target_language"],
                            glossary_csv_path
                        )
                        logger.info(f"Glossaire Deepl utilisé : {glossary_csv_path}")

                    # Vérification et lecture sécurisée du fichier DOCX
                    if input_path.lower().endswith('.docx'):
                        logger.info("Fichier DOCX détecté. Lecture via python-docx.")
                        try:
                            doc = Document(input_path)
                            text_content = "\n".join([para.text for para in doc.paragraphs])
                        except Exception as e:
                            set_task_status("error", f"Erreur de lecture DOCX: {str(e)}")
                            logger.error(f"Erreur de lecture du fichier DOCX: {str(e)}")
                            return
                    else:
                        encoding = detect_encoding(input_path)  # MODIFICATION
                        try:
                            with open(input_path, 'r', encoding=encoding) as f:
                                file_content = f.read()
                                logger.info(f"Fichier source chargé avec succès en encodage détecté: {encoding}")  # MODIFICATION
                        except UnicodeDecodeError as e:
                            logger.error(f"Erreur d'encodage lors de la lecture du fichier : {e}")  # MODIFICATION
                            set_task_status("error", f"Erreur d'encodage: {str(e)}")  # MODIFICATION
                            return

                    translate_docx_with_deepl(
                        api_key=app.config["DEEPL_API_KEY"],
                        input_file_path=input_path,
                        output_file_path=final_output_path,
                        target_language=form_data["target_language"],
                        source_language=form_data["source_language"],
                        glossary_id=glossary_id,
                    )
                    logger.info("Traduction initiale terminée avec DeepL.")

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
                    logger.info(f"Amélioration de la traduction terminée avec ChatGPT : {glossary_gpt_path}")

                    set_task_status("done", "Traduction terminée", os.path.basename(final_output_path))
                    logger.info(f"Traduction terminée avec succès : {final_output_path}")
                except Exception as e:
                    set_task_status("error", f"Erreur lors du traitement : {str(e)}")
                    logger.error(f"Erreur dans le traitement : {e}")

        thread = threading.Thread(target=background_task)
        thread.start()

        return redirect(url_for("translation.processing"))

    except Exception as e:
        logger.error(f"Erreur lors du traitement du fichier : {str(e)}")
        flash("Une erreur est survenue lors du traitement du fichier.", "danger")
        return redirect(url_for("translation.error"))


@translation_bp.route('/download/<filename>')
def download_file(filename):
    download_folder = current_app.config["DOWNLOAD_FOLDER"]
    try:
        return send_from_directory(download_folder, filename, as_attachment=True)
    except FileNotFoundError:
        flash("Fichier introuvable.", "danger")
        return redirect(url_for('translation.main_menu'))


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
