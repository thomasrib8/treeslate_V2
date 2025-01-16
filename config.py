import os

# Clé secrète pour Flask
SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')

# Clés API
DEEPL_API_KEY = os.environ.get('DEEPL_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Dossiers
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
