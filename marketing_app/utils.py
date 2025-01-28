import openai
import os
from fpdf import FPDF
from flask import current_app
from docx import Document
import logging
import time
from fpdf.enums import XPos, YPos

logger = logging.getLogger(__name__)

# Prompts pour ChatGPT
COMMERCIAL_PROMPT = """
À partir de l'analyse suivante d'un livre de magie, génère une fiche commerciale détaillée avec les sections suivantes :

1. **Titre et Auteur** :
   - Extrais le titre exact et le nom de l'auteur directement du texte analysé.
   
2. **Présentation Générale** :
   - Présente le livre en précisant son titre, son auteur, et le contexte de création.
   - Développe l'objectif principal du livre et donne un aperçu des thématiques abordées (par exemple : philosophie de la magie, minimalisme, importance des réactions spectateurs).

3. **Résumé des Chapitres** :
   - Décris chaque chapitre ou tour de magie présenté dans le livre. Pour chaque chapitre :
     - Donne un titre s'il est mentionné.
     - Résume en quelques phrases le contenu du chapitre ou du tour (sans dévoiler les secrets).
     - Décris les effets magiques tels qu'ils sont perçus par les spectateurs, leur originalité, et leur impact.
     - Mentionne en quoi ce tour est adapté pour des magiciens débutants ou confirmés.

4. **Description des Effets Magiques** :
   - Détaille les effets magiques expliqués dans le livre, en mettant l'accent sur leur impact émotionnel ou visuel (sans dévoiler les secrets techniques). Explique pourquoi ils captivent l'audience.

5. **Points Forts** (liste à puces) :
   - Identifie et développe au moins 5 aspects qui rendent ce livre unique :
     - Originalité des tours ou techniques.
     - Approche pédagogique et facilité de compréhension.
     - Adaptabilité des tours à différents contextes (scène, close-up, etc.).
     - Philosophie ou théories sur la magie développées par l'auteur.
     - Autres qualités spécifiques (comme la structure claire du livre ou des illustrations utiles).

6. **Conclusion** :
   - Résume les points clés du livre.
   - Incite à la lecture ou à l'achat en mettant en avant les bénéfices pour le lecteur.

"""

SHOPIFY_PROMPT = """
À partir de l'analyse suivante d'un livre de magie, génère une fiche produit détaillée pour un site internet. Suis cette structure :

1. **Titre et Auteur** :
   - Extrais et présente le titre du livre et le nom de l'auteur depuis le texte.

2. **Introduction** :
   - Développe une introduction engageante en une ou deux phrases, précisant l'objectif principal du livre et les thèmes abordés.

3. **Résumé des Chapitres** :
   - Résume chaque chapitre de manière détaillée en expliquant :
     - Les effets magiques décrits (sans dévoiler les secrets techniques).
     - Le contexte ou la philosophie de chaque chapitre.
     - Comment ces effets ou réflexions aident les magiciens dans leur pratique.

4. **Description des Effets Magiques** :
   - Décris les tours de magie et leurs effets sur les spectateurs.
   - Explique pourquoi ces effets se démarquent (par exemple, par leur simplicité, leur impact émotionnel, ou leur originalité).

5. **Points Forts** (liste à puces) :
   - Identifie et énumère 5 à 7 points forts du livre :
     - Originalité et pertinence des effets magiques.
     - Accessibilité pour différents niveaux de magiciens.
     - Philosophie unique de l'auteur sur la magie.
     - Adaptabilité des tours aux contextes variés.
     - Présentation claire et soignée.

6. **Appel à l'Action** :
   - Termine par un appel à l'action engageant qui motive l'utilisateur à acheter le livre (par exemple : "Explorez ces effets magiques et enrichissez votre répertoire dès maintenant !").

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
    """Sauvegarde le contenu dans un fichier PDF avec support Unicode."""
    pdf = FPDF()
    pdf.add_page()
    
    # Ajouter une police compatible Unicode (FreeSerif)
    font_path = os.path.join(current_app.root_path, "static", "fonts", "FreeSerif-4aeK.ttf")
    pdf.add_font("FreeSerif", "", font_path, uni=True)
    pdf.set_font("FreeSerif", size=12)
    
    # Ajouter le contenu au PDF
    pdf.multi_cell(0, 10, content)
    
    # Sauvegarde du fichier PDF
    pdf.output(path)
    logger.info(f"PDF sauvegardé : {path}")
