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
    """Page d'accueil pour le téléchargement du fichier."""
    return render_template('marketing/upload.html')

@marketing_bp.route('/marketing/upload', methods=['POST'])
def upload_marketing_file():
    """Route pour gérer l'upload et le traitement du fichier."""
    # Création des dossiers nécessaires s'ils n'existent pas
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    # Vérification du fichier envoyé
    file = request.files.get('file')
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Type de fichier non pris en charge. Veuillez fournir un fichier .docx.'}), 400

    # Sauvegarde du fichier dans le dossier des uploads
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Vérification de l'action spécifiée (génération commerciale ou Shopify)
    action = request.form.get('action')
    if not action:
        return jsonify({'error': 'Aucune action spécifiée'}), 400

    # Analyse globale du fichier en chunks
    try:
        consolidated_analysis = analyze_chunks(file_path)
    except Exception as e:
        return jsonify({'error': f"Erreur lors de l'analyse du fichier : {str(e)}"}), 500

    # Génération des fiches en fonction de l'action choisie
    try:
        if action == 'generate_commercial':
            french_text, english_text = generate_final_fiche(consolidated_analysis, "COMMERCIAL_PROMPT")
        elif action == 'generate_shopify':
            french_text, english_text = generate_final_fiche(consolidated_analysis, "SHOPIFY_PROMPT")
        else:
            return jsonify({'error': 'Action inconnue'}), 400
    except Exception as e:
        return jsonify({'error': f"Erreur lors de la génération des fiches : {str(e)}"}), 500

    # Sauvegarde des fichiers PDF générés
    try:
        french_pdf = os.path.join(DOWNLOAD_FOLDER, "french.pdf")
        english_pdf = os.path.join(DOWNLOAD_FOLDER, "english.pdf")
        save_pdf(french_text, french_pdf)
        save_pdf(english_text, english_pdf)
    except Exception as e:
        return jsonify({'error': f"Erreur lors de la sauvegarde des PDF : {str(e)}"}), 500

    # Rendu de la page des résultats
    return render_template(
        'marketing/result.html',
        french_pdf=f"marketing/download/{os.path.basename(french_pdf)}",
        english_pdf=f"marketing/download/{os.path.basename(english_pdf)}"
    )

@marketing_bp.route('/marketing/download/<filename>', methods=['GET'])
def download_file(filename):
    """Route pour télécharger les fichiers PDF générés."""
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Fichier non trouvé'}), 404
