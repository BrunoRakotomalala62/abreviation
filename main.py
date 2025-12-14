from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

app = Flask(__name__)

def scrape_usito(abbreviation):
    """
    Scrape the USITO dictionary for a given abbreviation/term.
    Returns the scraped data as a dictionary.
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
    
    result = {
        "success": True,
        "abbreviation": abbreviation,
        "url": url,
        "definitions": [],
        "raw_content": []
    }
    
    title = soup.find('h1')
    if title:
        result["title"] = title.get_text(strip=True)
    
    definitions = soup.find_all('div', class_='definition')
    if definitions:
        for defn in definitions:
            result["definitions"].append(defn.get_text(strip=True))
    
    articles = soup.find_all('article')
    for article in articles:
        article_text = article.get_text(separator=' ', strip=True)
        if article_text:
            result["raw_content"].append(article_text)
    
    main_content = soup.find('main')
    if main_content:
        result["main_content"] = main_content.get_text(separator='\n', strip=True)
    
    entries = soup.find_all(['section', 'div'], class_=lambda x: x and ('entry' in x.lower() if x else False))
    if entries:
        result["entries"] = [entry.get_text(separator=' ', strip=True) for entry in entries]
    
    if not result["definitions"] and not result["raw_content"]:
        all_text = soup.find('body')
        if all_text:
            paragraphs = all_text.find_all(['p', 'div', 'span'])
            for p in paragraphs[:10]:
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    result["raw_content"].append(text)
    
    return result

@app.route('/')
def home():
    """Page d'accueil avec documentation de l'API"""
    return jsonify({
        "message": "API de recherche d'abréviations USITO",
        "usage": {
            "endpoint": "/recherche",
            "method": "GET",
            "parameter": "abreviation",
            "example": "/recherche?abreviation=ONG"
        },
        "description": "Cette API permet de rechercher des abréviations et leurs définitions dans le dictionnaire USITO de l'Université de Sherbrooke."
    })

@app.route('/recherche')
def recherche():
    """
    Route GET pour rechercher une abréviation.
    Usage: /recherche?abreviation=ONG
    """
    abreviation = request.args.get('abreviation', '').strip()
    
    if not abreviation:
        return jsonify({
            "error": "Paramètre 'abreviation' manquant",
            "usage": "/recherche?abreviation=ONG",
            "success": False
        }), 400
    
    result = scrape_usito(abreviation)
    
    if not result.get("success", False):
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
