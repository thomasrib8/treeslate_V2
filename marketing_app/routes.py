from flask import Blueprint, render_template, request, jsonify, send_file
import os

marketing_bp = Blueprint('marketing', __name__)

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
def index():
    return render_template('upload.html')  # ou une autre page

@marketing_bp.route('/marketing', methods=['GET'])
def marketing_home():
    # Liste les fichiers présents dans le dossier marketing/download
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            files.append({
                'filename': filename,
                'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
            })

    return render_template('marketing/upload.html', marketing_files=files)
    
@marketing_bp.route('/marketing/marketing/upload', methods=['POST'])
def upload_marketing_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "Aucun fichier sélectionné."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nom de fichier invalide."}), 400

    # Vérifier si le dossier existe avant d'enregistrer le fichier
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)  # Crée le dossier s'il n'existe pas

    file_path = os.path.join(DOWNLOAD_FOLDER, file.filename)
    file.save(file_path)

    return jsonify({"success": True, "filename": file.filename}), 200

@marketing_bp.route('/marketing/get_uploaded_files', methods=['GET'])
def get_uploaded_files():
    if not os.path.exists(DOWNLOAD_FOLDER):
        return jsonify([])  # Si le dossier n'existe pas encore, on retourne une liste vide

    files = []
    for filename in os.listdir(DOWNLOAD_FOLDER):
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            files.append({
                "filename": filename,
                "created_at": os.path.getctime(file_path)  # Timestamp de création du fichier
            })

    return jsonify(files)

@marketing_bp.route('/marketing/files', methods=['GET'])
def list_files():
    files = os.listdir(DOWNLOAD_FOLDER)
    return jsonify(files)

@marketing_bp.route('/marketing/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Fichier non trouvé'}), 404
