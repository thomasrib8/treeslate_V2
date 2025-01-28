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
À partir de l'analyse suivante d'un livre, génère une fiche commerciale détaillée mettant en avant le livre en respectant la structure suivante, avec un texte développé et fluide (pas de listes à puces ni de tirets) :

1 - **Présentation Générale** :  
   Rédige un paragraphe décrivant le titre du livre, son auteur, et son genre. Explique en quoi ce livre est unique, notamment pour les amateurs ou professionnels de la magie. Donne un aperçu de la thématique principale, de l’objectif du livre, du public cible (magiciens débutants, amateurs ou confirmés), et de l’approche pédagogique adoptée par l’auteur.

2 - **Contenu et Chapitres Clés** :  
   Développe un ou plusieurs paragraphes expliquant comment le livre est structuré et ce que chaque chapitre ou section apporte. Décris les principaux thèmes abordés dans le livre, comme la psychologie du spectateur, les techniques de présentation, ou les subtilités pour rendre un effet magique plus impactant. Montre comment chaque chapitre s’inscrit dans une démarche pédagogique ou inspirante pour le lecteur.

3 - **Description des Effets Magiques** :  
   Décris les effets magiques présentés dans le livre de manière engageante et intrigante, sans révéler les secrets. Par exemple, explique comment un tour donne l’impression qu’une pièce disparaît entre les mains du spectateur, ou qu’une carte choisie au hasard réapparaît dans un endroit impossible. Mettez en avant la diversité des effets et leur originalité pour inciter le lecteur à découvrir les méthodes derrière ces miracles.

4 - **Points Forts** :  
   Rédige un texte fluide expliquant pourquoi ce livre est exceptionnel. Soulignez des aspects comme l’originalité des effets, la clarté des explications, la qualité des illustrations ou des photos, et l’expertise de l’auteur. Expliquez pourquoi ces éléments rendent ce livre indispensable dans la bibliothèque de tout magicien.

5 - **Avantages et Bénéfices pour le Lecteur** :  
   Développe un ou plusieurs paragraphes expliquant comment ce livre peut enrichir le lecteur. Montrez comment il peut aider à développer des compétences magiques, à mieux comprendre la psychologie des spectateurs, ou à améliorer sa présentation et sa créativité. Appuyez vos arguments avec des exemples tirés du livre pour démontrer sa valeur pratique.

6 - **Conclusion** :  
   Terminez par un paragraphe engageant, synthétisant les qualités principales du livre, et incitant le lecteur à l’ajouter à sa collection. Insistez sur son utilité, son caractère inspirant, et la richesse des enseignements qu’il contient.

"""

SHOPIFY_PROMPT = """
À partir de l'analyse suivante d'un livre, génère une fiche produit détaillée pour un site internet en respectant la structure suivante, avec un texte développé et fluide (pas de listes à puces ni de tirets) :

1 - **Présentation Générale** :  
   Introduis brièvement le titre du livre, son auteur, et son genre. Développe en plusieurs paragraphes en quoi ce livre est unique pour les magiciens, en décrivant son objectif principal. Donne un aperçu de la thématique abordée, des thèmes majeurs traités, et du public cible (magiciens débutants, amateurs ou professionnels). Explique comment l’auteur a structuré son contenu pour captiver l’attention des lecteurs.

2 - **Contenu et Chapitres** :  
   Développe un ou plusieurs paragraphes décrivant les chapitres principaux. Explique en détail les concepts abordés dans chaque chapitre, comme la théorie magique, les techniques spécifiques, ou les idées pour créer des effets originaux. Souligne comment ces chapitres apportent de la valeur au lecteur, tout en montrant leur lien avec l’objectif global du livre.

3 - **Description des Effets Magiques** :  
   Décris les effets magiques expliqués dans le livre de manière captivante, sans révéler les secrets. Par exemple, parle de tours qui font disparaître des objets, des prédictions impossibles, ou des manipulations subtiles qui laissent les spectateurs émerveillés. Mets en avant l’originalité et la diversité des effets pour donner envie au lecteur de découvrir leurs méthodes.

4 - **Points Forts** :  
   Rédige un texte fluide expliquant ce qui rend ce livre exceptionnel. Parlez de l’approche pédagogique de l’auteur, de la clarté des explications, de la créativité des effets, et de l’attention portée aux détails. Expliquez pourquoi ces éléments font de ce livre une ressource incontournable pour les magiciens.

5 - **Pourquoi lire ce livre ?** :  
   Montrez en quoi ce livre est essentiel pour les magiciens. Expliquez comment il peut inspirer, améliorer la maîtrise des techniques, ou aider à développer des effets uniques. Donnez des exemples concrets issus du contenu pour démontrer son utilité et son inspiration.
"""

def convert_docx_to_txt(docx_path, txt_path):
    """Convertit un fichier DOCX en fichier TXT."""
    try:
        doc = Document(docx_path)
        content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(content)
        logger.info(f"Conversion DOCX vers TXT réussie : {txt_path}")
        return txt_path
    except Exception as e:
        logger.error(f"Erreur lors de la conversion DOCX -> TXT : {e}")
        raise ValueError("Impossible de convertir le fichier DOCX en TXT.")

def split_text_into_chunks(text, max_length=3000):
    """Divise le texte en morceaux de taille maximale."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def analyze_chunks(file_path):
    """Analyse chaque chunk d'un fichier TXT après regroupement."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Diviser le texte en chunks de 3000 caractères
    chunks = split_text_into_chunks(content, max_length=3000)

    # Regrouper les chunks par paquets de 1 ou 2 pour éviter les retards excessifs
    grouped_chunks = ["\n".join(chunks[i:i + 2]) for i in range(0, len(chunks), 2)]

    analysis_results = []
    for i, group in enumerate(grouped_chunks, start=1):
        start_time = time.time()
        logger.info(f"Envoi du groupe {i}/{len(grouped_chunks)} à OpenAI...")

        try:
            analysis_prompt = f"Voici une partie d'un livre. Analyse ce contenu : {group}"
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": analysis_prompt}]
            )["choices"][0]["message"]["content"]
            analysis_results.append(response)
            logger.info(f"Groupe {i} analysé avec succès en {time.time() - start_time:.2f} secondes")
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du groupe {i}: {e}")
            raise

    consolidated_analysis = "\n".join(analysis_results)
    return consolidated_analysis

def generate_final_fiche(consolidated_analysis, prompt_template):
    """Génère une fiche commerciale ou produit Shopify."""
    final_prompt = f"{prompt_template}\n\nVoici une analyse globale du livre :\n{consolidated_analysis}"
    logger.info("Envoi du prompt global à OpenAI.")

    french_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": final_prompt + "\nLangue: Français"}]
    )["choices"][0]["message"]["content"]

    english_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": final_prompt + "\nLangue: Anglais"}]
    )["choices"][0]["message"]["content"]

    return french_response, english_response

def save_pdf(content, path):
    """Sauvegarde le contenu dans un fichier PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    pdf.output(path)
    logger.info(f"PDF sauvegardé : {path}")
