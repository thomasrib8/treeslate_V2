from flask import Blueprint, render_template, request, jsonify, current_app, send_file, redirect, url_for
import os
from .utils import (
    analyze_chunks, 
    generate_final_fiche, 
    save_pdf, 
    convert_docx_to_txt, 
    extract_title_and_author,
    COMMERCIAL_PROMPT, 
    SHOPIFY_PROMPT
)

marketing_bp = Blueprint('marketing', __name__)
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads/marketing"

# Extensions autorisées
ALLOWED_EXTENSIONS = {'docx'}

def allowed_file(filename):
    """ Vérifie si le fichier a une extension autorisée """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@marketing_bp.route('/marketing', methods=['GET'])
def marketing_home():
    """ Affiche la page d’upload des fichiers """
    return render_template('marketing/upload.html')

@marketing_bp.route('/marketing/upload', methods=['POST'])
def upload_marketing_file():
    """ Gère l’upload et le traitement du fichier DOCX """
    
    # Vérification et création des dossiers nécessaires
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    file = request.files.get('file')
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Type de fichier non pris en charge. Veuillez fournir un fichier .docx.'}), 400

    # Sauvegarde du fichier
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Conversion en texte brut
    txt_path = convert_docx_to_txt(file_path)
    
    # Analyse du fichier
    consolidated_analysis = analyze_chunks(txt_path)

    # Extraction du titre et de l'auteur pour les noms de fichiers
    title, author = extract_title_and_author(txt_path)
    if not title:
        title = "Fiche_Produit"
    if not author:
        author = "Auteur_Inconnu"

    # Nettoyage du titre et de l’auteur pour éviter les caractères spéciaux dans les noms de fichiers
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
    safe_author = "".join(c for c in author if c.isalnum() or c in (" ", "_", "-")).strip()

    action = request.form.get('action')
    if not action:
        return jsonify({'error': 'Aucune action spécifiée'}), 400

    # Génération des fiches
    if action == 'generate_commercial':
        french_text, english_text = generate_final_fiche(consolidated_analysis, COMMERCIAL_PROMPT)
        file_prefix = "Fiche_Commerciale"
    elif action == 'generate_shopify':
        french_text, english_text = generate_final_fiche(consolidated_analysis, SHOPIFY_PROMPT)
        file_prefix = "Fiche_Produit"
    else:
        return jsonify({'error': 'Action inconnue'}), 400

    # Définition des chemins des fichiers générés
    french_pdf = os.path.join(DOWNLOAD_FOLDER, f"{file_prefix}_{safe_title}_{safe_author}_FR.pdf")
    english_pdf = os.path.join(DOWNLOAD_FOLDER, f"{file_prefix}_{safe_title}_{safe_author}_EN.pdf")

    # Sauvegarde en PDF
    save_pdf(french_text, french_pdf)
    save_pdf(english_text, english_pdf)

    # Redirection vers la page de confirmation
    return render_template(
        'marketing/result.html',
        french_pdf=french_pdf,
        english_pdf=english_pdf,
        title=title,
        author=author
    )

@marketing_bp.route('/marketing/download/<filename>', methods=['GET'])
def download_file(filename):
    """ Permet de télécharger un fichier généré """
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Fichier non trouvé'}), 404

