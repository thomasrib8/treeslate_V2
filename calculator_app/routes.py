from flask import Blueprint, render_template, request
from calculator_app.python_docx import get_docx_stats, calculate_translation_time, calculate_translation_cost, calculate_review_cost

calculator_bp = Blueprint("calculator", __name__, template_folder="templates")

@calculator_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["file"]
        group_size = int(request.form["group_size"])
        reviewer_choice = request.form["reviewer"]

        # Analyse du fichier
        file_path = f"uploads/{file.filename}"
        file.save(file_path)
        words, characters, pages, paragraphs = get_docx_stats(file_path)

        # Calculs
        translation_time, translation_time_sec = calculate_translation_time(words, paragraphs, group_size)
        translation_cost = calculate_translation_cost(words, characters, translation_time_sec / 60)
        review_cost = calculate_review_cost(words, reviewer_choice)
        total_cost = translation_cost + review_cost

        return render_template("result.html", words=words, characters=characters, paragraphs=paragraphs,
                               translation_time=str(translation_time), translation_cost=round(translation_cost, 6),
                               review_cost=round(review_cost, 2), total_cost=round(total_cost, 6))
    return render_template("index_calculator.html")
