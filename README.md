# Prophotos

Application web de gestion de photos avec reconnaissance faciale. Architecture microservices déployable via Docker Compose et Jenkins.

---

## Table des matières

1. [Architecture](#architecture)
2. [Prérequis](#prérequis)
3. [Services](#services)
4. [Variables d'environnement](#variables-denvironnement)
5. [Développement local](#développement-local)
6. [Tests](#tests)
7. [Déploiement](#déploiement)
   - [Déploiement manuel](#déploiement-manuel)
   - [Déploiement via Jenkins (CI/CD)](#déploiement-via-jenkins-cicd)
8. [Configuration Nginx](#configuration-nginx)
9. [Monitoring](#monitoring)
10. [GPU Worker](#gpu-worker)
11. [Structure du projet](#structure-du-projet)

---

## Architecture

Prophotos est une application microservices composée de :

```
                         ┌─────────────────────────────┐
                         │          Nginx               │
                         │  (Reverse Proxy + SSL/TLS)   │
                         │   votre-domaine.com          │
                         └──────────┬──────────────────┘
                                    │
            ┌───────────┬───────────┼────────────┐
            │           │           │            │
     ┌──────▼────┐ ┌────▼─────┐ ┌──▼───────┐   │
     │ Frontend  │ │ backend- │ │ backend- │   │
     │  Vue 3    │ │  users   │ │  files   │   │
     │ :8082     │ │  :8001   │ │  :8002   │   │
     └───────────┘ └──────────┘ └──────────┘   │
                                            ┌───▼──────┐
                                            │ backend- │
                                            │  recfac  │
                                            │  :8003   │
                                            └────┬─────┘
                                                 │
                                          ┌──────▼──────┐
                                          │  gpu-worker │
                                          │  InsightFace│
                                          │  (externe)  │
                                          └─────────────┘
            ┌──────────────────────────────────────────┐
            │              PostgreSQL :5432             │
            └──────────────────────────────────────────┘
            ┌────────────┐  ┌────────────┐  ┌──────────┐
            │ Prometheus │  │  Grafana   │  │cAdvisor  │
            │   :9090    │  │   :3000    │  │  :8085   │
            └────────────┘  └────────────┘  └──────────┘
```

---

## Prérequis

| Outil | Version minimale |
|-------|-----------------|
| Docker | 24+ |
| Docker Compose | v2 (plugin) |
| Git | 2.x |
| Python | 3.11 (pour développement local des backends) |
| Node.js | 18+ (pour développement local du frontend) |

Pour le GPU Worker uniquement :
- Serveur avec GPU NVIDIA
- NVIDIA Container Toolkit installé
- `onnxruntime-gpu`

---

## Services

| Service | Port exposé | Rôle |
|---------|-------------|------|
| `prophotos` | 8082 | Frontend Vue 3 (Nginx) |
| `users` | 8001 | API de gestion des utilisateurs (Django) |
| `files` | 8002 | API de gestion des photos (Django + pyvips) |
| `recfac` | 8003 | API de reconnaissance faciale (Django) |
| `gpu-worker` | 8000 | Worker GPU InsightFace (FastAPI) — déployé séparément |
| `db` | 5432 | Base de données PostgreSQL |
| `prometheus` | 9090 | Collecte de métriques |
| `grafana` | 3000 | Dashboards de monitoring |
| `cadvisor` | 8085 | Métriques des conteneurs |

Les images Docker sont à publier sur votre propre registry (Docker Hub ou registry privé). Adaptez les noms d'images dans `docker-compose.yml` selon votre organisation.

---

## Variables d'environnement

Copiez le fichier exemple et remplissez les valeurs :

```bash
cp envexemple .env.prod.backend
```

| Variable | Description | Exemple |
|----------|-------------|---------|
| `DEBUG` | Mode debug Django | `False` |
| `SECRET_KEY` | Clé secrète Django (partagée entre backends) | `une-cle-aleatoire-longue` |
| `ALLOWED_HOSTS` | Hôtes Django autorisés | `votre-domaine.com,localhost` |
| `POSTGRES_DB` | Nom de la base de données | `prophotos` |
| `POSTGRES_USER` | Utilisateur PostgreSQL | `prophotos` |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | `strongpassword` |
| `POSTGRES_HOST` | Hôte PostgreSQL | `db` |
| `POSTGRES_PORT` | Port PostgreSQL | `5432` |
| `TOKEN_EXPIRATION_HOURS` | Durée de vie des tokens JWT | `24` |
| `EMAIL_BACKEND` | Backend email Django | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | Serveur SMTP | `smtp.example.com` |
| `EMAIL_PORT` | Port SMTP | `587` |
| `EMAIL_USE_TLS` | TLS activé | `True` |
| `EMAIL_HOST_USER` | Adresse email d'envoi | `noreply@example.com` |
| `EMAIL_HOST_PASSWORD` | Mot de passe email | `apppassword` |
| `EMAIL_VERIFICATION_BASE` | URL de base pour les liens de vérification | `https://votre-domaine.com` |
| `ADMIN_EMAIL` | Email administrateur | `admin@example.com` |
| `FILES_ROOT_DIR` | Chemin interne des photos dans le conteneur | `/data/photos` |
| `PHOTOS_HOST_DIR` | Chemin hôte des photos montées dans le conteneur | `/srv/photos` |
| `VUE_APP_USERS_API_URL` | URL publique de l'API users (injectée au build Vue) | `https://votre-domaine.com/api/users` |
| `VUE_APP_FILES_API_URL` | URL publique de l'API files (injectée au build Vue) | `https://votre-domaine.com/api/files` |
| `VUE_APP_RECFAC_API_URL` | URL publique de l'API recfac (injectée au build Vue) | `https://votre-domaine.com/api/recfac` |
| `GPU_WORKER_URL` | URL du serveur GPU Worker | `http://gpu-server:8000` |
| `GPU_WORKER_TOKEN` | Token d'authentification du GPU Worker | `secret-token` |
| `GRAFANA_ADMIN_USER` | Utilisateur admin Grafana | `admin` |
| `GRAFANA_ADMIN_PASSWORD` | Mot de passe admin Grafana | `strongpassword` |

> **Note :** Les variables `VUE_APP_*` sont injectées au moment du **build** de l'image Docker frontend. Elles doivent être présentes dans `.env.prod.backend` avant de lancer `docker compose build`.

---

## Développement local

### Frontend (Vue 3)

```bash
cd prophotos
npm install
npm run serve
```

L'application sera disponible sur `http://localhost:8080`.

Pour pointer vers vos backends locaux, créez un fichier `.env.local` dans `prophotos/` :

```env
VUE_APP_USERS_API_URL=http://localhost:8001
VUE_APP_FILES_API_URL=http://localhost:8002
VUE_APP_RECFAC_API_URL=http://localhost:8003
```

### Backend (Django)

Chaque service backend suit la même structure. Exemple pour `backend-users` :

```bash
cd backend-users
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Créer un fichier .env local
cp ../envexemple .env

# Appliquer les migrations
python manage.py migrate

# Lancer le serveur
python manage.py runserver 8001
```

Répéter pour `backend-files` (port 8002) et `backend-recfac` (port 8003).

### Stack complète avec Docker Compose

```bash
# Copier et remplir les variables d'environnement
cp envexemple .env.prod.backend
# (éditer .env.prod.backend avec vos valeurs)

# Construire et démarrer tous les services
docker compose --env-file .env.prod.backend up --build -d

# Vérifier les logs
docker compose logs -f

# Arrêter la stack
docker compose --env-file .env.prod.backend down
```

---

## Tests

Les tests sont écrits avec `unittest` (Django test runner). Chaque service a ses propres settings de test.

### Lancer les tests manuellement

```bash
# Tests du service Users
cd backend-users
python manage.py test users --settings=users_service.test_settings --verbosity=2

# Tests du service Files
cd backend-files
python manage.py test files --settings=files_service.test_settings --verbosity=2

# Tests du service Recfac
cd backend-recfac
python manage.py test recfac --settings=recfac_service.test_settings --verbosity=2
```

### Lancer les tests via Docker

```bash
# Users
cd backend-users
docker build -t test-users-temp . && \
docker run --rm test-users-temp python manage.py test users \
  --settings=users_service.test_settings --verbosity=2
docker rmi test-users-temp

# Files
cd backend-files
docker build -t test-files-temp . && \
docker run --rm test-files-temp python manage.py test files \
  --settings=files_service.test_settings --verbosity=2
docker rmi test-files-temp

# Recfac
cd backend-recfac
docker build -t test-recfac-temp . && \
docker run --rm test-recfac-temp python manage.py test recfac \
  --settings=recfac_service.test_settings --verbosity=2
docker rmi test-recfac-temp
```

---

## Déploiement

### Déploiement manuel

#### 1. Préparer le serveur

```bash
# Cloner le dépôt
git clone git@github.com:<votre-org>/Prophotos.git
cd Prophotos

# Copier et remplir le fichier d'environnement
cp envexemple .env.prod.backend
nano .env.prod.backend
```

#### 2. Construire les images

```bash
docker compose --env-file .env.prod.backend build
```

#### 3. Tagger les images pour versioning

Adaptez `DOCKERHUB_USER` et les noms d'images selon votre configuration dans `docker-compose.yml`.

```bash
TAG=v1.0.0
DOCKERHUB_USER=votre-utilisateur

docker tag ${DOCKERHUB_USER}/photos:latest          ${DOCKERHUB_USER}/photos:${TAG}
docker tag ${DOCKERHUB_USER}/photos_files:latest    ${DOCKERHUB_USER}/photos_files:${TAG}
docker tag ${DOCKERHUB_USER}/photos_users:latest    ${DOCKERHUB_USER}/photos_users:${TAG}
docker tag ${DOCKERHUB_USER}/photos_recfac:latest   ${DOCKERHUB_USER}/photos_recfac:${TAG}
docker tag ${DOCKERHUB_USER}/photos_prometheus:latest ${DOCKERHUB_USER}/photos_prometheus:${TAG}
docker tag ${DOCKERHUB_USER}/photos_grafana:latest    ${DOCKERHUB_USER}/photos_grafana:${TAG}
```

#### 4. Construire et tagger le GPU Worker

```bash
docker build -t ${DOCKERHUB_USER}/photos_gpu_worker:latest ./gpu-worker
docker tag ${DOCKERHUB_USER}/photos_gpu_worker:latest ${DOCKERHUB_USER}/photos_gpu_worker:${TAG}
```

#### 5. Pousser les images sur le registry

```bash
docker login

docker push ${DOCKERHUB_USER}/photos:${TAG}          && docker push ${DOCKERHUB_USER}/photos:latest
docker push ${DOCKERHUB_USER}/photos_files:${TAG}    && docker push ${DOCKERHUB_USER}/photos_files:latest
docker push ${DOCKERHUB_USER}/photos_users:${TAG}    && docker push ${DOCKERHUB_USER}/photos_users:latest
docker push ${DOCKERHUB_USER}/photos_recfac:${TAG}   && docker push ${DOCKERHUB_USER}/photos_recfac:latest
docker push ${DOCKERHUB_USER}/photos_prometheus:${TAG} && docker push ${DOCKERHUB_USER}/photos_prometheus:latest
docker push ${DOCKERHUB_USER}/photos_grafana:${TAG}    && docker push ${DOCKERHUB_USER}/photos_grafana:latest
docker push ${DOCKERHUB_USER}/photos_gpu_worker:${TAG} && docker push ${DOCKERHUB_USER}/photos_gpu_worker:latest
```

#### 6. Déployer la stack

```bash
# Arrêter les conteneurs existants
docker compose --env-file .env.prod.backend down

# Redémarrer avec les nouvelles images
docker compose --env-file .env.prod.backend up -d

# Vérifier que tout est up
docker compose ps
```

#### 7. Déployer le GPU Worker sur le serveur GPU

Le GPU Worker est déployé **séparément** sur un serveur disposant d'un GPU NVIDIA :

```bash
# Sur le serveur GPU
docker pull ${DOCKERHUB_USER}/photos_gpu_worker:${TAG}

docker run -d \
  --gpus all \
  --restart unless-stopped \
  -p 8000:8000 \
  -e GPU_WORKER_TOKEN=votre_token_secret \
  --name prophotos-gpu-worker \
  ${DOCKERHUB_USER}/photos_gpu_worker:${TAG}

# Vérifier les logs de démarrage
docker logs -f prophotos-gpu-worker
```

> **Important :** Après le démarrage, InsightFace charge le modèle `buffalo_l` (~500 MB). Attendez le message `✓ GPU initialization successful` ou `✓ CPU initialization successful` avant d'envoyer des requêtes.

---

### Déploiement via Jenkins (CI/CD)

Le fichier `Jenkinsfile` à la racine définit le pipeline complet. Il est déclenché automatiquement depuis le dépôt Git via webhook.

#### Prérequis Jenkins

1. **Credentials à configurer dans Jenkins** (Manage Jenkins → Credentials) :

   | ID (exemple) | Type | Contenu |
   |---|---|---|
   | `github-ssh-key` | SSH Username with private key | Clé SSH pour cloner le dépôt |
   | `env-file-backend` | Secret file | Fichier `.env.prod.backend` complet |
   | `dockerhub-credentials` | Username with password | Login / mot de passe Docker Hub |

   > Les IDs ci-dessus sont des exemples. Adaptez-les aux valeurs réelles renseignées dans votre Jenkins, et mettez à jour les références correspondantes dans le `Jenkinsfile`.

2. **Plugins Jenkins requis :**
   - Pipeline
   - SSH Agent
   - Credentials Binding

3. **Agent Jenkins :** le nœud doit avoir Docker et Docker Compose installés, et l'utilisateur Jenkins doit appartenir au groupe `docker`.

#### Structure du Jenkinsfile

Le `Jenkinsfile` reçoit un paramètre `TAG` (numéro de build, SHA Git, version sémantique…) et enchaîne les stages suivants :

```
Checkout  →  Tests (parallèle)  →  Prepare env  →  Build  →  Login Registry
    →  Tag Images  →  Build GPU Worker  →  Push (parallèle)  →  Deploy
```

| Stage | Description |
|-------|-------------|
| **Checkout** | Clone le dépôt depuis la branche `main` via la clé SSH Jenkins |
| **Run Tests** | Lance les tests des 3 backends **en parallèle** dans des conteneurs Docker éphémères (buildés et supprimés à la volée) |
| **Prepare env file** | Charge le fichier secret `.env.prod.backend` depuis les credentials Jenkins |
| **Build** | `docker compose --env-file .env.prod.backend build` |
| **Login to Registry** | `docker login` avec les credentials Jenkins |
| **Tag Images** | Retag de chaque image `latest` avec le `TAG` passé en paramètre |
| **Build GPU Worker** | Build séparé de l'image GPU Worker (contexte `./gpu-worker`) |
| **Push Images** | Push en **parallèle** des images `latest` et `TAG` vers le registry |
| **Deploy** | `docker compose down` puis `docker compose up -d` sur le serveur |

#### Exemple de Jenkinsfile générique

Voici la structure du pipeline, avec les placeholders à adapter à votre environnement :

```groovy
pipeline {
  agent any

  parameters {
    string(name: 'TAG', defaultValue: 'latest', description: 'Tag Docker à utiliser (ex: numéro de build, SHA git)')
  }

  environment {
    COMPOSE_FILE = 'docker-compose.yml'
    TAG          = "${params.TAG}"
    // Préfixe de vos images Docker (ex: "monorg/monapp")
    IMAGE_PREFIX = "votre-dockerhub-user/prophotos"
  }

  stages {

    stage('Checkout') {
      steps {
        sshagent(['<id-credential-ssh-github>']) {
          git branch: 'main', url: 'git@github.com:<votre-org>/Prophotos.git'
        }
      }
    }

    stage('Run Tests') {
      parallel {
        stage('Test Users Service') {
          steps {
            sh '''
              cd backend-users
              docker build -t test-users-temp .
              docker run --rm test-users-temp \
                python manage.py test users \
                --settings=users_service.test_settings --verbosity=2
              docker rmi test-users-temp || true
            '''
          }
        }
        stage('Test Files Service') {
          steps {
            sh '''
              cd backend-files
              docker build -t test-files-temp .
              docker run --rm test-files-temp \
                python manage.py test files \
                --settings=files_service.test_settings --verbosity=2
              docker rmi test-files-temp || true
            '''
          }
        }
        stage('Test Recfac Service') {
          steps {
            sh '''
              cd backend-recfac
              docker build -t test-recfac-temp .
              docker run --rm test-recfac-temp \
                python manage.py test recfac \
                --settings=recfac_service.test_settings --verbosity=2
              docker rmi test-recfac-temp || true
            '''
          }
        }
      }
    }

    stage('Prepare env file') {
      steps {
        withCredentials([file(credentialsId: '<id-credential-env-file>', variable: 'ENV_BE')]) {
          sh '''
            cp "$ENV_BE" .env.prod.backend
          '''
        }
      }
    }

    stage('Build') {
      steps {
        sh 'docker compose --env-file .env.prod.backend build'
      }
    }

    stage('Login to Registry') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: '<id-credential-dockerhub>',
          usernameVariable: 'REGISTRY_USER',
          passwordVariable: 'REGISTRY_PASS'
        )]) {
          sh 'echo "$REGISTRY_PASS" | docker login -u "$REGISTRY_USER" --password-stdin'
        }
      }
    }

    stage('Tag Images') {
      steps {
        sh '''
          docker tag ${IMAGE_PREFIX}_frontend:latest   ${IMAGE_PREFIX}_frontend:${TAG}
          docker tag ${IMAGE_PREFIX}_users:latest      ${IMAGE_PREFIX}_users:${TAG}
          docker tag ${IMAGE_PREFIX}_files:latest      ${IMAGE_PREFIX}_files:${TAG}
          docker tag ${IMAGE_PREFIX}_recfac:latest     ${IMAGE_PREFIX}_recfac:${TAG}
          docker tag ${IMAGE_PREFIX}_prometheus:latest ${IMAGE_PREFIX}_prometheus:${TAG}
          docker tag ${IMAGE_PREFIX}_grafana:latest    ${IMAGE_PREFIX}_grafana:${TAG}
        '''
      }
    }

    stage('Build GPU Worker') {
      steps {
        sh '''
          docker build -t ${IMAGE_PREFIX}_gpu_worker:latest ./gpu-worker
          docker tag ${IMAGE_PREFIX}_gpu_worker:latest ${IMAGE_PREFIX}_gpu_worker:${TAG}
        '''
      }
    }

    stage('Push Images') {
      parallel {
        stage('Push Frontend')   { steps { sh 'docker push ${IMAGE_PREFIX}_frontend:${TAG} && docker push ${IMAGE_PREFIX}_frontend:latest' } }
        stage('Push Users')      { steps { sh 'docker push ${IMAGE_PREFIX}_users:${TAG}    && docker push ${IMAGE_PREFIX}_users:latest' } }
        stage('Push Files')      { steps { sh 'docker push ${IMAGE_PREFIX}_files:${TAG}    && docker push ${IMAGE_PREFIX}_files:latest' } }
        stage('Push Recfac')     { steps { sh 'docker push ${IMAGE_PREFIX}_recfac:${TAG}   && docker push ${IMAGE_PREFIX}_recfac:latest' } }
        stage('Push GPU Worker') { steps { sh 'docker push ${IMAGE_PREFIX}_gpu_worker:${TAG} && docker push ${IMAGE_PREFIX}_gpu_worker:latest' } }
        stage('Push Prometheus') { steps { sh 'docker push ${IMAGE_PREFIX}_prometheus:${TAG} && docker push ${IMAGE_PREFIX}_prometheus:latest' } }
        stage('Push Grafana')    { steps { sh 'docker push ${IMAGE_PREFIX}_grafana:${TAG}    && docker push ${IMAGE_PREFIX}_grafana:latest' } }
      }
    }

    stage('Deploy') {
      steps {
        sh '''
          docker compose --env-file .env.prod.backend down || true
          docker compose --env-file .env.prod.backend up -d
        '''
      }
    }
  }

  post {
    success {
      echo "Déploiement ${TAG} terminé avec succès."
      echo "Le GPU Worker nécessite un déploiement manuel sur le serveur GPU (voir section GPU Worker)."
    }
    failure {
      echo "Le pipeline a échoué."
    }
    always {
      sh 'docker image prune -f || true'
    }
  }
}
```

#### Déclencher un build Jenkins

**Via l'interface Jenkins :**
1. Ouvrir le job Jenkins du projet
2. Cliquer sur "Build with Parameters"
3. Renseigner le paramètre `TAG` (ex: `1.0.0`, `build-42`, SHA Git court)
4. Lancer le build

**Via webhook Git :**
Configurez un webhook dans votre dépôt GitHub/GitLab pointant vers :
```
https://votre-jenkins.com/github-webhook/
```
Chaque push sur `main` déclenchera automatiquement le pipeline.

---

## Configuration Nginx

Le fichier `nginx.conf` à la racine est un exemple de configuration reverse proxy pour la production. Il gère :

- Redirection HTTP → HTTPS
- Certificats SSL via Let's Encrypt (Certbot)
- Routage des requêtes vers les microservices :

| Route Nginx | Service cible |
|-------------|---------------|
| `/api/users/` | `localhost:8001/users/` |
| `/api/files/` | `localhost:8002/files/` |
| `/api/recfac/` | `localhost:8003/recfac/` |
| `/` | `localhost:8082/` (frontend Vue) |
| `/github-webhook/` | `localhost:<port-jenkins>/github-webhook/` |

- Protection anti-bots et rate limiting (10 req/s par IP)

Pour obtenir un certificat SSL avec Certbot :

```bash
sudo certbot --nginx -d votre-domaine.com
```

Pour appliquer une modification Nginx :

```bash
sudo nginx -t                  # Vérifier la syntaxe
sudo systemctl reload nginx    # Recharger sans couper les connexions
```

Pour renouveler les certificats :

```bash
sudo certbot renew --dry-run   # Tester
sudo certbot renew             # Renouveler
```

---

## Monitoring

### Accès

| Interface | Port | Identifiants par défaut |
|-----------|------|------------------------|
| Grafana | 3000 | `admin` / `admin` (à changer) |
| Prometheus | 9090 | — |
| cAdvisor | 8085 | — |

### Métriques collectées

- **django-prometheus** : requêtes HTTP, latences et codes de réponse pour chaque backend
- **cAdvisor** : CPU, mémoire, réseau et disque par conteneur Docker
- **Rétention Prometheus** : 30 jours (configurable dans `docker-compose.yml`)

### Changer les identifiants Grafana

Dans `.env.prod.backend` :

```env
GRAFANA_ADMIN_USER=monuser
GRAFANA_ADMIN_PASSWORD=monmotdepasse
```

Puis redémarrer uniquement Grafana :

```bash
docker compose --env-file .env.prod.backend up -d grafana
```

---

## GPU Worker

Service FastAPI indépendant utilisant **InsightFace** (modèle `buffalo_l`) pour la détection et l'extraction d'embeddings faciaux. Il est déployé sur un serveur séparé disposant d'un GPU NVIDIA.

### Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | Vérification de l'état du service |
| `POST` | `/detect` | Détection des visages dans une image |
| `POST` | `/embed` | Extraction des embeddings faciaux |

### Authentification

Toutes les requêtes doivent inclure le header :
```
X-Token: <GPU_WORKER_TOKEN>
```

La valeur du token est définie par la variable d'environnement `GPU_WORKER_TOKEN` au démarrage du conteneur.

### Forcer le mode CPU (pour les tests sans GPU)

```bash
docker run -d \
  -p 8000:8000 \
  -e GPU_WORKER_TOKEN=votre_token \
  -e FORCE_CPU=1 \
  votre-image/photos_gpu_worker:latest
```

### Changer le modèle InsightFace

Par défaut le modèle `buffalo_l` est utilisé. Pour utiliser un modèle plus léger :

```bash
-e INSIGHTFACE_MODEL=buffalo_s
```

---

## Structure du projet

```
Prophotos/
├── Jenkinsfile              # Pipeline CI/CD Jenkins
├── docker-compose.yml       # Orchestration de tous les services
├── nginx.conf               # Exemple de config reverse proxy production
├── envexemple               # Template des variables d'environnement
│
├── prophotos/               # Frontend Vue 3
│   ├── src/
│   │   ├── views/           # Pages (HomePage, ImagePage, ...)
│   │   ├── components/      # Composants réutilisables
│   │   └── router/          # Routes Vue Router
│   ├── dockerfile           # Build multi-stage (Node build + Nginx serve)
│   └── package.json
│
├── backend-users/           # Microservice utilisateurs (Django)
│   ├── users/               # App Django principale
│   ├── users_service/       # Settings et config Django
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── requirements.txt
│
├── backend-files/           # Microservice fichiers/photos (Django + pyvips)
│   ├── files/               # App Django principale
│   ├── files_service/       # Settings et config Django
│   ├── Dockerfile
│   └── requirements.txt
│
├── backend-recfac/          # Microservice reconnaissance faciale (Django)
│   ├── recfac/              # App Django principale
│   ├── recfac_service/      # Settings et config Django
│   ├── Dockerfile
│   └── requirements.txt
│
├── gpu-worker/              # Worker GPU (FastAPI + InsightFace)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── monitoring/              # Stack Prometheus + Grafana
    ├── prometheus.yml
    ├── Dockerfile.prometheus
    ├── Dockerfile.grafana
    └── grafana/             # Dashboards Grafana préconfigurés
```
