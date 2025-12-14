# API de Recherche d'Abreviations USITO

API Flask qui permet de rechercher des abreviations et leurs definitions dans le dictionnaire USITO de l'Universite de Sherbrooke.

## Utilisation

### Endpoint principal

```
GET /recherche?abreviation=ONG
```

### Exemples

- `/recherche?abreviation=ONG` - Recherche la definition de ONG
- `/recherche?abreviation=UNESCO` - Recherche la definition de UNESCO
- `/recherche?abreviation=OTAN` - Recherche la definition de OTAN

### Reponse

```json
{
  "success": true,
  "abbreviation": "ONG",
  "url": "https://usito.usherbrooke.ca/definitions/ONG",
  "definitions": [...],
  "raw_content": [...]
}
```

## Endpoints

- `GET /` - Documentation de l'API
- `GET /recherche?abreviation=<terme>` - Recherche une abreviation
- `GET /health` - Verification de l'etat du serveur
