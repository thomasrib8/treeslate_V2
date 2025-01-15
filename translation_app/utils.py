# translation_app/utils.py

import pandas as pd
from docx import Document
import os

def convert_excel_to_csv(excel_path, csv_path):
    """
    Convertit un fichier Excel (.xlsx) en fichier CSV pour DeepL.
    
    Args:
        excel_path (str): Chemin du fichier Excel d'entrée.
        csv_path (str): Chemin du fichier CSV de sortie.

    Returns:
        str: Chemin du fichier CSV généré.
    """
    try:
        df = pd.read_excel(excel_path, header=None)
        df.to_csv(csv_path, index=False, header=False)
        return csv_path
    except Exception as e:
        raise Exception(f"Erreur lors de la conversion d'Excel en CSV : {str(e)}")

def read_glossary(docx_path):
    """
    Lit un glossaire à partir d'un fichier .docx et le retourne sous forme de dictionnaire.
    
    Args:
        docx_path (str): Chemin du fichier .docx contenant le glossaire.

    Returns:
        dict: Glossaire sous forme de paires clé-valeur.
    """
    glossary = {}
    try:
        doc = Document(docx_path)
        for line in doc.paragraphs:
            if ":" in line.text:
                source, target = line.text.split(":", 1)
                glossary[source.strip()] = target.strip()
        return glossary
    except Exception as e:
        raise Exception(f"Erreur lors de la lecture du glossaire : {str(e)}")

def save_translation_metadata(output_file_name, metadata_file="translations_metadata.csv"):
    """
    Sauvegarde les métadonnées d'un fichier traduit dans un fichier CSV.

    Args:
        output_file_name (str): Nom du fichier traduit.
        metadata_file (str): Chemin du fichier CSV contenant les métadonnées.
    """
    from datetime import datetime

    data = {
        "File Name": output_file_name,
        "Date Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Si le fichier n'existe pas, crée un nouveau CSV avec un en-tête
    if not os.path.exists(metadata_file):
        df = pd.DataFrame([data])
        df.to_csv(metadata_file, index=False)
    else:
        # Sinon, ajoute une nouvelle ligne au CSV existant
        df = pd.read_csv(metadata_file)
        df = df.append(data, ignore_index=True)
        df.to_csv(metadata_file, index=False)

def load_translation_metadata(metadata_file="translations_metadata.csv"):
    """
    Charge les métadonnées des fichiers traduits à partir d'un fichier CSV.

    Args:
        metadata_file (str): Chemin du fichier CSV contenant les métadonnées.

    Returns:
        pandas.DataFrame: DataFrame contenant les métadonnées des traductions.
    """
    if os.path.exists(metadata_file):
        return pd.read_csv(metadata_file)
    else:
        return pd.DataFrame(columns=["File Name", "Date Created"])
