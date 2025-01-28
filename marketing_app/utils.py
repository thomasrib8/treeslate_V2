import openai
import os
from fpdf import FPDF
from flask import current_app
from docx import Document
import logging
import time

logger = logging.getLogger(__name__)

# Prompts pour ChatGPT
COMMERCIAL_PROMPT = """
À partir de l'analyse suivante d'un livre, génère une fiche commerciale mettant en avant le livre en respectant la structure suivante :

1 - Présentation Générale : Présente brièvement le livre en précisant son titre, son auteur, son genre et son objectif principal. Donne un aperçu de la thématique abordée et du public cible.

2 - Contenu et Chapitres Clés : Décris les principaux chapitres ou parties du livre, en mettant en lumière les thèmes majeurs traités. Explique comment le contenu est structuré pour captiver le lecteur.

3 - Points Forts : Identifie et développe les aspects qui rendent ce livre unique ou particulièrement intéressant (style, originalité, pertinence, sources utilisées, etc.). Mets en avant les qualités rédactionnelles et la crédibilité de l'auteur.

4 - Avantages et Bénéfices de la Lecture : Explique en quoi la lecture de ce livre apporte une réelle valeur ajoutée au lecteur. Développe les bénéfices pratiques, éducatifs ou émotionnels que le lecteur peut en tirer.

5 - Conclusion : Propose une conclusion engageante qui incite à l'achat ou à la lecture en rappelant les points essentiels du livre et en soulignant son utilité.
"""

SHOPIFY_PROMPT = """
À partir de l'analyse suivante d'un livre, génère une fiche produit détaillée pour un site internet en respectant la structure suivante :

1 - Présentation Générale : Introduis brièvement le livre en une ou deux phrases, en précisant le titre, l’auteur, et le genre. Développe ensuite, en deux paragraphes, l'objectif principal du livre en donnant un aperçu de la thématique abordée, en mettant en lumière les thèmes majeurs traités, le public cible, et en expliquant comment le contenu est structuré pour captiver le lecteur.

2- Contenu et Chapitres : Présente la table des matières en détaillant chaque chapitre, en soulignant les thèmes abordés et la valeur ajoutée qu'ils apportent au lecteur.

3 - Points Forts : Identifie quatre aspects majeurs qui rendent ce livre unique ou particulièrement intéressant (ex. style, originalité, pertinence, sources utilisées, etc.). Décris chaque point fort par une phrase courte, percutante et convaincante.
"""

def extract_text_from_file(file_path):
    """Extraire le texte d'un fichier DOCX."""
    logger.info(f"Fichier DOCX détecté : {file_path}")
    try:
        doc = Document(file_path)
        content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        logger.info(f"Extraction du contenu du DOCX réussie. Longueur : {len(content)} caractères.")
        return content
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du contenu du fichier DOCX : {e}")
        raise ValueError("Impossible d'extraire le contenu du fichier .docx.")

def split_text_into_chunks(text, max_length=1000):
    """Divise le texte en morceaux pour respecter la limite de tokens."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def analyze_chunks(file_path):
    """Analyse chaque chunk d'un fichier DOCX."""
    content = extract_text_from_file(file_path)
    chunks = split_text_into_chunks(content, max_length=1000)
    analysis_results = []

    for i, chunk in enumerate(chunks, start=1):
        start_time = time.time()
        logger.info(f"Envoi du chunk {i}/{len(chunks)} à OpenAI...")
        
        try:
            analysis_prompt = f"Voici une partie d'un livre. Analyse ce contenu : {chunk}"
            response = openai.ChatCompletion.create(
                model="gpt-4-32k",
                messages=[{"role": "user", "content": analysis_prompt}]
            )["choices"][0]["message"]["content"]
            analysis_results.append(response)
            logger.info(f"Chunk {i} analysé avec succès en {time.time() - start_time:.2f} secondes")
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du chunk {i}: {e}")
            raise

    consolidated_analysis = "\n".join(analysis_results)
    logger.info("Analyse consolidée générée avec succès.")
    return consolidated_analysis

def generate_final_fiche(consolidated_analysis, prompt_type):
    """Génère une fiche commerciale ou produit Shopify."""
    if prompt_type == "COMMERCIAL_PROMPT":
        prompt_template = COMMERCIAL_PROMPT
    elif prompt_type == "SHOPIFY_PROMPT":
        prompt_template = SHOPIFY_PROMPT
    else:
        raise ValueError("Type de prompt inconnu.")

    final_prompt = f"{prompt_template}\n\nVoici une analyse globale du livre :\n{consolidated_analysis}"
    logger.info("Envoi du prompt global à OpenAI.")

    try:
        french_response = openai.ChatCompletion.create(
            model="gpt-4-32k",
            messages=[{"role": "user", "content": final_prompt + "\nLangue: Français"}]
        )["choices"][0]["message"]["content"]

        english_response = openai.ChatCompletion.create(
            model="gpt-4-32k",
            messages=[{"role": "user", "content": final_prompt + "\nLangue: Anglais"}]
        )["choices"][0]["message"]["content"]

        return french_response, english_response
    except Exception as e:
        logger.error(f"Erreur lors de la génération des fiches finales : {e}")
        raise

def save_pdf(content, path):
    """Sauvegarde le contenu dans un fichier PDF."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, content)
        pdf.output(path)
        logger.info(f"PDF sauvegardé : {path}")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du PDF : {e}")
        raise
