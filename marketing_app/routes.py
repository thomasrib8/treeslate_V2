from flask import Blueprint, render_template, request, jsonify, send_from_directory
import os
from datetime import datetime

marketing_bp = Blueprint('marketing', __name__, url_prefix='/marketing')

# Définition du dossier d'upload des fichiers
UPLOAD_FOLDER = os.path.join(os.getcwd(), "marketing", "download")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # S'assure que le dossier existe

def allowed_file(filename):
    """ Vérifie si l'extension du fichier est autorisée (ici, DOCX et TXT). """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'docx', 'txt'}

@marketing_bp.route('/')
def marketing_home():
    """Affiche la page d'upload des fichiers marketing"""
    files = get_uploaded_files_data()
    return render_template('marketing/upload.html', marketing_files=files)

@marketing_bp.route('/upload', methods=['POST'])
def upload_marketing_file():
    """Gère l'upload des fichiers"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "Aucun fichier fourni"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nom de fichier invalide"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    print(f"DEBUG - Fichier {file.filename} sauvegardé dans {UPLOAD_FOLDER}")  # Log pour voir l'upload

    return jsonify({"success": True, "filename": file.filename})

@marketing_bp.route('/get_uploaded_files', methods=['GET'])
def get_uploaded_files():
    """Renvoie la liste des fichiers uploadés en JSON"""
    files = get_uploaded_files_data()
    return jsonify(files)

@marketing_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Permet de télécharger un fichier depuis le dossier d'upload"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    else:
        return jsonify({"success": False, "error": "Fichier non trouvé"}), 404

def get_uploaded_files_data():
    """Récupère les fichiers avec leur date de création"""
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            files.append({
                "filename": filename,
                "created_at": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()  # Format ISO
            })
    return files
