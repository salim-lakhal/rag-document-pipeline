# Guide de Test - RAG Pipeline OQTF

Guide complet pour tester le pipeline de traitement de documents.

## Table des Matières

1. [Prérequis](#prérequis)
2. [Installation](#installation)
3. [Configuration Google Drive](#configuration-google-drive)
4. [Tests Unitaires](#tests-unitaires)
5. [Tests d'Intégration](#tests-dintégration)
6. [Test du Pipeline Complet](#test-du-pipeline-complet)
7. [Vérification des Résultats](#vérification-des-résultats)
8. [Dépannage](#dépannage)

---

## Prérequis

### Logiciels Requis

```bash
# Python 3.10 ou supérieur
python3 --version

# Git
git --version

# Pour OCR (optionnel mais recommandé)
tesseract --version
```

### Installation de Tesseract (pour OCR)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
Télécharger depuis: https://github.com/UB-Mannheim/tesseract/wiki

---

## Installation

### Étape 1: Cloner le Projet

```bash
cd /home/salim/Informatique/Perso/OQTF
```

### Étape 2: Créer un Environnement Virtuel

```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate  # Linux/macOS
# OU
.\venv\Scripts\activate   # Windows
```

### Étape 3: Installer les Dépendances

```bash
# Installer toutes les dépendances
pip install -r requirements.txt

# Vérifier l'installation
pip list | grep -E "pdfplumber|beautifulsoup4|google-api"
```

### Étape 4: Vérifier la Structure

```bash
# Afficher la structure du projet
tree -L 2 -I '__pycache__|*.pyc|venv'

# Vérifier que tous les fichiers Python sont présents
find . -name "*.py" -type f | grep -E "(utils|processors|scripts)"
```

---

## Configuration Google Drive

### Étape 1: Créer un Projet Google Cloud

1. Aller sur https://console.cloud.google.com/
2. Créer un nouveau projet : "OQTF-RAG-Pipeline"
3. Activer l'API Google Drive :
   - Menu "APIs & Services" > "Library"
   - Rechercher "Google Drive API"
   - Cliquer sur "Enable"

### Étape 2: Créer des Identifiants OAuth 2.0

1. Menu "APIs & Services" > "Credentials"
2. Cliquer sur "Create Credentials" > "OAuth client ID"
3. Type d'application : "Desktop app"
4. Nom : "OQTF Desktop Client"
5. Télécharger le fichier JSON des credentials

### Étape 3: Obtenir le Refresh Token

```bash
# Créer un script temporaire pour obtenir le token
cat > get_refresh_token.py << 'EOF'
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ['https://www.googleapis.com/auth/drive']

# Remplacer avec vos vraies valeurs
CLIENT_ID = "VOTRE_CLIENT_ID"
CLIENT_SECRET = "VOTRE_CLIENT_SECRET"

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"]
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=8080)

print("\n=== CREDENTIALS ===")
print(f"Access Token: {creds.token}")
print(f"Refresh Token: {creds.refresh_token}")
print(f"\nAjoutez ceci dans votre .env:")
print(f"GOOGLE_DRIVE_CLIENT_ID={CLIENT_ID}")
print(f"GOOGLE_DRIVE_CLIENT_SECRET={CLIENT_SECRET}")
print(f"GOOGLE_DRIVE_REFRESH_TOKEN={creds.refresh_token}")
EOF

# Exécuter le script
python get_refresh_token.py
```

### Étape 4: Configurer le Fichier .env

```bash
# Copier le template
cp .env.example .env

# Éditer avec vos credentials
nano .env
```

Contenu du fichier `.env` :
```env
# Google Drive OAuth Credentials
GOOGLE_DRIVE_CLIENT_ID=votre_client_id_ici
GOOGLE_DRIVE_CLIENT_SECRET=votre_client_secret_ici
GOOGLE_DRIVE_REFRESH_TOKEN=votre_refresh_token_ici

# Google Drive Folder IDs (optionnel pour les tests)
GDRIVE_PDFS_FOLDER_ID=
GDRIVE_HTML_FOLDER_ID=
GDRIVE_JSONL_FOLDER_ID=
GDRIVE_META_FOLDER_ID=

# Configuration locale
METADATA_FILE=/home/salim/Informatique/Perso/OQTF/data/meta/metadata.json
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

---

## Tests Unitaires

### Test 1: Module de Nettoyage de Texte

```bash
# Créer un script de test
cat > test_text_cleaning.py << 'EOF'
#!/usr/bin/env python3
"""Test du module text_cleaning"""

import sys
sys.path.insert(0, '/home/salim/Informatique/Perso/OQTF')

from utils.text_cleaning import (
    clean_text,
    detect_language,
    normalize_whitespace,
    remove_boilerplate,
    standardize_dates
)

def test_normalize_whitespace():
    print("\n=== Test: Normalisation des espaces ===")
    text = "Hello    world\n\n\n\nNext paragraph"
    result = normalize_whitespace(text)
    print(f"Input:  '{text}'")
    print(f"Output: '{result}'")
    assert "    " not in result, "Multiple spaces should be removed"
    print("✓ Test réussi")

def test_detect_language():
    print("\n=== Test: Détection de langue ===")
    text_fr = "Ceci est un texte en français pour tester la détection de langue."
    text_en = "This is an English text to test language detection."

    lang_fr = detect_language(text_fr)
    lang_en = detect_language(text_en)

    print(f"Texte FR: {lang_fr}")
    print(f"Texte EN: {lang_en}")

    assert lang_fr == "fr", f"Expected 'fr', got '{lang_fr}'"
    assert lang_en == "en", f"Expected 'en', got '{lang_en}'"
    print("✓ Test réussi")

def test_standardize_dates():
    print("\n=== Test: Standardisation des dates ===")
    text = "Réunion le 15/03/2024 et le 20 mars 2024"
    result = standardize_dates(text)
    print(f"Input:  '{text}'")
    print(f"Output: '{result}'")
    assert "2024-03-15" in result or "2024-03-20" in result, "Dates should be standardized"
    print("✓ Test réussi")

def test_clean_text():
    print("\n=== Test: Nettoyage complet ===")
    raw_text = """
    Page 1 of 10

    Ceci est le contenu principal.    Avec beaucoup d'espaces.



    Rencontre le 15/03/2024.

    Copyright © 2024 Company
    """

    cleaned = clean_text(raw_text)
    print(f"Longueur originale: {len(raw_text)}")
    print(f"Longueur nettoyée:  {len(cleaned)}")
    print(f"\nRésultat:\n{cleaned}")
    print("✓ Test réussi")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTS DU MODULE TEXT_CLEANING")
    print("=" * 60)

    try:
        test_normalize_whitespace()
        test_detect_language()
        test_standardize_dates()
        test_clean_text()

        print("\n" + "=" * 60)
        print("✓ TOUS LES TESTS RÉUSSIS")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOF

# Exécuter le test
python test_text_cleaning.py
```

### Test 2: Module de Chunking

```bash
# Créer le script de test
cat > test_chunking.py << 'EOF'
#!/usr/bin/env python3
"""Test du module chunking"""

import sys
sys.path.insert(0, '/home/salim/Informatique/Perso/OQTF')

from utils.chunking import chunk_text, create_chunks_with_metadata

def test_basic_chunking():
    print("\n=== Test: Chunking basique ===")

    # Créer un texte de test
    text = " ".join(["mot"] * 1000)  # 1000 mots

    chunks = chunk_text(text, chunk_size=100, overlap=10)

    print(f"Texte: {len(text.split())} mots")
    print(f"Nombre de chunks: {len(chunks)}")
    print(f"Premier chunk: {chunks[0]['word_count']} mots")

    if len(chunks) > 1:
        print(f"Deuxième chunk: {chunks[1]['word_count']} mots")

    assert len(chunks) > 0, "Au moins un chunk devrait être créé"
    print("✓ Test réussi")

def test_chunking_with_metadata():
    print("\n=== Test: Chunking avec métadonnées ===")

    text = "Ceci est un document de test. " * 200

    metadata = {
        "document_id": "test_doc_001",
        "category": "test",
        "jurisdiction": "Paris",
        "authority_score": 4,
        "language": "fr"
    }

    chunks = create_chunks_with_metadata(
        text=text,
        document_metadata=metadata,
        chunk_size=50,
        overlap=5
    )

    print(f"Nombre de chunks: {len(chunks)}")
    print(f"\nPremier chunk:")
    print(f"  - chunk_id: {chunks[0]['chunk_id']}")
    print(f"  - document_id: {chunks[0]['document_id']}")
    print(f"  - category: {chunks[0]['category']}")
    print(f"  - word_count: {chunks[0]['word_count']}")
    print(f"  - has_next: {chunks[0]['has_next']}")

    assert chunks[0]['document_id'] == "test_doc_001", "Metadata should be attached"
    assert chunks[0]['category'] == "test", "Category should be preserved"
    print("✓ Test réussi")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTS DU MODULE CHUNKING")
    print("=" * 60)

    try:
        test_basic_chunking()
        test_chunking_with_metadata()

        print("\n" + "=" * 60)
        print("✓ TOUS LES TESTS RÉUSSIS")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOF

# Exécuter le test
python test_chunking.py
```

### Test 3: Module JSONL Writer

```bash
# Créer le script de test
cat > test_jsonl_writer.py << 'EOF'
#!/usr/bin/env python3
"""Test du module jsonl_writer"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, '/home/salim/Informatique/Perso/OQTF')

from utils.jsonl_writer import write_jsonl, validate_chunk

def test_jsonl_writing():
    print("\n=== Test: Écriture JSONL ===")

    # Créer des chunks de test
    chunks = [
        {
            "chunk_id": "test_001",
            "text": "Premier chunk de test",
            "document_id": "doc_test",
            "category": "test",
            "chunk_size": 3
        },
        {
            "chunk_id": "test_002",
            "text": "Deuxième chunk de test",
            "document_id": "doc_test",
            "category": "test",
            "chunk_size": 3
        }
    ]

    # Créer un fichier temporaire
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        temp_path = f.name

    try:
        # Écrire les chunks
        write_jsonl(chunks, temp_path)
        print(f"✓ Fichier écrit: {temp_path}")

        # Lire et vérifier
        with open(temp_path, 'r') as f:
            lines = f.readlines()

        print(f"✓ Nombre de lignes: {len(lines)}")

        # Vérifier que chaque ligne est du JSON valide
        for i, line in enumerate(lines, 1):
            obj = json.loads(line)
            print(f"✓ Ligne {i}: chunk_id={obj['chunk_id']}")

        assert len(lines) == len(chunks), "Nombre de lignes incorrect"
        print("✓ Test réussi")

    finally:
        # Nettoyer
        Path(temp_path).unlink(missing_ok=True)

def test_validation():
    print("\n=== Test: Validation des chunks ===")

    valid_chunk = {
        "chunk_id": "test_001",
        "text": "Contenu du chunk",
        "document_id": "doc_test"
    }

    invalid_chunk = {
        "chunk_id": "test_002"
        # Manque 'text' et 'document_id'
    }

    is_valid = validate_chunk(valid_chunk)
    print(f"Chunk valide: {is_valid}")
    assert is_valid, "Le chunk valide devrait passer la validation"

    is_invalid = validate_chunk(invalid_chunk)
    print(f"Chunk invalide: {is_invalid}")
    assert not is_invalid, "Le chunk invalide devrait échouer la validation"

    print("✓ Test réussi")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTS DU MODULE JSONL_WRITER")
    print("=" * 60)

    try:
        test_jsonl_writing()
        test_validation()

        print("\n" + "=" * 60)
        print("✓ TOUS LES TESTS RÉUSSIS")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOF

# Exécuter le test
python test_jsonl_writer.py
```

### Test 4: Metadata Manager

```bash
# Créer le script de test
cat > test_metadata_manager.py << 'EOF'
#!/usr/bin/env python3
"""Test du module metadata_manager"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, '/home/salim/Informatique/Perso/OQTF')

from utils.metadata_manager import MetadataManager

def test_metadata_operations():
    print("\n=== Test: Opérations sur les métadonnées ===")

    # Créer un fichier temporaire
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
        # Écrire des métadonnées de test
        test_data = [
            {
                "document_id": "test_doc_001",
                "document_type": "pdf",
                "drive_link": "https://drive.google.com/file/d/test123",
                "source_url": "https://example.com/doc1",
                "category": "test",
                "jurisdiction": "Paris",
                "date": "2025-01-01",
                "authority_score": 4,
                "language": "fr",
                "jsonl_ready": False,
                "embedding_done": False
            },
            {
                "document_id": "test_doc_002",
                "document_type": "html",
                "drive_link": "https://drive.google.com/file/d/test456",
                "source_url": "https://example.com/doc2",
                "category": "test",
                "jurisdiction": "Lyon",
                "date": "2025-01-02",
                "authority_score": 3,
                "language": "fr",
                "jsonl_ready": True,
                "embedding_done": False
            }
        ]
        json.dump(test_data, f, indent=2)

    try:
        # Initialiser le manager
        manager = MetadataManager(temp_path)
        print(f"✓ Manager initialisé avec {len(manager.metadata)} documents")

        # Test: Récupérer les documents en attente
        pending = manager.get_pending_documents()
        print(f"✓ Documents en attente: {len(pending)}")
        assert len(pending) == 1, "Devrait avoir 1 document en attente"

        # Test: Récupérer un document
        doc = manager.get_document("test_doc_001")
        print(f"✓ Document récupéré: {doc['document_id']}")
        assert doc['category'] == "test", "Category incorrecte"

        # Test: Mettre à jour le statut
        manager.update_document_status(
            "test_doc_001",
            jsonl_ready=True,
            chunk_count=25
        )
        print("✓ Statut mis à jour")

        # Test: Sauvegarder
        manager.save(backup=False)
        print("✓ Métadonnées sauvegardées")

        # Test: Statistiques
        stats = manager.get_statistics()
        print(f"\nStatistiques:")
        print(f"  - Total documents: {stats['total_documents']}")
        print(f"  - JSONL ready: {stats['jsonl_ready_count']}")
        print(f"  - En attente: {stats['pending_documents']}")

        print("✓ Test réussi")

    finally:
        # Nettoyer
        Path(temp_path).unlink(missing_ok=True)
        backup_file = Path(temp_path).with_suffix('.json.bak')
        backup_file.unlink(missing_ok=True)

if __name__ == "__main__":
    print("=" * 60)
    print("TESTS DU MODULE METADATA_MANAGER")
    print("=" * 60)

    try:
        test_metadata_operations()

        print("\n" + "=" * 60)
        print("✓ TOUS LES TESTS RÉUSSIS")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOF

# Exécuter le test
python test_metadata_manager.py
```

---

## Tests d'Intégration

### Test 5: Processeur HTML

```bash
# Créer un fichier HTML de test
cat > /tmp/test.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Document de Test</title>
    <script>console.log('script');</script>
    <style>body { color: red; }</style>
</head>
<body>
    <header>En-tête du site</header>
    <nav>Navigation</nav>

    <main>
        <article>
            <h1>Titre Principal</h1>
            <p>Ceci est le contenu principal du document de test.</p>
            <p>Un autre paragraphe avec du contenu pertinent.</p>
        </article>
    </main>

    <footer>Pied de page</footer>
</body>
</html>
EOF

# Tester le processeur HTML
cat > test_html_processor.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/salim/Informatique/Perso/OQTF')

from processors.html_processor import process_html

metadata = {
    "document_id": "test_html",
    "category": "test"
}

result = process_html("/tmp/test.html", metadata)

print("\n=== Résultat du Processeur HTML ===")
print(f"Status: {result['status']}")
print(f"Caractères extraits: {result['metadata']['total_chars']}")
print(f"\nTexte extrait:\n{result['text'][:200]}...")

assert result['status'] == 'success', "Le traitement devrait réussir"
assert len(result['text']) > 0, "Du texte devrait être extrait"
print("\n✓ Test HTML réussi")
EOF

python test_html_processor.py
```

### Test 6: Processeur PDF (avec un PDF de test)

```bash
# Option 1: Télécharger un PDF de test
wget -O /tmp/test.pdf "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

# Option 2: Créer un PDF simple avec reportlab (si installé)
cat > create_test_pdf.py << 'EOF'
#!/usr/bin/env python3
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    c = canvas.Canvas("/tmp/test.pdf", pagesize=letter)
    c.drawString(100, 750, "Ceci est un document PDF de test.")
    c.drawString(100, 730, "Il contient plusieurs lignes de texte.")
    c.drawString(100, 710, "Pour tester l'extraction de texte.")
    c.showPage()
    c.save()
    print("✓ PDF de test créé: /tmp/test.pdf")
except ImportError:
    print("reportlab non installé, utilisez un PDF existant")
EOF

python create_test_pdf.py

# Tester le processeur PDF
cat > test_pdf_processor.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/salim/Informatique/Perso/OQTF')

from processors.pdf_processor import process_pdf

metadata = {
    "document_id": "test_pdf",
    "category": "test"
}

result = process_pdf("/tmp/test.pdf", metadata)

print("\n=== Résultat du Processeur PDF ===")
print(f"Status: {result['status']}")
print(f"Pages: {result['metadata']['page_count']}")
print(f"Caractères: {result['metadata']['total_chars']}")
print(f"Méthode: {result['metadata']['processing_method']}")
print(f"\nTexte extrait:\n{result['text'][:200]}...")

assert result['status'] in ['success', 'success_ocr'], "Le traitement devrait réussir"
print("\n✓ Test PDF réussi")
EOF

python test_pdf_processor.py
```

### Test 7: Processeur URL

```bash
# Tester avec une vraie URL
cat > test_url_processor.py << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/salim/Informatique/Perso/OQTF')

from processors.url_processor import process_url

metadata = {
    "document_id": "test_url",
    "category": "test"
}

# Tester avec Wikipedia (généralement stable)
url = "https://fr.wikipedia.org/wiki/Python_(langage)"

print(f"\nTest de l'URL: {url}")
result = process_url(url, metadata)

print("\n=== Résultat du Processeur URL ===")
print(f"Status: {result['status']}")
print(f"Domaine: {result['metadata']['domain']}")
print(f"Caractères: {result['metadata']['total_chars']}")
print(f"\nPremières 200 caractères:\n{result['text'][:200]}...")

assert result['status'] == 'success', "Le traitement devrait réussir"
assert len(result['text']) > 100, "Texte extrait trop court"
print("\n✓ Test URL réussi")
EOF

python test_url_processor.py
```

---

## Test du Pipeline Complet

### Étape 1: Préparer les Données de Test

```bash
# Créer un fichier metadata de test
cat > /home/salim/Informatique/Perso/OQTF/data/meta/metadata_test.json << 'EOF'
[
  {
    "document_id": "test_wikipedia_python",
    "document_type": "url",
    "source_url": "https://fr.wikipedia.org/wiki/Python_(langage)",
    "drive_link": "",
    "category": "test",
    "sub_category": "documentation",
    "jurisdiction": "International",
    "date": "2025-12-12",
    "authority_score": 4,
    "language": "fr",
    "jsonl_ready": false,
    "embedding_done": false
  }
]
EOF
```

### Étape 2: Tester le Pipeline (Mode Dry-Run)

```bash
# Créer un script de test du pipeline
cat > test_pipeline_dry_run.py << 'EOF'
#!/usr/bin/env python3
"""Test du pipeline en mode dry-run (sans Google Drive)"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, '/home/salim/Informatique/Perso/OQTF')

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("\n" + "="*80)
print("TEST DU PIPELINE (DRY-RUN)")
print("="*80 + "\n")

# Test 1: Vérifier les imports
print("1. Vérification des imports...")
try:
    from utils.text_cleaning import clean_text
    from utils.chunking import create_chunks_with_metadata
    from utils.jsonl_writer import write_jsonl
    from utils.metadata_manager import MetadataManager
    from processors.html_processor import process_html
    from processors.pdf_processor import process_pdf
    from processors.url_processor import process_url
    print("   ✓ Tous les modules importés avec succès")
except ImportError as e:
    print(f"   ✗ Erreur d'import: {e}")
    sys.exit(1)

# Test 2: Charger les métadonnées
print("\n2. Chargement des métadonnées de test...")
try:
    manager = MetadataManager("/home/salim/Informatique/Perso/OQTF/data/meta/metadata_test.json")
    docs = manager.get_all_documents()
    print(f"   ✓ {len(docs)} document(s) chargé(s)")

    for doc in docs:
        print(f"     - {doc['document_id']} ({doc['document_type']})")
except Exception as e:
    print(f"   ✗ Erreur: {e}")
    sys.exit(1)

# Test 3: Traiter un document URL (sans caching Drive)
print("\n3. Traitement d'un document URL...")
try:
    doc = docs[0]
    print(f"   Document: {doc['document_id']}")
    print(f"   URL: {doc['source_url']}")

    # Extraire le contenu
    result = process_url(doc['source_url'], doc)
    print(f"   ✓ Texte extrait: {result['metadata']['total_chars']} caractères")

    # Nettoyer le texte
    cleaned = clean_text(result['text'])
    print(f"   ✓ Texte nettoyé: {len(cleaned)} caractères")

    # Créer les chunks
    chunks = create_chunks_with_metadata(
        text=cleaned,
        document_metadata=doc,
        chunk_size=500,
        overlap=50
    )
    print(f"   ✓ {len(chunks)} chunks créés")

    # Écrire le JSONL
    output_path = f"/home/salim/Informatique/Perso/OQTF/data/jsonl/{doc['document_id']}.jsonl"
    write_jsonl(chunks, output_path)
    print(f"   ✓ JSONL écrit: {output_path}")

    # Vérifier le fichier
    jsonl_file = Path(output_path)
    if jsonl_file.exists():
        size = jsonl_file.stat().st_size
        print(f"   ✓ Fichier créé: {size} bytes")

except Exception as e:
    print(f"   ✗ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("✓ TEST DU PIPELINE RÉUSSI")
print("="*80 + "\n")
EOF

# Exécuter le test
python test_pipeline_dry_run.py
```

### Étape 3: Vérifier les Résultats

```bash
# Vérifier le fichier JSONL généré
echo "=== Vérification du JSONL généré ==="
if [ -f "/home/salim/Informatique/Perso/OQTF/data/jsonl/test_wikipedia_python.jsonl" ]; then
    echo "✓ Fichier trouvé"

    # Compter les lignes
    lines=$(wc -l < "/home/salim/Informatique/Perso/OQTF/data/jsonl/test_wikipedia_python.jsonl")
    echo "✓ Nombre de chunks: $lines"

    # Afficher le premier chunk
    echo -e "\n=== Premier chunk ==="
    head -n 1 "/home/salim/Informatique/Perso/OQTF/data/jsonl/test_wikipedia_python.jsonl" | python3 -m json.tool | head -n 20

    # Vérifier la validité JSON de chaque ligne
    echo -e "\n=== Validation JSON ==="
    while IFS= read -r line; do
        echo "$line" | python3 -m json.tool > /dev/null && echo "✓ Ligne valide" || echo "✗ Ligne invalide"
    done < "/home/salim/Informatique/Perso/OQTF/data/jsonl/test_wikipedia_python.jsonl" | head -n 5
else
    echo "✗ Fichier non trouvé"
fi
```

---

## Vérification des Résultats

### Script de Validation Complet

```bash
cat > validate_results.py << 'EOF'
#!/usr/bin/env python3
"""Script de validation des résultats du pipeline"""

import json
import sys
from pathlib import Path

def validate_jsonl_file(filepath):
    """Valide un fichier JSONL"""
    print(f"\n=== Validation de {filepath} ===")

    if not Path(filepath).exists():
        print(f"✗ Fichier non trouvé: {filepath}")
        return False

    required_fields = {
        'chunk_id', 'text', 'document_id', 'category', 'jurisdiction',
        'source_url', 'language', 'authority_score', 'chunk_size'
    }

    chunks = []
    with open(filepath, 'r') as f:
        for i, line in enumerate(f, 1):
            try:
                chunk = json.loads(line)
                chunks.append(chunk)

                # Vérifier les champs requis
                missing = required_fields - set(chunk.keys())
                if missing:
                    print(f"✗ Ligne {i}: champs manquants: {missing}")
                    return False

                # Vérifier les types
                if not isinstance(chunk['chunk_size'], int):
                    print(f"✗ Ligne {i}: chunk_size doit être un entier")
                    return False

                if not isinstance(chunk['text'], str) or len(chunk['text']) == 0:
                    print(f"✗ Ligne {i}: text doit être une chaîne non vide")
                    return False

            except json.JSONDecodeError as e:
                print(f"✗ Ligne {i}: JSON invalide: {e}")
                return False

    print(f"✓ {len(chunks)} chunks valides")
    print(f"✓ Taille moyenne des chunks: {sum(c['chunk_size'] for c in chunks) / len(chunks):.0f} mots")
    print(f"✓ Langue(s): {set(c['language'] for c in chunks)}")
    print(f"✓ Catégorie(s): {set(c['category'] for c in chunks)}")

    return True

def validate_all_jsonl():
    """Valide tous les fichiers JSONL"""
    jsonl_dir = Path("/home/salim/Informatique/Perso/OQTF/data/jsonl")

    print("="*80)
    print("VALIDATION DES FICHIERS JSONL")
    print("="*80)

    if not jsonl_dir.exists():
        print(f"✗ Répertoire non trouvé: {jsonl_dir}")
        return False

    jsonl_files = list(jsonl_dir.glob("*.jsonl"))

    if not jsonl_files:
        print(f"✗ Aucun fichier JSONL trouvé dans {jsonl_dir}")
        return False

    print(f"\nFichiers trouvés: {len(jsonl_files)}")

    all_valid = True
    for jsonl_file in jsonl_files:
        if not validate_jsonl_file(jsonl_file):
            all_valid = False

    print("\n" + "="*80)
    if all_valid:
        print("✓ TOUS LES FICHIERS SONT VALIDES")
    else:
        print("✗ CERTAINS FICHIERS SONT INVALIDES")
    print("="*80)

    return all_valid

if __name__ == "__main__":
    success = validate_all_jsonl()
    sys.exit(0 if success else 1)
EOF

python validate_results.py
```

---

## Dépannage

### Problème 1: Erreur d'Import

```bash
# Vérifier que tous les modules sont installés
pip list | grep -E "pdfplumber|beautifulsoup4|google|langdetect"

# Réinstaller si nécessaire
pip install --upgrade -r requirements.txt
```

### Problème 2: Erreur Google Drive

```bash
# Vérifier les credentials
python3 << EOF
import os
from dotenv import load_dotenv

load_dotenv()

print("GOOGLE_DRIVE_CLIENT_ID:", "✓" if os.getenv('GOOGLE_DRIVE_CLIENT_ID') else "✗ Manquant")
print("GOOGLE_DRIVE_CLIENT_SECRET:", "✓" if os.getenv('GOOGLE_DRIVE_CLIENT_SECRET') else "✗ Manquant")
print("GOOGLE_DRIVE_REFRESH_TOKEN:", "✓" if os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN') else "✗ Manquant")
EOF
```

### Problème 3: OCR ne Fonctionne Pas

```bash
# Vérifier Tesseract
tesseract --version

# Installer si manquant
sudo apt-get install tesseract-ocr tesseract-ocr-fra
```

### Problème 4: Erreurs de Détection de Langue

```bash
# Réinstaller langdetect
pip uninstall langdetect -y
pip install langdetect
```

### Logs de Débogage

```bash
# Activer les logs détaillés
export PYTHONPATH=/home/salim/Informatique/Perso/OQTF
export LOG_LEVEL=DEBUG

# Exécuter avec logs verbeux
python -u test_pipeline_dry_run.py 2>&1 | tee pipeline_debug.log
```

---

## Checklist Finale

Avant de passer en production:

- [ ] ✓ Tous les tests unitaires passent
- [ ] ✓ Les processeurs PDF/HTML/URL fonctionnent
- [ ] ✓ Le chunking produit les bons résultats
- [ ] ✓ Les fichiers JSONL sont valides
- [ ] ✓ Les métadonnées sont correctement attachées
- [ ] ✓ Google Drive est configuré (si nécessaire)
- [ ] ✓ Les logs sont propres (pas d'erreurs)
- [ ] ✓ La validation des résultats passe

---

## Prochaines Étapes

Une fois tous les tests réussis:

1. **Traiter vos vrais documents**:
   ```bash
   # Mettre à jour metadata.json avec vos documents
   # Exécuter le pipeline complet
   python scripts/pipeline_orchestrator.py
   ```

2. **Vérifier les résultats**:
   ```bash
   python validate_results.py
   ```

3. **Passer à l'étape suivante**: Génération d'embeddings et intégration avec Vector DB

---

**Bonne chance avec vos tests! 🚀**
