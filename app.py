from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import os
import threading
from your_script import translate_docx_with_deepl, improve_translation, create_glossary, convert_excel_to_csv

app = Flask(__name__)

# Configuration des dossiers
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER

DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Authentification HTTP
auth = HTTPBasicAuth()

# Utilisateurs autorisés
users = {
    "admin": generate_password_hash("Roue2021*"),  # Remplacez par votre mot de passe
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

# Variable globale pour suivre le statut du traitement
progress = {"status": "idle", "message": ""}

@app.route("/uploads/<filename>")
def serve_uploads(filename):
    """
    Sert les fichiers du dossier uploads.
    """
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/")
@auth.login_required
def index():
    """
    Page principale affichant le formulaire de téléchargement et les options.
    """
    return render_template("index.html")

@app.route("/processing")
@auth.login_required
def processing():
    """
    Page intermédiaire affichant "Traduction en cours...".
    """
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
    return jsonify(progress)

@app.route("/downloads/<filename>")
@auth.login_required
def download_file(filename):
    """
    Permet à l'utilisateur de télécharger le fichier traduit.
    """
    return send_from_directory(app.config["DOWNLOAD_FOLDER"], filename, as_attachment=True)

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

            # Gestion du glossaire DeepL
            glossary_id = None
            if kwargs.get("glossary_csv_path"):
                progress["message"] = "Création du glossaire..."
                glossary_id = create_glossary(
                    api_key=DEEPL_API_KEY,
                    name="MyGlossary",
                    source_lang=kwargs["source_language"],
                    target_lang=kwargs["target_language"],
                    glossary_path=kwargs["glossary_csv_path"],
                )

            # Traduction avec DeepL
            progress["message"] = "Traduction avec DeepL..."
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
            progress["message"] = "Amélioration avec ChatGPT..."
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

        except Exception as e:
            progress["status"] = "error"
            progress["message"] = f"Une erreur est survenue : {str(e)}"

    # Récupération des fichiers et paramètres du formulaire
    input_file = request.files["input_file"]
    input_path = os.path.join(app.config["UPLOAD_FOLDER"], input_file.filename)
    input_file.save(input_path)

    # Gestion du glossaire
    glossary_file = request.files.get("glossary_file")
    glossary_csv_path = None
    if glossary_file:
        glossary_extension = os.path.splitext(glossary_file.filename)[1].lower()
        glossary_path = os.path.join(app.config["UPLOAD_FOLDER"], glossary_file.filename)
        glossary_file.save(glossary_path)

        if glossary_extension == ".xlsx":
            glossary_csv_path = os.path.join(app.config["UPLOAD_FOLDER"], "converted_glossary.csv")
            convert_excel_to_csv(glossary_path, glossary_csv_path)
        elif glossary_extension == ".csv":
            glossary_csv_path = glossary_path
        else:
            progress["status"] = "error"
            progress["message"] = "Format de glossaire non supporté (uniquement .csv ou .xlsx)."
            return redirect(url_for("processing"))

    glossary_gpt = request.files.get("glossary_gpt")
    glossary_gpt_path = None
    if glossary_gpt:
        glossary_gpt_path = os.path.join(app.config["UPLOAD_FOLDER"], glossary_gpt.filename)
        glossary_gpt.save(glossary_gpt_path)

    # Récupération du nom de fichier de sortie depuis le formulaire
    output_file_name = request.form.get("output_file_name", "improved_output.docx")
    final_output_path = os.path.join(app.config["DOWNLOAD_FOLDER"], output_file_name)

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

    return redirect(url_for("processing"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
