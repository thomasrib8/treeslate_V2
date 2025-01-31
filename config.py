import os

# Définir le répertoire de base
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Classe principale de configuration pour Flask.
    """
    # Clé secrète pour Flask (à utiliser pour les sessions)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')

    # Clés API pour les services externes
    DEEPL_API_KEY = os.environ.get('DEEPL_API_KEY', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

    # Répertoire de stockage persistant sur Render
    PERSISTENT_STORAGE = os.getenv("PERSISTENT_STORAGE", "/var/data/")

   # Dossiers pour les fichiers (utilisant le stockage persistant)
    UPLOAD_FOLDER = os.path.join(PERSISTENT_STORAGE, "uploads")
    DOWNLOAD_FOLDER = os.path.join(PERSISTENT_STORAGE, "downloads")
    MARKETING_FOLDER = os.path.join(DOWNLOAD_FOLDER, "marketing")

    # Dossiers pour les glossaires
    GLOSSARY_FOLDER = os.path.join(PERSISTENT_STORAGE, "glossaries")
    DEEPL_GLOSSARY_FOLDER = os.path.join(GLOSSARY_FOLDER, "deepl")
    GPT_GLOSSARY_FOLDER = os.path.join(GLOSSARY_FOLDER, "chatgpt")

    # Création des répertoires s'ils n'existent pas
    @staticmethod
    def create_directories():
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.DOWNLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.MARKETING_FOLDER, exist_ok=True)
        os.makedirs(Config.GLOSSARY_FOLDER, exist_ok=True)
        os.makedirs(Config.DEEPL_GLOSSARY_FOLDER, exist_ok=True)
        os.makedirs(Config.GPT_GLOSSARY_FOLDER, exist_ok=True)

    # Configuration des sessions
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = os.path.join(BASE_DIR, ".flask_session")  
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # Configuration Flask-HTTPAuth pour l'authentification
    USERS = {
        "admin": os.environ.get('ADMIN_PASSWORD', 'Roue2021*'),
        "thomas": os.environ.get('USER_PASSWORD', 'Roue2021*'),
        "victor": os.environ.get('EDITOR_PASSWORD', 'Roue2021*'),
        "florian": os.environ.get('VIEWER_PASSWORD', 'Roue2021*')
    }

    # Configuration Flask-HTTPAuth pour HTTP Basic Auth
    AUTH_REALM = "Authentification requise"
    AUTH_ERROR_MESSAGE = "Nom d'utilisateur ou mot de passe incorrect."

class DevelopmentConfig(Config):
    """
    Configuration spécifique pour le développement.
    """
    DEBUG = True
    TESTING = False
    FLASK_ENV = "development"

class ProductionConfig(Config):
    """
    Configuration spécifique pour la production.
    """
    DEBUG = False
    TESTING = False
    FLASK_ENV = "production"
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super_secret_key_for_production')

class TestingConfig(Config):
    """
    Configuration spécifique pour les tests.
    """
    TESTING = True
    DEBUG = True
    SESSION_TYPE = "null"  # Désactiver les sessions pour les tests
