# CSV Insights API

Solution FastAPI pour le projet de fin de chapitre.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Lancer le serveur

```bash
uvicorn app.main:app --reload
```

## Utilisateurs de démonstration

- alice
- bob

Utilisez `POST /login` dans `/docs` pour récupérer un token Bearer.

## Notes

- Les fichiers CSV envoyés sont stockés dans `uploads/`.
- L'analyse est lancée en arrière-plan avec `BackgroundTasks`.
- La base SQLite est créée automatiquement dans `csv_insights.db`.
