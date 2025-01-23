import os

class Config:
    """
    Classe principale de configuration pour Flask.
    """
    # Clé secrète pour Flask (à utiliser pour les sessions)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')

    # Clés API pour les services externes
    DEEPL_API_KEY = os.environ.get('DEEPL_API_KEY', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

    # Dossiers pour les fichiers
    BASE_DIR = os.getcwd()
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")

    # Dossiers pour les glossaires
    GLOSSARY_FOLDER = os.path.join(BASE_DIR, "glossaries")
    DEEPL_GLOSSARY_FOLDER = os.path.join(GLOSSARY_FOLDER, "deepl")
    GPT_GLOSSARY_FOLDER = os.path.join(GLOSSARY_FOLDER, "chatgpt")

    # Configuration des sessions
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = os.path.join(BASE_DIR, ".flask_session")
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # Configuration Flask-HTTPAuth
    USERS = {
        "admin": os.environ.get('ADMIN_PASSWORD', 'Roue2021*'),
        "user": os.environ.get('USER_PASSWORD', 'Roue2021*'),
        "editor": os.environ.get('EDITOR_PASSWORD', 'Roue2021*'),
        "viewer": os.environ.get('VIEWER_PASSWORD', 'Roue2021*')
    }

class DevelopmentConfig(Config):
    """
    Configuration spécifique pour le développement.
    """
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """
    Configuration spécifique pour la production.
    """
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super_secret_key_for_production')

class TestingConfig(Config):
    """
    Configuration spécifique pour les tests.
    """
    TESTING = True
    DEBUG = True
    SESSION_TYPE = "null"  # Désactiver les sessions pour les tests
