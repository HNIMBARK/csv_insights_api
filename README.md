# CSV Insights API

API REST construite avec **FastAPI** pour analyser des fichiers CSV. L'utilisateur s'authentifie, envoie un CSV, et l'analyse (nombre de lignes, colonnes, statistiques descriptives) est exécutée **en arrière-plan** puis stockée dans **PostgreSQL**.

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Stack technique](#stack-technique)
- [Architecture du projet](#architecture-du-projet)
- [Prérequis](#prérequis)
- [Configuration (.env)](#configuration-env)
- [Lancement avec Docker (recommandé)](#lancement-avec-docker-recommandé)
- [Lancement en local (sans Docker)](#lancement-en-local-sans-docker)
- [Authentification](#authentification)
- [Endpoints](#endpoints)
- [Exemple complet avec curl](#exemple-complet-avec-curl)
- [Modèle de données](#modèle-de-données)
- [Fonctionnement de l'analyse](#fonctionnement-de-lanalyse)
- [Commandes utiles](#commandes-utiles)
- [Dépannage](#dépannage)
- [Limites connues et pistes d'amélioration](#limites-connues-et-pistes-damélioration)

## Fonctionnalités

- Authentification par token Bearer (utilisateurs de démonstration `alice` et `bob`)
- Upload de fichiers CSV (seule l'extension `.csv` est acceptée)
- Analyse asynchrone avec `BackgroundTasks` : la réponse est immédiate (`202 Accepted`), le traitement se fait ensuite
- Suivi du statut de chaque analyse : `pending`, `running`, `completed`, `failed`
- Statistiques par colonne (type, `count`, `mean`, `std`, `min`, quartiles, `max` pour les colonnes numériques)
- Statistiques globales (nombre de fichiers, nombre total de lignes traitées)
- Suppression d'une analyse, réservée à son propriétaire
- Documentation interactive automatique (Swagger UI)

## Stack technique

| Composant | Rôle |
|---|---|
| FastAPI + Uvicorn | API web et serveur ASGI |
| SQLAlchemy | ORM |
| PostgreSQL 16 | Base de données |
| psycopg2-binary | Driver PostgreSQL |
| pandas | Lecture et analyse des CSV |
| python-multipart | Gestion des uploads de fichiers |
| Docker / Docker Compose | Conteneurisation et orchestration |

## Architecture du projet

```
.
├── app/
│   ├── main.py            # Point d'entrée : création des tables, seed des utilisateurs, routers
│   ├── database.py        # Connexion SQLAlchemy / PostgreSQL (variables d'environnement)
│   ├── models.py          # Modèles ORM : UserDB, AnalysisDB, AnalysisStatus
│   ├── schemas.py         # Schémas Pydantic (entrées / sorties de l'API)
│   ├── dependencies.py    # Session DB, gestion des tokens, utilisateur courant
│   ├── services.py        # Sauvegarde des CSV, analyse pandas, statistiques globales
│   └── routers/
│       ├── auth.py        # /login et /users
│       └── analyses.py    # Endpoints /analyses
├── uploads/               # CSV envoyés (créé automatiquement)
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env                   # Variables d'environnement (non versionné)
├── .env.example           # Modèle de .env (versionné)
├── requirements.txt
└── README.md
```

## Prérequis

**Avec Docker (recommandé)** : Docker et Docker Compose v2.

**Sans Docker** : Python 3.11+ et une instance PostgreSQL accessible.

## Configuration (.env)

Copie le fichier d'exemple puis renseigne les valeurs :

```bash
cp .env.example .env
```

Contenu attendu de `.env` :

```env
DB_HOST=
DB_PORT=5432
DB_USER=
DB_PASSWORD=
DB_NAME=
```

| Variable | Description |
|---|---|
| `DB_HOST` | Hôte PostgreSQL. `db` avec Docker Compose (nom du service), `localhost` en local |
| `DB_PORT` | Port PostgreSQL (5432 par défaut) |
| `DB_USER` | Utilisateur PostgreSQL |
| `DB_PASSWORD` | Mot de passe PostgreSQL |
| `DB_NAME` | Nom de la base |

> Le fichier `.env` ne doit **jamais** être commité. Il est listé dans `.gitignore` et `.dockerignore`.

Les mêmes variables servent à deux endroits : au service `db` (création de l'utilisateur et de la base au premier démarrage) et au service `api` (connexion).

## Lancement avec Docker (recommandé)

```bash
docker compose up --build
```

Ce qui se passe :

1. Le service `db` (PostgreSQL 16 Alpine) démarre et passe en état `healthy` grâce à `pg_isready`.
2. Le service `api` attend ce healthcheck (`depends_on: service_healthy`), puis démarre.
3. Au démarrage, l'application crée les tables (`Base.metadata.create_all`) et ajoute les utilisateurs `alice` et `bob` si la table `users` est vide.

Accès :

- API : http://localhost:8000
- Documentation Swagger : http://localhost:8000/docs
- Documentation ReDoc : http://localhost:8000/redoc

Arrêt :

```bash
docker compose down        # arrête les conteneurs, conserve les données
docker compose down -v     # arrête et supprime aussi les volumes (base et uploads)
```

Volumes utilisés :

| Volume | Contenu |
|---|---|
| `postgres_data` | Données PostgreSQL |
| `uploads_data` | CSV envoyés (`/app/uploads`) |

## Lancement en local (sans Docker)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Il faut une base PostgreSQL accessible. Une option rapide consiste à ne lancer que le service `db` avec Docker (en ajoutant `ports: - "5432:5432"` à ce service dans `docker-compose.yml`) :

```bash
docker compose up -d db
```

Dans `.env`, mets `DB_HOST=localhost`. Uvicorn ne lit pas `.env` tout seul : soit tu exportes les variables dans ton shell, soit tu installes `python-dotenv` et appelles `load_dotenv()` au début de `app/database.py`.

```bash
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload
```

## Authentification

L'authentification est volontairement simple (projet pédagogique) :

1. `POST /login` avec un nom d'utilisateur existant (`alice` ou `bob`).
2. La réponse contient un `access_token`.
3. Toutes les autres routes exigent l'en-tête `Authorization: Bearer <access_token>`.

Dans Swagger (`/docs`), clique sur **Authorize** et colle le token.

Il n'y a pas de mot de passe, et les tokens sont gardés **en mémoire** : ils sont perdus à chaque redémarrage du serveur (y compris à chaque rechargement dû à `--reload`). Il faut alors refaire un `POST /login`.

## Endpoints

| Méthode | Route | Auth | Description |
|---|---|---|---|
| `POST` | `/login` | Non | Retourne un token Bearer pour un utilisateur existant |
| `GET` | `/users` | Oui | Liste des utilisateurs |
| `POST` | `/analyses/upload` | Oui | Envoie un CSV et lance l'analyse (réponse `202`) |
| `GET` | `/analyses` | Oui | Liste des analyses, de la plus récente à la plus ancienne |
| `GET` | `/analyses/stats/summary` | Oui | Statistiques globales |
| `GET` | `/analyses/{analysis_id}` | Oui | Détail d'une analyse |
| `DELETE` | `/analyses/{analysis_id}` | Oui | Supprime une analyse (propriétaire uniquement) |

### Codes d'erreur

| Code | Cas |
|---|---|
| `400` | Nom de fichier manquant, ou extension différente de `.csv` |
| `401` | Identifiants invalides, token invalide ou expiré |
| `403` | Suppression d'une analyse appartenant à un autre utilisateur |
| `404` | Analyse introuvable |

### Exemple de réponse : `GET /analyses/{id}`

```json
{
  "id": 1,
  "file_name": "ventes.csv",
  "status": "completed",
  "file_size": 2048,
  "rows_count": 120,
  "columns_count": 3,
  "columns": ["produit", "quantite", "prix"],
  "stats_summary": {
    "produit": { "type": "object" },
    "quantite": {
      "type": "int64",
      "describe": {
        "count": 120.0,
        "mean": 4.2,
        "std": 1.8,
        "min": 1.0,
        "25%": 3.0,
        "50%": 4.0,
        "75%": 5.0,
        "max": 9.0
      }
    }
  },
  "created_at": "2026-11-18T10:00:00",
  "finished_at": "2026-11-18T10:00:01",
  "error_message": null,
  "owner_id": 1
}
```

Les colonnes non numériques n'ont que le champ `type`. Les colonnes numériques ont en plus le bloc `describe`.

## Exemple complet avec curl

```bash
# 1. Se connecter et récupérer le token
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Envoyer un CSV
curl -X POST http://localhost:8000/analyses/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@ventes.csv"

# 3. Lister les analyses
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analyses

# 4. Voir le détail (remplace 1 par l'id retourné à l'upload)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analyses/1

# 5. Statistiques globales
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/analyses/stats/summary

# 6. Supprimer une analyse
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8000/analyses/1
```

Pour créer un CSV de test :

```bash
cat > ventes.csv << 'EOF'
produit,quantite,prix
stylo,10,1.5
cahier,5,3.2
sac,2,25.0
EOF
```

## Modèle de données

### Table `users`

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | Integer | Clé primaire |
| `username` | String | Unique, non nul |

### Table `analyses`

| Colonne | Type | Description |
|---|---|---|
| `id` | Integer | Clé primaire |
| `file_name` | String | Nom d'origine du fichier |
| `stored_file_name` | String | Nom sur disque (`<uuid>_<nom>.csv`), unique |
| `status` | Enum | `pending`, `running`, `completed`, `failed` |
| `file_size` | Integer | Taille du fichier en octets |
| `rows_count` | Integer | Nombre de lignes (après analyse) |
| `columns_count` | Integer | Nombre de colonnes (après analyse) |
| `columns` | JSON | Liste des noms de colonnes |
| `stats_summary` | JSON | Statistiques par colonne |
| `created_at` | DateTime | Date de création (UTC) |
| `finished_at` | DateTime | Date de fin de traitement (UTC) |
| `error_message` | Text | Message d'erreur en cas d'échec |
| `owner_id` | Integer | Clé étrangère vers `users.id` |

## Fonctionnement de l'analyse

1. `POST /analyses/upload` sauvegarde le fichier dans `uploads/` sous le nom `<uuid>_<nom_original>`, puis crée une ligne `AnalysisDB` avec le statut `pending`.
2. L'API répond tout de suite avec `202 Accepted`.
3. En arrière-plan, `process_analysis` passe le statut à `running`, lit le CSV avec pandas, puis enregistre le nombre de lignes, les colonnes et les statistiques.
4. Si tout se passe bien, le statut devient `completed` et `finished_at` est renseigné.
5. En cas d'erreur (CSV invalide, fichier vide, etc.), le statut devient `failed` et le message d'erreur est stocké dans `error_message`.

Pour suivre une analyse, interroge `GET /analyses/{id}` jusqu'à ce que le statut soit `completed` ou `failed`.

## Commandes utiles

```bash
docker compose ps                         # état des services (db doit être "healthy")
docker compose logs -f api                # logs de l'API en direct
docker compose exec api pip freeze        # versions des dépendances dans le conteneur
docker compose exec db psql -U taskuser -d tasks -c "\dt"           # lister les tables
docker compose exec db psql -U taskuser -d tasks -c "SELECT * FROM users;"
docker compose down -v                    # tout réinitialiser (base et uploads)
```

Adapte `taskuser` et `tasks` si tu as changé les valeurs dans `.env`.

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `manifest unknown` au build | Faute dans le nom de l'image (ex. `alpin` au lieu de `alpine`) | Utiliser `postgres:16-alpine` |
| `database files are incompatible with server` | Le volume contient des données d'une autre version de PostgreSQL | `docker compose down -v` puis relancer |
| `KeyError: 'DB_USER'` | Variable absente de `.env` | Vérifier que `.env` existe et contient toutes les variables |
| `could not translate host name "db"` | L'API tourne hors Docker avec `DB_HOST=db` | Mettre `DB_HOST=localhost` pour un lancement en local |
| `connection refused` en local | Le port 5432 du service `db` n'est pas exposé | Ajouter `ports: - "5432:5432"` au service `db` |
| `401 Invalid or expired token` | Le serveur a redémarré, les tokens sont en mémoire | Refaire `POST /login` |
| `400 Only CSV files are allowed` | Extension différente de `.csv` | Envoyer un fichier `.csv` |
| Analyse en `failed` | CSV mal formé ou vide | Consulter `error_message` dans le détail de l'analyse |

## Limites connues et pistes d'amélioration

- **Authentification minimale** : pas de mot de passe, tokens en mémoire. Pistes : JWT avec expiration, hachage de mots de passe, table de tokens.
- **Visibilité des analyses** : `GET /analyses` et `GET /analyses/{id}` renvoient les analyses de tous les utilisateurs. Seule la suppression est limitée au propriétaire. Piste : filtrer sur `owner_id`.
- **Suppression** : supprimer une analyse retire la ligne en base mais pas le fichier CSV dans `uploads/`.
- **Tâches en arrière-plan** : `BackgroundTasks` s'exécute dans le même processus que l'API. Pour de gros volumes, utiliser une file de tâches (Celery, RQ, Arq).
- **Gros fichiers** : le CSV est lu entièrement en mémoire. Pistes : lecture par blocs (`chunksize`), limite de taille à l'upload.
- **Migrations** : les tables sont créées par `create_all`, sans suivi des changements de schéma. Piste : Alembic.
- **Secrets** : les identifiants de démonstration (`taskuser` / `taskpassword`) sont à changer hors environnement de test.
- **Tests** : pas de tests automatisés pour l'instant. Piste : `pytest` avec `TestClient` de FastAPI.