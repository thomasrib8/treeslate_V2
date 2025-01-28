import openai
import os
from fpdf import FPDF
from flask import current_app
from charset_normalizer import detect
import logging

logger = logging.getLogger(__name__)

# Prompts pour ChatGPT
COMMERCIAL_PROMPT = """
À partir du fichier fourni contenant le contenu d'un livre, génère une fiche commerciale mettant en avant le livre en respectant la structure suivante :

1 - Présentation Générale : Présente brièvement le livre en précisant son titre, son auteur, son genre et son objectif principal. Donne un aperçu de la thématique abordée et du public cible.

2 - Contenu et Chapitres Clés : Décris les principaux chapitres ou parties du livre, en mettant en lumière les thèmes majeurs traités. Explique comment le contenu est structuré pour captiver le lecteur.

3 - Points Forts : Identifie et développe les aspects qui rendent ce livre unique ou particulièrement intéressant (style, originalité, pertinence, sources utilisées, etc.). Mets en avant les qualités rédactionnelles et la crédibilité de l'auteur.

4 - Avantages et Bénéfices de la Lecture : Explique en quoi la lecture de ce livre apporte une réelle valeur ajoutée au lecteur. Développe les bénéfices pratiques, éducatifs ou émotionnels que le lecteur peut en tirer.

5 - Conclusion : Propose une conclusion engageante qui incite à l'achat ou à la lecture en rappelant les points essentiels du livre et en soulignant son utilité.

Utilise un ton engageant et professionnel, avec un style fluide et convaincant.
"""

SHOPIFY_PROMPT = """
À partir du fichier fourni contenant le contenu du livre, génère une fiche produit détaillée pour un site internet en respectant la structure suivante :

1 - Présentation Générale : Introduis brièvement le livre en une ou deux phrases, en précisant le titre, l’auteur, et le genre. Développe ensuite, en deux paragraphes, l'objectif principal du livre en donnant un aperçu de la thématique abordée, en mettant en lumière les thèmes majeurs traités, le public cible, et en expliquant comment le contenu est structuré pour captiver le lecteur.

2- Contenu et Chapitres : Présente la table des matières en détaillant chaque chapitre, en soulignant les thèmes abordés et la valeur ajoutée qu'ils apportent au lecteur.

3 - Points Forts : Identifie quatre aspects majeurs qui rendent ce livre unique ou particulièrement intéressant (ex. style, originalité, pertinence, sources utilisées, etc.). Décris chaque point fort par une phrase courte, percutante et convaincante.

Adopte un ton engageant et professionnel, avec un style fluide et convaincant, en incitant subtilement à la découverte et à l’achat du livre.
"""

def process_commercial_sheet(file_path):
    output_folder = os.path.join("downloads", "marketing")
    return _generate_pdf(file_path, COMMERCIAL_PROMPT, "commercial", output_folder)

def process_shopify_sheet(file_path):
    output_folder = os.path.join("downloads", "marketing")
    return _generate_pdf(file_path, SHOPIFY_PROMPT, "shopify", output_folder)

def _generate_pdf(file_path, prompt_template, doc_type, output_folder):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        detected = detect(raw_data)
        encoding = detected.get('encoding', 'latin-1')
        logger.info(f"Encodage détecté : {encoding}")

    try:
        with open(file_path, 'r', encoding=encoding) as file:
            content = file.read()
    except UnicodeDecodeError as e:
        logger.warning(f"Erreur de décodage avec l'encodage {encoding}, utilisation de latin-1. Erreur : {e}")
        with open(file_path, 'r', encoding='latin-1') as file:
            content = file.read()

    # Générer les prompts pour ChatGPT
    french_prompt = f"{prompt_template}\n\nContenu du fichier:\n{content}\n\nLangue: Français"
    english_prompt = f"{prompt_template}\n\nContenu du fichier:\n{content}\n\nLangue: Anglais"

    # Appeler l'API ChatGPT
    french_text = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": french_prompt}]
    )["choices"][0]["message"]["content"]

    english_text = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": english_prompt}]
    )["choices"][0]["message"]["content"]

    # Créer le dossier de sortie
    os.makedirs(output_folder, exist_ok=True)
    french_pdf = os.path.join(output_folder, f"french_{doc_type}.pdf")
    english_pdf = os.path.join(output_folder, f"english_{doc_type}.pdf")

    # Sauvegarder les fichiers PDF
    _save_pdf(french_text, french_pdf)
    _save_pdf(english_text, english_pdf)

    return french_pdf, english_pdf

def _save_pdf(content, path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    pdf.output(path)

