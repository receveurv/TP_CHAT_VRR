# Assistant Achats

Assistant conversationnel en français pour consulter un catalogue de produits et les fiches de ses fournisseurs. Le modèle Azure OpenAI sélectionne les outils adaptés : recherche dans MySQL pour les produits et recherche documentaire locale pour les informations fournisseurs.

## Fonctionnalités

- Recherche de produits par mot-clé, fournisseur, disponibilité ou fourchette de prix.
- Recherche dans les PDF fournisseurs avec classement BM25 et références de page.
- Conversation avec conservation du fil de discussion pendant l'exécution.
- Filtrage de certaines demandes suspectes et limitation du nombre de requêtes.
- Connexion MySQL en lecture seule; les requêtes SQL sont paramétrées.

## Prérequis

- Python 3.10 ou ultérieur.
- Une base MySQL 8 ou MariaDB 10.x.
- Un déploiement de modèle de chat Azure OpenAI et ses identifiants.

## Installation

Depuis la racine du projet, créez et activez un environnement virtuel, puis installez les dépendances :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Sous macOS ou Linux, utilisez plutôt :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuration

Copiez `.env.example` en `.env` et renseignez les valeurs de votre environnement. Ne publiez jamais ce fichier ni vos clés Azure.

```dotenv
AZURE_OPENAI_ENDPOINT=https://<votre-ressource>.openai.azure.com
AZURE_OPENAI_API_KEY=<votre-cle>
CHAT_DEPLOYMENT=<nom-du-deploiement>

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=<utilisateur-lecture-seule>
MYSQL_PASSWORD=<mot-de-passe>
MYSQL_DATABASE=catalogue

RAG_DOSSIER_PDF=fiches_fournisseurs
AGENT_MAX_DEMANDES=10
AGENT_DUREE_SECONDES=60
```

`CHAT_DEPLOYMENT` doit être le nom du déploiement Azure, pas celui du modèle. Le dossier RAG est résolu depuis le répertoire courant; par défaut, lancez l'application depuis la racine du projet.

## Base de données

L'application attend une base `catalogue` et une table `produits` avec les colonnes `id`, `libelle`, `categorie`, `prix`, `stock` et `fournisseur`. Les scripts fournis dans `sql/` créent la base et l'utilisateur, la table, puis les données d'exemple. Pour les exécuter localement :

```bash
mysql -u root -p < sql/00_mysql_base_et_utilisateur.sql
mysql -u root -p catalogue < sql/01_schema.sql
mysql -u root -p catalogue < sql/02_donnees.sql
```

**Attention :** `01_schema.sql` supprime puis recrée la table `produits`. Ne l'exécutez pas sur une base contenant des données à conserver. Avant d'exécuter `00_mysql_base_et_utilisateur.sql`, remplacez le mot de passe défini en clair par un mot de passe local et reportez-le dans `MYSQL_PASSWORD`.

Les fichiers `sql/` sont actuellement exclus du dépôt par `.gitignore`. Ils ne seront donc pas disponibles après un clone GitHub à moins d'être ajoutés explicitement au dépôt.

## Lancement

Depuis la racine du projet :

```bash
python src/agent.py
```

L'application propose une question d'exemple au premier démarrage. Saisissez une question, appuyez sur Entrée pour continuer la conversation, ou tapez `quitter` pour terminer.

Exemples de questions :

- « Quels produits sont en rupture de stock ? »
- « Quels produits propose NovaTech Distribution ? »
- « Quels sont les délais de livraison de ce fournisseur ? »

## Tests

Les tests unitaires n'ont pas besoin d'une connexion active à MySQL ou Azure OpenAI :

```bash
python -m pytest
```

## Structure du projet

```text
src/
  agent.py                 Interface conversationnelle et garde-fous
  config.py                Configuration de Semantic Kernel
  connexion.py             Client Azure OpenAI
  plugins/
    sql_plugin.py          Outils de consultation du catalogue MySQL
    rag_plugin.py          Recherche dans les PDF fournisseurs
fiches_fournisseurs/       Fiches PDF indexées au démarrage
sql/                       Scripts SQL d'initialisation et données de démonstration
test/                      Tests unitaires pytest
```

Le contenu des PDF est extrait au démarrage de l'agent et indexé en mémoire; les PDF numérisés sans couche texte ne seront pas recherchables sans OCR préalable.