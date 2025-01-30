from flask import Blueprint, render_template, request, jsonify, send_file
import os
from datetime import datetime

marketing_bp = Blueprint('marketing', __name__)
marketing_bp = Blueprint('marketing', __name__, url_prefix='/marketing')

DOWNLOAD_FOLDER = 'marketing/download'  # Assurez-vous que ce dossier existe bien
UPLOAD_FOLDER = "marketing/download"

# Vérifier si le dossier de téléchargement existe, sinon le créer
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Définition du répertoire de stockage des fichiers
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "marketing", "download")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)  # Assure que le dossier existe

def allowed_file(filename):
    """ Vérifie si l'extension du fichier est autorisée (ici, DOCX et TXT). """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'docx', 'txt'}

@marketing_bp.route('/')
def main_menu():
    files = []
    if os.path.exists(DOWNLOAD_FOLDER):
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                files.append({
                    'filename': filename,
                    'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                })
    return render_template('main_menu.html', marketing_files=files)

@marketing_bp.route('/marketing', methods=['GET'])
def marketing_home():
    """Affiche la page d'upload et liste les fichiers existants."""
    files = []
    if os.path.exists(DOWNLOAD_FOLDER):
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            files.append({
                'filename': filename,
                'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
            })
    return render_template('marketing/upload.html', marketing_files=files)
    
@marketing_bp.route('/marketing/upload', methods=['POST'])
def upload_marketing_file():
    """Gère l'upload des fichiers marketing."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné.'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nom de fichier invalide.'})

    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    file_path = os.path.join(DOWNLOAD_FOLDER, file.filename)
    file.save(file_path)

    return jsonify({'success': True, 'filename': file.filename})

@marketing_bp.route('/get_uploaded_files')
def get_uploaded_files():
    """Renvoie la liste des fichiers marketing en JSON."""
    files = []
    if os.path.exists(DOWNLOAD_FOLDER):
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            files.append({
                'filename': filename,
                'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
            })
    return jsonify(files)

@marketing_bp.route('/marketing/files', methods=['GET'])
def list_files():
    files = os.listdir(DOWNLOAD_FOLDER)
    return jsonify(files)

@marketing_bp.route('/download/<filename>')
def download_file(filename):
    """Télécharge un fichier marketing."""
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'success': False, 'error': 'Fichier introuvable.'}), 404
