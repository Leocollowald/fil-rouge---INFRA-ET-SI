# Documentation Y-Plaza — Partie DEV

**Projet** : Y-Plaza — Plateforme immobilière en ligne  
**Contexte** : Projet fil rouge B2 Ynov INFRA & DEV  
**Date** : Juin 2026

---

## 1. Architecture technique

### Stack

| Couche | Technologie | Version |
|--------|-------------|---------|
| Backend API | FastAPI | 0.115.0 |
| ORM | SQLAlchemy | 2.0.35 |
| Base de données | PostgreSQL | 15+ |
| Migrations | Alembic | 1.13.3 |
| Auth | JWT (python-jose) | HS256 |
| Hash mots de passe | passlib + bcrypt | 1.7.4 + 3.2.2 |
| Analyse de données | pandas | 2.2.3 |
| Upload images | Pillow | 11.2.1 |
| Frontend | Jinja2 + Vanilla JS/CSS | 3.1.4 |
| Serveur web (prod) | nginx + uvicorn | — |

### Schéma d'infrastructure

```
Internet → DMZ (SRV-WEB1-DEB13, 10.0.20.20)
         → OPNsense (firewall, règle TCP 5432)
         → LAN Backend (SRV-DB2-DEB13, 10.0.30.30)
```

Le serveur web dans la DMZ héberge l'application FastAPI + nginx.  
La base de données PostgreSQL est dans le LAN Backend, isolée de l'extérieur.

### Pattern architectural — 3 couches

```
Endpoint (FastAPI) → Service (logique métier) → Repository (accès DB)
```

- **Endpoints** : routing, validation des entrées, gestion des droits
- **Services** : logique métier, vérifications de permissions
- **Repositories** : queries SQLAlchemy, abstraction `BaseRepository[T]`

---

## 2. Modèle de données

### Schéma relationnel

```
agencies ─────────────────────────────────────────────────────────┐
  │                                                               │
  ├──< users (agency_id FK) ────────────────────────────────┐    │
  │                                                          │    │
  └──< properties (agency_id FK, agent_id FK) ──────────────┤    │
         │                                                   │    │
         ├──< property_images (property_id FK, CASCADE)      │    │
         ├──< favorites (property_id + user_id FK, CASCADE)  │    │
         └──< transactions (property_id + buyer_id + agent_id FK)
```

### Tables

**`agencies`** — Agences immobilières
- `id` UUID PK, `name`, `city`, `address`, `zip_code`, `phone`, `email`, `created_at`

**`users`** — Utilisateurs
- `id` UUID PK, `email` UNIQUE, `hashed_password`, `first_name`, `last_name`
- `role` ENUM : client | commercial | direction | communication_marketing | administratif_rh | it_support
- `is_active`, `agency_id` FK → agencies, `created_at`

**`properties`** — Biens immobiliers
- `id` UUID PK, `title`, `description`, `price`, `surface`, `rooms`, `bedrooms`, `bathrooms`
- `property_type` ENUM : apartment | house | commercial | land | office
- `status` ENUM : available | under_offer | sold | rented
- `transaction_type` ENUM : sale | rental
- `city`, `address`, `zip_code`, `latitude`, `longitude`
- `agency_id` FK, `agent_id` FK → users, `created_at`, `updated_at`

**`property_images`** — Photos des biens
- `id` UUID PK, `property_id` FK (CASCADE DELETE), `url` (chemin local), `is_primary`, `created_at`

**`favorites`** — Favoris utilisateurs
- `id` UUID PK, `user_id` FK (CASCADE), `property_id` FK (CASCADE), `created_at`

**`transactions`** — Demandes d'achat/visite
- `id` UUID PK, `property_id` FK, `buyer_id` FK, `agent_id` FK
- `offered_price`, `status` ENUM, `notes`, `created_at`, `updated_at`

---

## 3. API — Endpoints

**Base URL** : `http://localhost:8000/api/v1` (dev) | `https://yplaza.exemple.fr/api/v1` (prod)

### Authentification `/auth`

