import requests
from docx import Document
from tqdm import tqdm
import time
import os
import pandas as pd
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_glossary(api_key, name, source_lang, target_lang, glossary_path):
    api_url = "https://api.deepl.com/v2/glossaries"
    with open(glossary_path, "r") as glossary_file:
        glossary_content = glossary_file.read()

    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "name": name,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "entries_format": "csv",
        "entries": glossary_content,
    }

    response = requests.post(api_url, headers=headers, data=data)
    response_data = response.json()

    if response.status_code in (200, 201) and "glossary_id" in response_data:
        logger.info("Glossary created successfully.")
        return response_data["glossary_id"]
    else:
        logger.error(f"Failed to create glossary: {response.text}")
        raise Exception(f"Failed to create glossary: {response.text}")

def translate_docx_with_deepl(api_key, input_file_path, output_file_path, target_language, source_language, glossary_id=None):
    api_url = "https://api.deepl.com/v2/document"
    headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}
    data = {"target_lang": target_language, "source_lang": source_language}

    if glossary_id:
        data["glossary_id"] = glossary_id

    with open(input_file_path, "rb") as file:
        upload_response = requests.post(api_url, headers=headers, data=data, files={"file": file})

    if upload_response.status_code != 200:
        raise Exception(f"Failed to upload document: {upload_response.text}")

    upload_data = upload_response.json()
    document_id = upload_data["document_id"]
    document_key = upload_data["document_key"]

    status_url = f"{api_url}/{document_id}"
    while True:
        status_response = requests.post(status_url, headers=headers, data={"document_key": document_key})
        status_data = status_response.json()
        if status_data["status"] == "done":
            break
        elif status_data["status"] == "error":
            raise Exception(f"Translation error: {status_data}")
        time.sleep(1)

    download_url = f"{api_url}/{document_id}/result"
    download_response = requests.post(download_url, headers=headers, data={"document_key": document_key})

    if download_response.status_code == 200:
        with open(output_file_path, "wb") as output_file:
            output_file.write(download_response.content)
    else:
        raise Exception(f"Failed to download translated document: {download_response.text}")

def improve_translation(input_file, glossary_path, output_file, language_level, source_language, target_language, group_size, model):
    doc = Document(input_file)
    glossary = read_glossary(glossary_path)
    output_doc = Document()
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

    with tqdm(total=len(paragraphs), desc="Processing paragraphs") as pbar:
        for i in range(0, len(paragraphs), group_size):
            group = paragraphs[i : i + group_size]
            improved_text = process_paragraphs(group, glossary, language_level, source_language, target_language, model)
            if improved_text:
                output_doc.add_paragraph(improved_text)
            pbar.update(len(group))
    output_doc.save(output_file)

def convert_excel_to_csv(excel_path, csv_path):
    df = pd.read_excel(excel_path, header=None)
    df.to_csv(csv_path, index=False, header=False)
    return csv_path
