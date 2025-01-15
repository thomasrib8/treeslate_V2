from flask import Blueprint, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_httpauth import HTTPBasicAuth
import os
import threading
from werkzeug.security import generate_password_hash, check_password_hash
from translation_app.database import init_db, add_translated_file, get_translated_files
from translation_app.translation_utils import translate_docx_with_deepl, improve_translation, create_glossary, convert_excel_to_csv
import logging

# Configuration
bp = Blueprint("translation", __name__)
UPLOAD_FOLDER = "translation_app/uploads"
DOWNLOAD_FOLDER = "translation_app/downloads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Authentification HTTP
auth = HTTPBasicAuth()

# Utilisateurs autorisés
users = {
    "admin": generate_password_hash("Roue2021*"),  # Remplacez par votre mot de passe
}

# Clés API (provenant des variables d'environnement)
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("translation")

# Initialiser la base de données
init_db()

@auth.verify_password
def verify_password(username, password):
    """
    Vérifie si le nom d'utilisateur et le mot de passe sont corrects.
    """
    if username in users and check_password_hash(users.get(username), password):
        return username

# Variable pour suivre le statut du traitement
progress = {"status": "idle", "message": ""}

@bp.route("/")
@auth.login_required
def home():
    """
    Page principale avec le tableau des fichiers traduits.
    """
    translated_files = get_translated_files()  # Récupère les fichiers traduits
    return render_template("home.html", translated_files=translated_files)

@bp.route("/process", methods=["POST"])
@auth.login_required
def process():
    """
    Lance le processus de traduction et amélioration en arrière-plan.
    """
    def background_process(input_path, final_output_path, **kwargs):
        global progress
        try:
            progress["status"] = "in_progress"
            progress["message"] = "Traitement en cours..."
            logger.debug("Début du traitement en arrière-plan.")

            # Vérification de la clé API DeepL
            logger.debug(f"DEEPL_API_KEY starts with: {DEEPL_API_KEY[:5] if DEEPL_API_KEY else 'Not Set'}")

            # Gestion du glossaire DeepL
            glossary_id = None
            if kwargs.get("glossary_csv_path"):
                logger.debug(f"Création du glossaire avec le fichier : {kwargs['glossary_csv_path']}")
                glossary_id = create_glossary(
                    api_key=DEEPL_API_KEY,
                    name="MyGlossary",
                    source_lang=kwargs["source_language"],
                    target_lang=kwargs["target_language"],
                    glossary_path=kwargs["glossary_csv_path"],
                )

            # Traduction avec DeepL
            logger.debug("Début de la traduction avec DeepL.")
            translated_output_path = os.path.join(UPLOAD_FOLDER, "translated.docx")
            translate_docx_with_deepl(
                api_key=DEEPL_API_KEY,
                input_file_path=input_path,
                output_file_path=translated_output_path,
                target_language=kwargs["target_language"],
                source_language=kwargs["source_language"],
                glossary_id=glossary_id,
            )

            # Amélioration avec ChatGPT
            logger.debug("Début de l'amélioration avec ChatGPT.")
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

            # Enregistrer le fichier traduit dans la base de données
            add_translated_file(os.path.basename(final_output_path), final_output_path)

            # Mise à jour du statut
            progress["status"] = "done"
            progress["message"] = "Traitement terminé avec succès."
            progress["output_file_name"] = os.path.basename(final_output_path)
            logger.debug("Traitement terminé avec succès.")

        except Exception as e:
            # Gestion des erreurs
            progress["status"] = "error"
            progress["message"] = f"Une erreur est survenue : {str(e)}"
            logger.error(f"Erreur dans le traitement : {e}")

    # Récupération des fichiers et paramètres
    input_file = request.files["input_file"]
    input_path = os.path.join(UPLOAD_FOLDER, input_file.filename)
    input_file.save(input_path)
    logger.debug(f"Fichier principal téléchargé : {input_path}")

    glossary_csv = request.files.get("glossary_csv")
    glossary_csv_path = None
    if glossary_csv:
        glossary_csv_path = os.path.join(UPLOAD_FOLDER, glossary_csv.filename)
        glossary_csv.save(glossary_csv_path)
        logger.debug(f"Glossaire CSV téléchargé : {glossary_csv_path}")

        if glossary_csv_path.endswith(".xlsx"):
            glossary_csv_path = convert_excel_to_csv(glossary_csv_path, glossary_csv_path.replace(".xlsx", ".csv"))
            logger.debug(f"Glossaire Excel converti en CSV : {glossary_csv_path}")

    glossary_gpt = request.files.get("glossary_gpt")
    glossary_gpt_path = None
    if glossary_gpt:
        glossary_gpt_path = os.path.join(UPLOAD_FOLDER, glossary_gpt.filename)
        glossary_gpt.save(glossary_gpt_path)
        logger.debug(f"Glossaire GPT téléchargé : {glossary_gpt_path}")

    # Nom de fichier de sortie
    output_file_name = request.form.get("output_file_name", "improved_output.docx")
    final_output_path = os.path.join(DOWNLOAD_FOLDER, output_file_name)

    # Lancer le traitement en arrière-plan
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

    # Redirection vers la page de traitement
    return redirect(url_for("translation.processing"))

@bp.route("/processing")
@auth.login_required
def processing():
    """
    Page de traitement.
    """
    return render_template("processing.html")

@bp.route("/downloads/<filename>")
@auth.login_required
def download_file(filename):
    """
    Permet à l'utilisateur de télécharger un fichier traduit.
    """
    download_path = DOWNLOAD_FOLDER
    return send_from_directory(download_path, filename, as_attachment=True)

@bp.route("/check_status")
@auth.login_required
def check_status():
    """
    Vérifie le statut actuel du traitement.
    """
    return jsonify(progress)
