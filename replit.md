# API Abreviations USITO

## Overview
API Flask de web scraping pour rechercher des abreviations dans le dictionnaire USITO de l'Universite de Sherbrooke.

## Architecture
- **Backend**: Flask (Python 3.11)
- **Scraping**: BeautifulSoup4 + Requests
- **Production**: Gunicorn

## Files
- `main.py` - Application Flask avec routes API et logique de scraping
- `requirements.txt` - Dependances Python

## Running
- Development: `python main.py`
- Production: `gunicorn --bind=0.0.0.0:5000 main:app`

## API Endpoints
- `GET /` - Documentation
- `GET /recherche?abreviation=<terme>` - Recherche d'abreviation
- `GET /health` - Health check