| Méthode | Route | Description | Auth |
|---------|-------|-------------|------|
| POST | `/auth/register` | Créer un compte | Non |
| POST | `/auth/login` | Connexion → tokens | Non |
| POST | `/auth/refresh` | Rafraîchir l'access token | Cookie/Header |
| POST | `/auth/logout` | Déconnexion | — |

**Tokens** : JWT HS256, access (30 min) + refresh (7 jours).  
Stockage : httponly cookie (access) + localStorage (access + refresh pour les appels API).

### Biens `/properties`

| Méthode | Route | Description | Auth |
|---------|-------|-------------|------|
| GET | `/properties/` | Liste filtrée paginée | Non |
| GET | `/properties/{id}` | Détail d'un bien | Non |
| GET | `/properties/me` | Mes annonces (agent) | commercial+ |
| GET | `/properties/me/favorites` | Mes favoris | tout utilisateur |
| POST | `/properties/` | Créer un bien | commercial+ |
| PATCH | `/properties/{id}` | Modifier un bien | propriétaire ou direction |
| DELETE | `/properties/{id}` | Supprimer | propriétaire ou direction |
| POST | `/properties/{id}/favorite` | Toggle favori | tout utilisateur |
| POST | `/properties/{id}/images` | Upload photos | propriétaire ou direction |
| DELETE | `/properties/{id}/images/{img_id}` | Supprimer une photo | propriétaire ou direction |

**Filtres disponibles sur GET `/properties/`** :
`city`, `property_type`, `transaction_type`, `min_price`, `max_price`, `min_surface`, `rooms`, `status`, `page`, `per_page`

### Agences `/agencies`

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/agencies/` | Liste toutes les agences |
| GET | `/agencies/{id}` | Détail d'une agence |

### Transactions `/transactions`

| Méthode | Route | Description | Auth |
|---------|-------|-------------|------|
| POST | `/transactions/` | Créer une demande | tout utilisateur |
| GET | `/transactions/me` | Mes demandes (client) | tout utilisateur |
| GET | `/transactions/agent` | Demandes reçues (agent) | commercial+ |
| PATCH | `/transactions/{id}` | Accepter/Refuser | agent du bien |

### Utilisateurs `/users`

| Méthode | Route | Description | Auth |
|---------|-------|-------------|------|
| GET | `/users/me` | Mon profil | tout utilisateur |
| PATCH | `/users/me` | Modifier mon profil | tout utilisateur |
| GET | `/users/` | Liste tous les users | direction/IT |
| PATCH | `/users/{id}/role` | Changer le rôle | direction/IT |

### Rapports `/reports`

| Méthode | Route | Description | Auth |
|---------|-------|-------------|------|
| GET | `/reports/catalogue` | Stats globales du catalogue | direction/IT |
| GET | `/reports/ventes` | CA, volumes, par agence/ville/mois | direction/IT |
| GET | `/reports/populaires` | Top biens par popularité | direction/IT |
| GET | `/reports/prix-m2` | Prix au m² par ville | direction/IT |
| GET | `/reports/delai-vente` | Délai moyen de vente | direction/IT |

---

## 4. Upload d'images

### Fonctionnement

1. L'agent crée le bien (`POST /properties/`)
2. L'agent uploade les photos (`POST /properties/{id}/images`, multipart/form-data)
3. Le serveur :
   - Valide le type MIME déclaré (`image/jpeg`, `image/png`, `image/webp`)
   - Valide le contenu réel avec **Pillow** (contre le spoofing de content-type)
   - Vérifie la taille (max 5 Mo par fichier)
   - Génère un nom UUID côté serveur (anti path traversal)
   - Sauvegarde dans `uploads/properties/{property_id}/`
   - Enregistre le chemin en DB dans `property_images.url`
4. En production, nginx sert `/uploads/` directement (plus performant que FastAPI)

### Structure des dossiers

```
uploads/
└── properties/
    └── {property_id}/
        ├── a3f2b1c4-...-uuid.jpg   ← nom généré par le serveur
        └── 9e7d3a2f-...-uuid.png
