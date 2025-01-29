from flask import Blueprint, render_template, request, jsonify, send_file
import os

marketing_bp = Blueprint('marketing', __name__)

UPLOAD_FOLDER = "marketing/download"

# Vérifier si le dossier de téléchargement existe, sinon le créer
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """ Vérifie si l'extension du fichier est autorisée (ici, DOCX et TXT). """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'docx', 'txt'}

@marketing_bp.route('/')
def index():
    return render_template('upload.html')  # ou une autre page

@marketing_bp.route('/marketing', methods=['GET'])
def marketing_home():
    """ Affiche la page d'upload. """
    return render_template('marketing/upload.html')

@marketing_bp.route('/marketing/upload', methods=['POST'])
def upload_marketing_file():
    """ Gère l'upload et enregistre le fichier dans `marketing/download`. """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni.'}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Type de fichier non pris en charge. Seuls les fichiers .docx et .txt sont acceptés.'}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    return jsonify({'message': 'Fichier uploadé avec succès.', 'filename': file.filename}), 200

@marketing_bp.route('/marketing/download/<filename>', methods=['GET'])
def download_file(filename):
    """ Permet de télécharger un fichier depuis `marketing/download`. """
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    
    return jsonify({'error': 'Fichier non trouvé'}), 404
