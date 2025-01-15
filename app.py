from flask import Flask, render_template, redirect, url_for
from translation_app.routes import translation_bp
from calculator_app.routes import calculator_bp
import os

app = Flask(__name__)

# Configuration des dossiers
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER
app.config["SECRET_KEY"] = "your_secret_key"

# Enregistrement des blueprints pour les deux sous-applications
app.register_blueprint(translation_bp, url_prefix="/translation")
app.register_blueprint(calculator_bp, url_prefix="/calculator")

@app.route("/")
def main_menu():
    """Menu principal avec deux boutons et tableau des fichiers traduits."""
    return render_template("main_menu.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
