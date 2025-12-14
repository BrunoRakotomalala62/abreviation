from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re
import unicodedata

app = Flask(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
}

def clean_text(text):
    """Nettoie le texte."""
    if not text:
        return ""
    text = re.sub(r'infobulle[a-z_]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\d{3}\s*Informations[^.]*\.', '', text)
    text = re.sub(r'infoLexico[^.]*\.?', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def normalize_term(term):
    """Normalise un terme (sans accents, majuscules)."""
    normalized = unicodedata.normalize('NFD', term)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return without_accents.upper()

def scrape_abbreviations_com(term):
    """Scrape Abbreviations.com pour les abreviations mondiales."""
    url = f"https://www.abbreviations.com/{quote(term)}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    definitions = []
    
    tables = soup.find_all('table', class_='tdata')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                abbr = cells[0].get_text(strip=True)
                meaning = cells[1].get_text(strip=True)
                if meaning and abbr.upper() == term.upper():
                    category_cell = cells[2] if len(cells) > 2 else None
                    category = category_cell.get_text(strip=True) if category_cell else None
                    definitions.append({
                        "definition": meaning,
                        "categorie": category
                    })
    
    results_div = soup.find_all('p', class_='desc')
    for p in results_div:
        text = p.get_text(strip=True)
        if text and len(text) > 3:
            definitions.append({"definition": text})
    
    if definitions:
        return {
            "success": True,
            "terme": term.upper(),
            "source": "Abbreviations.com",
            "definitions": definitions[:10],
            "url": url
        }
    
    return None

def scrape_acronym_finder(term):
    """Scrape Acronym Finder pour les acronymes."""
    url = f"https://www.acronymfinder.com/{quote(term)}.html"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    definitions = []
    
    result_table = soup.find('table', class_='result-list')
    if result_table:
        rows = result_table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                meaning_cell = cells[1] if len(cells) > 1 else cells[0]
                meaning = meaning_cell.get_text(strip=True)
                if meaning:
                    category_cell = cells[2] if len(cells) > 2 else None
                    category = category_cell.get_text(strip=True) if category_cell else None
                    definitions.append({
                        "definition": meaning,
                        "categorie": category
                    })
    
    if not definitions:
        all_results = soup.find_all(['td', 'div'], class_=lambda x: x and 'meaning' in str(x).lower())
        for result in all_results:
            text = result.get_text(strip=True)
            if text and len(text) > 3:
                definitions.append({"definition": text})
    
    if definitions:
        return {
            "success": True,
            "terme": term.upper(),
            "source": "Acronym Finder",
            "definitions": definitions[:10],
            "url": url
        }
    
    return None

def scrape_all_acronyms(term):
    """Scrape All Acronyms."""
    url = f"https://www.allacronyms.com/{quote(term)}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    definitions = []
    
    meaning_divs = soup.find_all('div', class_='meaning')
    for div in meaning_divs:
        text = div.get_text(strip=True)
        if text and len(text) > 2:
            definitions.append({"definition": text})
    
    if not definitions:
        links = soup.find_all('a', href=True)
        for link in links:
            if f'/{term.lower()}/' in link.get('href', '').lower():
                parent = link.find_parent('div') or link.find_parent('li')
                if parent:
                    text = parent.get_text(strip=True)
                    text = re.sub(rf'^{re.escape(term)}\s*', '', text, flags=re.IGNORECASE)
                    if text and len(text) > 3:
                        definitions.append({"definition": text})
    
    if definitions:
        return {
            "success": True,
            "terme": term.upper(),
            "source": "All Acronyms",
            "definitions": definitions[:10],
            "url": url
        }
    
    return None

def extract_usito_definition(soup):
    """Extrait la definition USITO."""
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

def search_usito_acronyms(term):
    """Cherche dans les acronymes USITO."""
    first_letter = term[0].upper()
    url = f"https://usito.usherbrooke.ca/index/asas/acronymes/{first_letter}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    normalized_term = normalize_term(term)
    
    for link in soup.find_all('a'):
        href = link.get('href', '')
        link_text = link.get_text(strip=True)
        
        if normalize_term(link_text) == normalized_term and '/annexes/acronymes/' in href:
            parent = link.parent
            if parent:
                full_text = parent.get_text(separator=' ', strip=True)
                definition_match = re.search(rf'{re.escape(link_text)}\s+(.+)', full_text, re.IGNORECASE)
                if definition_match:
                    return definition_match.group(1).strip()
    
    return None

def scrape_usito(term):
    """Scrape USITO (dictionnaire quebecois)."""
    encoded_term = quote(term, safe='')
    url = f"https://usito.usherbrooke.ca/définitions/{encoded_term}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    definition = extract_usito_definition(soup)
    
    if not definition:
        definition = search_usito_acronyms(term)
    
    if definition:
        full_text = soup.get_text()
        etymology = None
        match = re.search(r'ÉTYMOLOGIE\s*(\d{4}[^O]*?)(?:ORTHOGRAPHE|$)', full_text, re.DOTALL)
        if match:
            etymology = re.sub(r'\s+', ' ', match.group(1).strip())
        
        example = None
        match = re.search(r'«(.+?)»', full_text)
        if match:
            example = re.sub(r'\s+', ' ', match.group(1).strip())
        
        result = {
            "success": True,
            "terme": term.upper(),
            "source": "USITO (Quebec)",
            "definition": definition,
            "url": url
        }
        
        if etymology:
            result["etymologie"] = etymology
        if example:
            result["exemple"] = example
        
        return result
    
    return None

def search_all_sources(term):
    """Recherche dans toutes les sources disponibles."""
    all_results = []
    
    usito_result = scrape_usito(term)
    if usito_result:
        all_results.append(usito_result)
    
    abbr_result = scrape_abbreviations_com(term)
    if abbr_result:
        all_results.append(abbr_result)
    
    acronym_result = scrape_acronym_finder(term)
    if acronym_result:
        all_results.append(acronym_result)
    
    allacronyms_result = scrape_all_acronyms(term)
    if allacronyms_result:
        all_results.append(allacronyms_result)
    
    return all_results

@app.route('/')
def home():
    """Page d'accueil avec documentation de l'API"""
    return jsonify({
        "message": "API de recherche d'abreviations multilingue",
        "sources": [
            "USITO (Quebec/France)",
            "Abbreviations.com (Mondial)",
            "Acronym Finder (Mondial)",
            "All Acronyms (Mondial)"
        ],
        "endpoints": {
            "/recherche": {
                "method": "GET",
                "params": "abreviation",
                "description": "Recherche dans USITO uniquement",
                "exemple": "/recherche?abreviation=ONG"
            },
            "/recherche/global": {
                "method": "GET",
                "params": "abreviation",
                "description": "Recherche dans toutes les sources mondiales",
                "exemple": "/recherche/global?abreviation=NASA"
            }
        }
    })

@app.route('/recherche')
def recherche():
    """Recherche dans USITO."""
    abreviation = request.args.get('abreviation', '').strip()
    
    if not abreviation:
        return jsonify({
            "error": "Parametre 'abreviation' manquant",
            "usage": "/recherche?abreviation=ONG",
            "success": False
        }), 400
    
    result = scrape_usito(abreviation)
    
    if not result:
        acronym_def = search_usito_acronyms(abreviation)
        if acronym_def:
            result = {
                "success": True,
                "terme": abreviation.upper(),
                "source": "USITO (Quebec)",
                "definition": acronym_def
            }
    
    if result:
        return jsonify(result)
    
    return jsonify({
        "success": False,
        "terme": abreviation.upper(),
        "message": "Terme non trouve dans USITO. Essayez /recherche/global pour une recherche mondiale."
    }), 404

@app.route('/recherche/global')
def recherche_global():
    """Recherche dans toutes les sources mondiales."""
    abreviation = request.args.get('abreviation', '').strip()
    
    if not abreviation:
        return jsonify({
            "error": "Parametre 'abreviation' manquant",
            "usage": "/recherche/global?abreviation=NASA",
            "success": False
        }), 400
    
    results = search_all_sources(abreviation)
    
    if results:
        return jsonify({
            "success": True,
            "terme": abreviation.upper(),
            "nombre_sources": len(results),
            "resultats": results
        })
    
    return jsonify({
        "success": False,
        "terme": abreviation.upper(),
        "message": "Aucun resultat trouve dans les sources disponibles."
    }), 404

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
