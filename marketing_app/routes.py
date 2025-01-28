from flask import render_template, request, jsonify, current_app, send_file
import os
from .utils import process_commercial_sheet, process_shopify_sheet
from . import marketing_bp  # Importez le blueprint correctement

@marketing_bp.route('/marketing', methods=['GET'])
def marketing_home():
    return render_template('marketing/upload.html')

@marketing_bp.route('/marketing/upload', methods=['POST'])
def upload_marketing_file():
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    download_folder = current_app.config["DOWNLOAD_FOLDER"]

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    file_path = os.path.join(upload_folder, file.filename)
    file.save(file_path)

    action = request.form.get('action')
    if action == 'generate_commercial':
        french_pdf, english_pdf = process_commercial_sheet(file_path)
    elif action == 'generate_shopify':
        french_pdf, english_pdf = process_shopify_sheet(file_path)
    else:
        return jsonify({'error': 'Action inconnue'}), 400

    return render_template(
        'marketing/result_commercial.html' if action == 'generate_commercial' else 'marketing/result_shopify.html',
        french_pdf=french_pdf,
        english_pdf=english_pdf
    )

@marketing_bp.route('/marketing/download/<filename>', methods=['GET'])
def download_file(filename):
    download_folder = current_app.config["DOWNLOAD_FOLDER"]
    file_path = os.path.join(download_folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Fichier non trouvé'}), 404
