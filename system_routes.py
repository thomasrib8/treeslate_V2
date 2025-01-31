import shutil
from flask import Blueprint, jsonify

system_bp = Blueprint('system', __name__)

@system_bp.route("/disk_usage", methods=["GET"])
def get_disk_usage():
    total, used, free = shutil.disk_usage("/")  # 📌 Récupère l'espace disque total, utilisé et libre

    disk_info = {
        "total": f"{total // (1024**3)} GB",
        "used": f"{used // (1024**3)} GB",
        "free": f"{free // (1024**3)} GB"
    }

    return jsonify(disk_info)
