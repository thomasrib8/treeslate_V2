from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import threading
from your_script import translate_docx_with_deepl, improve_translation, create_glossary

app = Flask(__name__)

# Configuration des dossiers
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Variable globale pour suivre le statut du traitement
progress = {"status": "idle", "message": ""}

@app.route("/")
def index():
    """
    Page principale affichant le formulaire de téléchargement et les options.
    """
    return render_template("index.html")

@app.route("/processing")
def processing():
    """
    Page intermédiaire affichant "Traduction en cours...".
    """
    return render_template("processing.html")

@app.route("/done")
def done():
    """
    Page finale affichant "Traduction terminée".
    """
    return render_template("done.html")

@app.route("/check_status")
def check_status():
    """
    Vérifie le statut du traitement en cours.
    """
    return jsonify(progress)

@app.route("/process", methods=["POST"])
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

            # Mise à jour pour indiquer que le traitement est terminé
            progress["status"] = "done"
            progress["message"] = f"Traitement terminé avec succès. Le fichier est enregistré dans {final_output_path}"

        except Exception as e:
            # Mise à jour en cas d'erreur
            progress["status"] = "error"
            progress["message"] = f"Une erreur est survenue : {str(e)}"

    # Récupération des fichiers et paramètres du formulaire
    input_file = request.files["input_file"]
    input_path = os.path.join(app.config["UPLOAD_FOLDER"], input_file.filename)
    input_file.save(input_path)

    glossary_csv = request.files.get("glossary_csv")
    glossary_csv_path = None
    if glossary_csv:
        glossary_csv_path = os.path.join(app.config["UPLOAD_FOLDER"], glossary_csv.filename)
        glossary_csv.save(glossary_csv_path)

    glossary_gpt = request.files.get("glossary_gpt")
    glossary_gpt_path = None
    if glossary_gpt:
        glossary_gpt_path = os.path.join(app.config["UPLOAD_FOLDER"], glossary_gpt.filename)
        glossary_gpt.save(glossary_gpt_path)

    # Récupération du nom de fichier de sortie depuis le formulaire
    output_file_name = request.form.get("output_file_name", "improved_output.docx")

    # Identifier le dossier Téléchargements de l'utilisateur
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    final_output_path = os.path.join(downloads_folder, output_file_name)

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

