from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

app = Flask(__name__)

def clean_text(text):
    """Nettoie le texte en supprimant les infobulles et le bruit."""
    if not text:
        return ""
    text = re.sub(r'infobulle[a-z_]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\d{3}\s*Informations[^.]*\.', '', text)
    text = re.sub(r'infoLexico[^.]*\.?', '', text)
    text = re.sub(r'definition_entree[^(]*\([^)]*\)', '', text)
    text = re.sub(r'in_GDT\s*in\s*GDT\s*in\s*Grand.*?CRIFUQ\)\.\s*Site du GDT\s*\(\s*in\s*GDT\s*\)', '', text, flags=re.DOTALL)
    text = re.sub(r'renvoi_syn.*$', '', text)
    text = re.sub(r'\binv\.\s*invariable\s*250\b', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_definition(soup):
    """Extrait la definition principale."""
    main_content = soup.find('main') or soup.find('body')
    if not main_content:
        return None
    
    full_text = main_content.get_text(separator=' ', strip=True)
    
    patterns = [
        r'(?:inv\.|invariable\.?)\s*(.+?)(?:«|⇒|ÉTYMOLOGIE|ORTHOGRAPHE|noticeJournal|Site du GDT|definition_entree)',
        r'(?:n\.f\.|n\.m\.)\s*(?:inv\.)?\s*(.+?)(?:«|⇒|ÉTYMOLOGIE|Site du GDT|definition_entree)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, full_text, re.DOTALL)
        if match:
            definition = match.group(1)
            definition = clean_text(definition)
            definition = re.sub(r'^[^A-Z]*', '', definition)
            definition = re.sub(r'\s*\*\s*a établi.*$', '', definition, flags=re.DOTALL)
            definition = re.sub(r'\s*Le Centre d.analyse.*$', '', definition, flags=re.DOTALL)
            if len(definition) > 20:
                return definition
    
    return None

def extract_etymology(soup):
    """Extrait l'etymologie."""
    full_text = soup.get_text()
    match = re.search(r'ÉTYMOLOGIE\s*(\d{4}[^O]*?)(?:ORTHOGRAPHE|$)', full_text, re.DOTALL)
    if match:
        etym = match.group(1).strip()
        etym = re.sub(r'\s+', ' ', etym)
        return etym
    return None

def extract_synonyms(soup):
    """Extrait les synonymes."""
    synonyms = []
    links = soup.find_all('a')
    for link in links:
        href = link.get('href', '')
        if '/définitions/' in href:
            text = link.get_text(strip=True)
            if text and len(text) > 1 and text not in synonyms:
                parent_text = link.parent.get_text() if link.parent else ''
                if '⇒' in parent_text or 'synonyme' in parent_text.lower():
                    synonyms.append(text)
    return synonyms[:5]

def extract_grammar_info(soup):
    """Extrait les informations grammaticales."""
    full_text = soup.get_text()
    info = {}
    
    if 'n.f.' in full_text or 'nom féminin' in full_text.lower():
        info['genre'] = 'feminin'
        info['type'] = 'nom'
    elif 'n.m.' in full_text or 'nom masculin' in full_text.lower():
        info['genre'] = 'masculin'
        info['type'] = 'nom'
    
    if 'inv.' in full_text or 'invariable' in full_text.lower():
        info['nombre'] = 'invariable'
    
    return info if info else None

def extract_example(soup):
    """Extrait un exemple d'utilisation."""
    full_text = soup.get_text()
    match = re.search(r'«(.+?)»', full_text)
    if match:
        example = match.group(1).strip()
        example = re.sub(r'\s+', ' ', example)
        return example
    return None

def extract_pronunciation(soup):
    """Extrait la prononciation phonetique."""
    full_text = soup.get_text()
    match = re.search(r'\[([a-zɛɔɑ̃œ̃ɛ̃ʒʃɲŋəø]+)\]', full_text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def scrape_usito(abbreviation):
    """
    Scrape the USITO dictionary for a given abbreviation/term.
    Returns structured and clean data.
    """
    encoded_term = quote(abbreviation, safe='')
    url = f"https://usito.usherbrooke.ca/définitions/{encoded_term}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Erreur de connexion: {str(e)}", "success": False}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    result = {
        "success": True,
        "terme": abbreviation.upper(),
        "url": url,
    }
    
    definition = extract_definition(soup)
    if definition:
        result["definition"] = definition
    
    pronunciation = extract_pronunciation(soup)
    if pronunciation:
        result["prononciation"] = pronunciation
    
    grammar = extract_grammar_info(soup)
    if grammar:
        result["grammaire"] = grammar
    
    etymology = extract_etymology(soup)
    if etymology:
        result["etymologie"] = etymology
    
    example = extract_example(soup)
    if example:
        result["exemple"] = example
    
    synonyms = extract_synonyms(soup)
    if synonyms:
        result["synonymes"] = synonyms
    
    if "definition" not in result:
        result["message"] = "Terme non trouve ou definition non disponible dans le dictionnaire USITO"
        result["success"] = False
    
    return result

@app.route('/')
def home():
    """Page d'accueil avec documentation de l'API"""
    return jsonify({
        "message": "API de recherche d'abreviations USITO",
        "usage": {
            "endpoint": "/recherche",
            "method": "GET",
            "parameter": "abreviation",
            "exemple": "/recherche?abreviation=ONG"
        },
        "description": "Cette API permet de rechercher des abreviations et leurs definitions dans le dictionnaire USITO de l'Universite de Sherbrooke.",
        "champs_retournes": [
            "terme", "definition", "prononciation", "grammaire", 
            "etymologie", "exemple", "synonymes"
        ]
    })

@app.route('/recherche')
def recherche():
    """
    Route GET pour rechercher une abreviation.
    Usage: /recherche?abreviation=ONG
    """
    abreviation = request.args.get('abreviation', '').strip()
    
    if not abreviation:
        return jsonify({
            "error": "Parametre 'abreviation' manquant",
            "usage": "/recherche?abreviation=ONG",
            "success": False
        }), 400
    
    result = scrape_usito(abreviation)
    
    if not result.get("success", False):
        return jsonify(result), 404
    
    return jsonify(result)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
