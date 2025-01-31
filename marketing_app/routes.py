from flask import Blueprint, render_template, request, jsonify, send_from_directory, current_app
import os
from datetime import datetime
import logging

# 📌 Ajout du logger
logger = logging.getLogger(__name__)

marketing_bp = Blueprint('marketing', __name__)

def allowed_file(filename):
    """ Vérifie si l'extension du fichier est autorisée (ici, DOCX et TXT). """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'docx', 'txt'}

def get_marketing_folder():
    with current_app.app_context():
        return current_app.config["MARKETING_FOLDER"]

@marketing_bp.route('/marketing')
def marketing_home():
    marketing_folder = get_marketing_folder()
    files = []

    if "MARKETING_FOLDER" in current_app.config and os.path.exists(marketing_folder):
        for filename in os.listdir(marketing_folder):
            file_path = os.path.join(marketing_folder, filename)
            if os.path.isfile(file_path):
                created_at = os.path.getctime(file_path)
                files.append({
                    "filename": filename,
                    "created_at": datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')
                })

    return render_template('marketing/upload.html', marketing_files=files)

@marketing_bp.route("/upload", methods=["POST"])
def upload_marketing_file():
    marketing_folder = current_app.config["MARKETING_FOLDER"]
    os.makedirs(marketing_folder, exist_ok=True)  # 📌 Assurer que le dossier existe

    if "file" not in request.files:
        return jsonify({"success": False, "message": "Aucun fichier sélectionné."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "Nom de fichier invalide."}), 400

    # 📌 Ajouter un timestamp pour éviter les conflits de nom de fichier
    filename, ext = os.path.splitext(file.filename)
    new_filename = f"{filename}_{int(time.time())}{ext}"
    file_path = os.path.join(marketing_folder, new_filename)

    # 📌 Sauvegarde du fichier
    file.save(file_path)

    # 📌 Vérifier si le fichier est bien sauvegardé
    if os.path.exists(file_path):
        logger.info(f"✅ Fichier marketing {new_filename} sauvegardé dans {marketing_folder}")
        return jsonify({"success": True, "message": f"Fichier {new_filename} uploadé avec succès."})
    else:
        logger.error(f"❌ Erreur : Le fichier {new_filename} n'a pas pu être sauvegardé.")
        return jsonify({"success": False, "message": "Erreur lors de l'enregistrement du fichier."}), 500

@marketing_bp.route('/get_uploaded_files', methods=['GET'])
def get_uploaded_files():
    marketing_folder = current_app.config["MARKETING_FOLDER"]
    files = []

    if os.path.exists(marketing_folder):
        for filename in os.listdir(marketing_folder):
            file_path = os.path.join(marketing_folder, filename)
            if os.path.isfile(file_path):
                created_at = os.path.getctime(file_path)
                files.append({
                    "filename": filename,
                    "created_at": datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')
                })

    return jsonify(files)

@marketing_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    marketing_folder = current_app.config["MARKETING_FOLDER"]

    if not os.path.exists(os.path.join(marketing_folder, filename)):
        return jsonify({"error": "Fichier non trouvé"}), 404

    return send_from_directory(marketing_folder, filename, as_attachment=True)

def get_uploaded_files_data():
    """Récupère les fichiers avec leur date de création"""
    files = []
    for filename in os.listdir(MARKETING_FOLDER):
        filepath = os.path.join(MARKETING_FOLDER, filename)
        if os.path.isfile(filepath):
            files.append({
                "filename": filename,
                "created_at": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()  # Format ISO
            })
    return files

@marketing_bp.route("/delete/<filename>", methods=["DELETE"])
def delete_marketing_file(filename):
    marketing_folder = current_app.config["MARKETING_FOLDER"]
    file_path = os.path.join(marketing_folder, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"🗑️ Fichier marketing supprimé : {file_path}")
        return jsonify({"success": True, "message": f"Le fichier {filename} a été supprimé."})
    else:
        logger.warning(f"⚠️ Tentative de suppression d'un fichier inexistant : {filename}")
        return jsonify({"success": False, "message": "Fichier introuvable."}), 404
