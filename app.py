from flask import Flask, render_template, redirect, url_for, jsonify, request
from translation_app.routes import translation_bp
from calculator_app.routes import calculator_bp
import os
import time

app = Flask(__name__)

# Configuration des dossiers
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER
app.config["SECRET_KEY"] = "your_secret_key"

# Clés API pour DeepL et OpenAI
app.config["DEEPL_API_KEY"] = os.getenv("DEEPL_API_KEY")
app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Enregistrement des blueprints pour les deux sous-applications
app.register_blueprint(translation_bp, url_prefix="/translation")
app.register_blueprint(calculator_bp, url_prefix="/calculator")

# Variable globale pour gérer le statut
translation_status = {"status": "idle", "message": "Aucune tâche en cours."}

@app.route("/")
def main_menu():
    """
    Menu principal avec deux boutons et tableau des fichiers traduits.
    """
    try:
        files = []
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                files.append({
                    "name": filename,
                    "path": filepath,
                    "creation_date": os.path.getctime(filepath),
                })
        # Trier les fichiers par date de création (les plus récents en premier)
        files.sort(key=lambda x: x["creation_date"], reverse=True)
    except Exception as e:
        files = []
        print(f"Erreur lors du chargement des fichiers : {e}")

    return render_template("main_menu.html", files=files)

@app.route("/translation/process", methods=["POST"])
def process_translation():
    """
    Route pour lancer le traitement de la traduction.
    """
    global translation_status

    try:
        # Mettre à jour le statut à "processing"
        translation_status = {"status": "processing", "message": "Traitement en cours."}

        # Simuler un traitement synchrone (remplacez par votre logique réelle)
        time.sleep(5)  # Simule un délai de traitement
        
        # Exemple : Simuler un fichier traduit
        output_filename = "translated_file.docx"
        output_filepath = os.path.join(DOWNLOAD_FOLDER, output_filename)
        with open(output_filepath, "w") as file:
            file.write("Fichier traduit avec succès.")  # Exemple de contenu

        # Mettre à jour le statut à "done"
        translation_status = {"status": "done", "message": "Traduction terminée."}
    except Exception as e:
        # En cas d'erreur
        translation_status = {"status": "error", "message": str(e)}
    
    return redirect("/translation/processing")

@app.route("/check_status", methods=["GET"])
def check_status():
    """
    Route pour vérifier l'état du traitement.
    """
    global translation_status
    return jsonify(translation_status)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
