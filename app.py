from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import os
import threading
from your_script import (
    translate_docx_with_deepl,
    improve_translation,
    create_glossary,
    convert_excel_to_csv,
)
import logging

# Configuration de l'application Flask
app = Flask(__name__)

# Configuration des dossiers
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER

# Authentification HTTP
auth = HTTPBasicAuth()

# Utilisateurs autorisés
users = {
    "admin": generate_password_hash("Roue2021*"),  # Remplacez par votre mot de passe
}

# Configuration des clés API
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Configuration des logs
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("app")

@auth.verify_password
def verify_password(username, password):
    """
    Vérifie si le nom d'utilisateur et le mot de passe sont corrects.
    """
    if username in users and check_password_hash(users.get(username), password):
        return username

# Variable globale pour suivre le statut du traitement
progress = {"status": "idle", "message": ""}

@app.route("/")
@auth.login_required
def index():
    """
    Page principale affichant le formulaire de téléchargement et les options.
    """
    logger.debug("Page principale (index) affichée.")
    return render_template("index.html")

@app.route("/processing")
@auth.login_required
def processing():
    """
    Page intermédiaire affichant "Traduction en cours...".
    """
    logger.debug("Page de traitement en cours affichée.")
    return render_template("processing.html")

@app.route("/done")
@auth.login_required
def done():
    """
    Page finale affichant "Traduction terminée".
    """
    output_file_name = progress.get("output_file_name", "improved_output.docx")
    return render_template("done.html", output_file_name=output_file_name)

@app.route("/check_status")
@auth.login_required
def check_status():
    """
    Vérifie le statut du traitement en cours.
    """
    logger.debug(f"Statut du traitement demandé : {progress}")
    return jsonify(progress)

@app.route("/process", methods=["POST"])
@auth.login_required
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
            translated_output_path = os.path.join(app.config["UPLOAD_FOLDER"], "translated.docx")
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

            # Mise à jour pour indiquer que le traitement est terminé
            progress["status"] = "done"
            progress["message"] = "Traitement terminé avec succès."
            progress["output_file_name"] = os.path.basename(final_output_path)
            logger.debug("Traitement terminé avec succès.")

        except Exception as e:
            # Mise à jour en cas d'erreur
            progress["status"] = "error"
            progress["message"] = f"Une erreur est survenue : {str(e)}"
            logger.error(f"Erreur dans le traitement : {e}")

    # Récupération des fichiers et paramètres du formulaire
    input_file = request.files["input_file"]
    input_path = os.path.join(app.config["UPLOAD_FOLDER"], input_file.filename)
    input_file.save(input_path)
    logger.debug(f"Fichier principal téléchargé : {input_path}")

    glossary_csv = request.files.get("glossary_csv")
    glossary_csv_path = None
    if glossary_csv:
        glossary_csv_path = os.path.join(app.config["UPLOAD_FOLDER"], glossary_csv.filename)
        glossary_csv.save(glossary_csv_path)
        logger.debug(f"Glossaire CSV téléchargé : {glossary_csv_path}")

        if glossary_csv_path.endswith(".xlsx"):
            glossary_csv_path = convert_excel_to_csv(glossary_csv_path, glossary_csv_path.replace(".xlsx", ".csv"))
            logger.debug(f"Glossaire Excel converti en CSV : {glossary_csv_path}")

    glossary_gpt = request.files.get("glossary_gpt")
    glossary_gpt_path = None
    if glossary_gpt:
        glossary_gpt_path = os.path.join(app.config["UPLOAD_FOLDER"], glossary_gpt.filename)
        glossary_gpt.save(glossary_gpt_path)
        logger.debug(f"Glossaire GPT téléchargé : {glossary_gpt_path}")

    # Récupération du nom de fichier de sortie depuis le formulaire
    output_file_name = request.form.get("output_file_name", "improved_output.docx")
    final_output_path = os.path.join(app.config["DOWNLOAD_FOLDER"], output_file_name)

    # Paramètres pour le traitement en arrière-plan
    thread_args = {
        "glossary_csv_path": glossary_csv_path,
        "glossary_gpt_path": glossary_gpt_path,
        "source_language": request.form["source_language"],
        "target_language": request.form["target_language"],
        "language_level": request.form["language_level"],
        "group_size": int(request.form["group_size"]),
        "gpt_model": request.form["gpt_model"],
    }

    # Lancer le traitement en arrière-plan
    threading.Thread(target=background_process, args=(input_path, final_output_path), kwargs=thread_args).start()

    # Rediriger vers la page "Traduction en cours..."
    return redirect(url_for("processing"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Utiliser le port fourni par Render
    app.run(debug=True, host="0.0.0.0", port=port)
