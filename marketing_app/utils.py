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
À partir de l'analyse suivante d'un livre, génère une fiche commerciale détaillée et captivante qui donne envie de découvrir le contenu, en respectant la structure suivante :

1 - **Présentation Générale** :  
   Rédige un paragraphe engageant qui présente le livre en mentionnant son titre, son auteur, son genre (par exemple : un livre de magie ou d’illusionnisme). Explique l’objectif principal de l’ouvrage (par exemple : transmettre des connaissances, inspirer des magiciens, ou détailler des tours inédits). Décris brièvement le public cible (débutants, amateurs passionnés ou professionnels) et la philosophie générale adoptée par l’auteur dans sa démarche.

2 - **Résumé Détail des Chapitres** :  
   Développe un résumé pour chaque chapitre ou section importante du livre. Pour chaque chapitre :
   - Explique les thématiques abordées (par exemple : psychologie des spectateurs, techniques de manipulation, ou théorie magique).
   - Décris les concepts clés ou enseignements spécifiques que le lecteur peut attendre.
   - Donne des exemples d’effets magiques ou de principes présentés dans ce chapitre sans dévoiler les secrets, mais en créant de l’intrigue. Par exemple : "Ce chapitre explore comment une carte choisie au hasard peut se retrouver dans un endroit impossible."

3 - **Description des Effets Magiques Présentés** :  
   Ajoute une description détaillée des types d’effets magiques expliqués dans le livre. Par exemple : des disparitions d’objets, des prédictions impossibles, ou des transformations visuelles spectaculaires. Présente les effets comme des outils créatifs, et insiste sur leur originalité et leur impact potentiel sur les spectateurs.

4 - **Points Forts du Livre** :  
   Liste les éléments qui rendent ce livre incontournable pour les magiciens, en utilisant des tirets pour clarifier les idées. Par exemple :
   - Une approche pédagogique claire et accessible.
   - Des effets originaux et percutants, adaptés à différentes situations (close-up, scène, etc.).
   - Une attention particulière portée à la psychologie des spectateurs.
   - Des illustrations ou explications visuelles pour chaque effet.

5 - **Bénéfices pour le Lecteur** :  
   Explique comment ce livre enrichit le magicien dans sa pratique. Développe les avantages tels que :
   - Améliorer la compréhension des principes magiques.
   - Inspirer des créations originales grâce aux concepts partagés.
   - Renforcer la capacité à captiver et émerveiller un public.
   - Offrir des techniques qui s’adaptent aussi bien à des performances professionnelles qu’à des spectacles plus intimes.

6 - **Conclusion** :  
   Termine avec un paragraphe motivant qui récapitule les points clés du livre et incite à l'achat. Mets l’accent sur la valeur ajoutée que ce livre peut apporter à un magicien et sur son caractère indispensable.

"""

SHOPIFY_PROMPT = """
À partir de l'analyse suivante d'un livre, génère une fiche produit captivante pour un site internet en respectant la structure suivante :

1 - **Présentation Générale** :  
   Introduis brièvement le livre en une ou deux phrases en mentionnant son titre, son auteur, et son genre. Développe ensuite en détail en quoi ce livre est une ressource unique pour les magiciens, qu’ils soient débutants ou confirmés. Donne un aperçu clair de la thématique générale du livre et des objectifs poursuivis par l’auteur.

2 - **Résumé Détail des Chapitres** :  
   Pour chaque chapitre ou section majeure du livre :
   - Fournis un résumé détaillé expliquant les concepts traités.
   - Décris les sujets spécifiques abordés (exemple : techniques avancées de manipulation, stratégies pour renforcer l’impact émotionnel des tours, ou secrets psychologiques pour influencer les spectateurs).
   - Ajoute des exemples d’effets magiques expliqués dans ce chapitre sans dévoiler les secrets, pour attiser la curiosité.

3 - **Description des Effets Magiques Présentés** :  
   Rédige un texte captivant décrivant les effets expliqués dans le livre, en mettant l’accent sur leur impact émotionnel et leur originalité. Par exemple : "Apprenez à réaliser des transformations impossibles, des disparitions spectaculaires, et des prédictions qui laissent les spectateurs sans voix." Insiste sur la diversité et la puissance des tours pour captiver le public.

4 - **Points Forts** :  
   Liste les points forts du livre de manière concise et percutante :
   - Une riche collection d’effets magiques testés par des professionnels.
   - Une structure pédagogique pour guider les magiciens de tous niveaux.
   - Des illustrations ou explications claires pour chaque tour.
   - Une approche unique qui mêle théorie, pratique et psychologie.

5 - **Pourquoi acheter ce livre ?** :  
   Développe les raisons pour lesquelles ce livre est indispensable à tout magicien. Par exemple :
   - Acquérir des techniques originales pour enrichir son répertoire.
   - S’inspirer des réflexions de l’auteur pour développer des créations personnelles.
   - Maîtriser des effets qui s’adaptent à divers contextes (scène, close-up, spectacles privés).
   - Améliorer sa capacité à émerveiller et captiver un public varié.
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