```

---

## 5. Module d'analyse de données

### Fichier : `backend/app/analysis/reports.py`

Toutes les fonctions utilisent SQLAlchemy `text()` pour les requêtes SQL brutes, puis pandas pour l'agrégation et le nettoyage.

| Fonction | SQL brut | pandas |
|----------|----------|--------|
| `rapport_ventes()` | JOIN transactions + properties + agencies | groupby agence/ville/type/mois, sum/count |
| `biens_populaires()` | LEFT JOIN favorites + transactions | tri par score populaire |
| `prix_m2_par_ville()` | AVG(price/surface), MIN, MAX | dropna, tri DESC |
| `stats_catalogue()` | COUNT FILTER par statut, AVG/MIN/MAX prix | conversion types numpy |
| `delai_vente_par_ville()` | EXTRACT(EPOCH...) entre création et finalisation | dropna |

---

## 6. Matrice des droits

| Fonctionnalité | client | commercial | direction | communication_marketing | administratif_rh | it_support |
|----------------|--------|------------|-----------|------------------------|------------------|------------|
| Voir annonces | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Gérer favoris | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Faire une demande | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Publier un bien | — | ✓ | ✓ | — | — | ✓ |
| Upload images | — | ✓ (son bien) | ✓ | — | — | ✓ |
| Traiter demandes | — | ✓ (son bien) | ✓ | — | — | ✓ |
| Gérer utilisateurs | — | — | ✓ | — | — | ✓ |
| Voir rapports | — | — | ✓ | — | — | ✓ |

---

## 7. Guide de lancement (développement)

### Prérequis

- PostgreSQL installé sur SRV-DB2-DEB13 (10.0.30.30)
- Conda avec environnement `y-plaza`
- Règle OPNsense : DMZ (10.0.20.20) → LAN Backend (10.0.30.30) TCP 5432

### Création de la base de données

```bash
# Sur SRV-DB2-DEB13
sudo -u postgres psql
CREATE USER yplaza WITH ENCRYPTED PASSWORD 'motdepasse';
CREATE DATABASE yplaza OWNER yplaza;
GRANT ALL PRIVILEGES ON DATABASE yplaza TO yplaza;
\q
```

### Installation et lancement

```bash
# Cloner et se placer dans le dossier backend
cd backend

# Installer les dépendances
conda activate y-plaza
pip install -r requirements.txt

# Créer le fichier d'environnement
cp .env.example .env
# Éditer .env : renseigner DATABASE_URL, SECRET_KEY

# Appliquer les migrations (crée toutes les tables)
alembic upgrade head

# Peupler la DB avec des données de démo
python seed.py

# Lancer le serveur
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Accès

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | Page d'accueil |
| `http://localhost:8000/api/docs` | Swagger UI (DEBUG=True uniquement) |
| `http://localhost:8000/dashboard` | Espace utilisateur |

### Lancer les tests

```bash
cd backend
pytest tests/ -v
```

---

## 8. Choix techniques justifiés

**FastAPI plutôt que Flask** : validation automatique via Pydantic, documentation Swagger générée, async natif, typage fort. Adapté à une API REST moderne.

**SQLAlchemy 2.0 + Repository pattern** : abstraction de la couche DB, tests avec SQLite sans changer les modèles (type `Uuid` générique), facilite les futures migrations de DB.

**JWT httponly cookie + localStorage** : le cookie httponly protège contre XSS pour l'accès aux pages, localStorage permet les appels API JS. Compromis pragmatique ; une implémentation plus stricte utiliserait uniquement le cookie.

**Stockage images local (pas de cloud)** : contrainte explicite du brief. Nginx sert `/uploads/` en production pour les performances. Pillow valide le contenu réel (le MIME type déclaré par le client est spoofable).

**pandas + SQL brut pour les rapports** : `sqlalchemy.text()` permet des requêtes SQL lisibles et optimisées, pandas gère l'agrégation et le nettoyage. Séparation claire entre récupération des données (SQL) et traitement (Python).
