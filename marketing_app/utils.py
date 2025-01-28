import openai
import os
from fpdf import FPDF

def process_commercial_sheet(file_path):
    return _generate_pdf(file_path, commercial_prompt)

def process_shopify_sheet(file_path):
    return _generate_pdf(file_path, shopify_prompt)

def _generate_pdf(file_path, prompt_template):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    french_prompt = f"{prompt_template}\n\nContenu du fichier:\n{content}\n\nLangue: Français"
    english_prompt = f"{prompt_template}\n\nContenu du fichier:\n{content}\n\nLangue: Anglais"

    french_text = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": french_prompt}]
    )["choices"][0]["message"]["content"]

    english_text = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": english_prompt}]
    )["choices"][0]["message"]["content"]

    french_pdf = os.path.join("downloads", "french_commercial.pdf")
    english_pdf = os.path.join("downloads", "english_commercial.pdf")

    _save_pdf(french_text, french_pdf)
    _save_pdf(english_text, english_pdf)

    return french_pdf, english_pdf

def _save_pdf(content, path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    pdf.output(path)
