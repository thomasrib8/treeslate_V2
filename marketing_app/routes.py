from flask import Blueprint, render_template, request, jsonify, current_app, send_file
import os
from .utils import analyze_chunks, generate_final_fiche, save_pdf

marketing_bp = Blueprint('marketing', __name__)
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads/marketing"

# Extensions autorisées
ALLOWED_EXTENSIONS = {'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@marketing_bp.route('/marketing', methods=['GET'])
def marketing_home():
    return render_template('marketing/upload.html')

@marketing_bp.route('/marketing/upload', methods=['POST'])
def upload_marketing_file():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    file = request.files.get('file')
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Type de fichier non pris en charge. Veuillez fournir un fichier .docx.'}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    action = request.form.get('action')
    if not action:
        return jsonify({'error': 'Aucune action spécifiée'}), 400

    # Analyse globale du fichier
    consolidated_analysis = analyze_chunks(file_path)

    # Génération des fiches
    if action == 'generate_commercial':
        french_text, english_text = generate_final_fiche(consolidated_analysis, "COMMERCIAL_PROMPT")
    elif action == 'generate_shopify':
        french_text, english_text = generate_final_fiche(consolidated_analysis, "SHOPIFY_PROMPT")
    else:
        return jsonify({'error': 'Action inconnue'}), 400

    # Sauvegarder les PDF
    french_pdf = os.path.join(DOWNLOAD_FOLDER, "french.pdf")
    english_pdf = os.path.join(DOWNLOAD_FOLDER, "english.pdf")
    save_pdf(french_text, french_pdf)
    save_pdf(english_text, english_pdf)

    return render_template(
        'marketing/result.html',
        french_pdf=french_pdf,
        english_pdf=english_pdf
    )

@marketing_bp.route('/marketing/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Fichier non trouvé'}), 404
