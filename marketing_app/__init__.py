from flask import Blueprint

marketing_bp = Blueprint('marketing', __name__)

from . import routes
