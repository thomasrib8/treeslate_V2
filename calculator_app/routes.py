from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from calculator_app.python_docx import (
    get_docx_stats,
    calculate_translation_time,
    calculate_translation_cost,
    calculate_review_cost,
)

calculator_bp = Blueprint("calculator", __name__, template_folder="templates")

# Configuration des dossiers
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@calculator_bp.route("/", methods=["GET", "POST"])
def index():
    """Affiche l'interface principale de la calculette."""
    if request.method == "POST":
        # Récupération des données du formulaire
        file = request.files.get("file")
        group_size = int(request.form.get("group_size", 1))
        reviewer_choice = request.form.get("reviewer")

        if not file:
            flash("Veuillez télécharger un fichier.", "error")
            return redirect(url_for("calculator.index"))

        # Enregistrer le fichier téléchargé
        file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(file_path)

        # Calculs basés sur le fichier
        try:
            words, characters, pages, paragraphs = get_docx_stats(file_path)
            translation_time, translation_time_sec = calculate_translation_time(words, paragraphs, group_size)
            translation_time_min = translation_time_sec / 60
            translation_cost = calculate_translation_cost(words, characters, translation_time_min)
            review_cost = calculate_review_cost(pages, reviewer_choice)
            total_cost = translation_cost + review_cost

            return render_template(
                "calculator/result.html",
                words=words,
                characters=characters,
                pages=pages,
                paragraphs=paragraphs,
                translation_time=str(translation_time),
                translation_cost=round(translation_cost, 6),
                review_cost=round(review_cost, 2),
                total_cost=round(total_cost, 6),
            )
        except Exception as e:
            flash(f"Erreur lors du traitement du fichier : {e}", "error")
            return redirect(url_for("calculator.index"))

    return render_template("calculator/index.html")
