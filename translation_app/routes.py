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
import chardet
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

def detect_encoding(file_path):
    """Détecte l'encodage d'un fichier."""
    with open(file_path, 'rb') as f:
        raw_data = f.read(8192)
        result = chardet.detect(raw_data)
        detected_encoding = result.get('encoding', 'utf-8')
        logger.info(f"Encodage détecté : {detected_encoding} pour {file_path}")
        return detected_encoding

def detect_and_convert_to_utf8(file_path):
    """Détecte et convertit un fichier en UTF-8 si nécessaire."""
    try:
        encoding = detect_encoding(file_path)
        if encoding.lower() == 'utf-8':
            logger.info(f"Aucune conversion nécessaire, fichier déjà en UTF-8 : {file_path}")
            return True

        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Conversion réussie de {encoding} vers UTF-8 pour {file_path}")
        return True

    except UnicodeDecodeError as e:
        logger.error(f"Erreur de conversion d'encodage {encoding} -> UTF-8 : {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue dans la détection/conversion d'encodage : {e}")
        return False

def verify_glossary_encoding(file_path):
    """Vérifie si le glossaire est lisible avec son encodage détecté."""
    encoding = detect_encoding(file_path)
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            f.read()
        logger.info(f"Le fichier {file_path} est lisible avec l'encodage {encoding}.")
        return True
    except UnicodeDecodeError:
        logger.error(f"Erreur de lecture du fichier {file_path} avec l'encodage détecté {encoding}.")
        return False

@translation_bp.route("/")
def index():
    logger.info("Affichage de la page d'accueil de la traduction.")
    try:
        os.makedirs(current_app.config["DEEPL_GLOSSARY_FOLDER"], exist_ok=True)
        os.makedirs(current_app.config["GPT_GLOSSARY_FOLDER"], exist_ok=True)

        deepl_glossaries = os.listdir(current_app.config["DEEPL_GLOSSARY_FOLDER"])
        gpt_glossaries = os.listdir(current_app.config["GPT_GLOSSARY_FOLDER"])

        return render_template(
            "index.html",
            deepl_glossaries=deepl_glossaries,
            gpt_glossaries=gpt_glossaries
        )
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
                return redirect(url_for('translation.upload_glossary'))

            if glossary_type not in ["deepl", "chatgpt"]:
                flash("Type de glossaire invalide.", "danger")
                return redirect(url_for('translation.upload_glossary'))

            save_folder = current_app.config["DEEPL_GLOSSARY_FOLDER"] if glossary_type == "deepl" else current_app.config["GPT_GLOSSARY_FOLDER"]
            file_path = os.path.join(save_folder, glossary_file.filename)

            allowed_extensions = {".csv", ".xlsx", ".docx"}
            if not glossary_file.filename.lower().endswith(tuple(allowed_extensions)):
                flash("Format de fichier non autorisé.", "danger")
                return redirect(url_for('translation.upload_glossary'))

            glossary_file.save(file_path)
            flash("Glossaire uploadé avec succès !", "success")
            return redirect(url_for('translation.main_menu'))

        except Exception as e:
            flash("Une erreur est survenue lors de l'upload.", "danger")
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

        if not detect_and_convert_to_utf8(input_path):
            set_task_status("error", "Erreur lors de la conversion en UTF-8")
            flash("Erreur lors de la conversion du fichier en UTF-8.", "danger")
            return redirect(url_for("translation.index"))

        glossary_csv_name = request.form.get("deepl_glossary")
        glossary_gpt_name = request.form.get("gpt_glossary")

        glossary_csv_path = os.path.join(current_app.config["DEEPL_GLOSSARY_FOLDER"], glossary_csv_name) if glossary_csv_name else None
        glossary_gpt_path = os.path.join(current_app.config["GPT_GLOSSARY_FOLDER"], glossary_gpt_name) if glossary_gpt_name else None

        # Vérification de l'encodage des glossaires
        if glossary_csv_path and not verify_glossary_encoding(glossary_csv_path):
            set_task_status("error", "Erreur d'encodage du glossaire Deepl")
            flash("Le fichier de glossaire Deepl a un encodage non valide.", "danger")
            return redirect(url_for("translation.index"))

        if glossary_gpt_path and not verify_glossary_encoding(glossary_gpt_path):
            set_task_status("error", "Erreur d'encodage du glossaire GPT")
            flash("Le fichier de glossaire GPT a un encodage non valide.", "danger")
            return redirect(url_for("translation.index"))

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
                            f"Glossary_{request.form['source_language']}_to_{request.form['target_language']}",
                            request.form["source_language"],
                            request.form["target_language"],
                            glossary_csv_path
                        )
                        logger.info(f"Glossaire Deepl utilisé : {glossary_csv_path}")

                    if input_path.lower().endswith('.docx'):
                        logger.info("Fichier DOCX détecté, pas de conversion d'encodage nécessaire.")
                    else:
                        if not detect_and_convert_to_utf8(input_path):
                            set_task_status("error", "Erreur lors de la conversion en UTF-8")
                            flash("Erreur lors de la conversion du fichier en UTF-8.", "danger")
                            return redirect(url_for("translation.index"))

                    translate_docx_with_deepl(
                        api_key=app.config["DEEPL_API_KEY"],
                        input_file_path=input_path,
                        output_file_path=final_output_path,
                        target_language=request.form["target_language"],
                        source_language=request.form["source_language"],
                        glossary_id=glossary_id,  # Utilisation du glossaire sélectionné
                    )
                    logger.info(f"Traduction initiale terminée avec DeepL en utilisant le glossaire: {glossary_csv_path if glossary_csv_path else 'Aucun'}")

                    improve_translation(
                        input_file=final_output_path,
                        glossary_path=glossary_gpt_path,
                        output_file=final_output_path,
                        language_level=request.form["language_level"],
                        source_language=request.form["source_language"],
                        target_language=request.form["target_language"],
                        group_size=int(request.form["group_size"]),
                        model=request.form["gpt_model"],
                    )
                    logger.info(f"Amélioration de la traduction terminée avec ChatGPT en utilisant le glossaire: {glossary_gpt_path if glossary_gpt_path else 'Aucun'}")

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
        return redirect(url_for("translation.index"))

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
