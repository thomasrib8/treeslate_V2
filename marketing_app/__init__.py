from flask import Blueprint

# Initialisation du blueprint
marketing_bp = Blueprint('marketing', __name__)

from . import routes  # Importez les routes après avoir défini le blueprint
