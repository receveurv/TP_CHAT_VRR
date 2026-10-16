import json
import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from pypdf import PdfReader
from semantic_kernel.functions import kernel_function

TAILLE_EXTRAIT = 800
CHEVAUCHEMENT = 150
MAX_RESULTATS = 8
# Parametres classiques de BM25
K1 = 1.5
B = 0.75


def _normaliser(texte: str) -> list[str]:
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return [mot for mot in re.findall(r"[a-z0-9]+", sans_accents.lower()) if len(mot) > 1]


def _decouper(texte: str) -> list[str]:
    texte = re.sub(r"\s+", " ", texte).strip()
    if not texte:
        return []
    pas = TAILLE_EXTRAIT - CHEVAUCHEMENT
    return [texte[i:i + TAILLE_EXTRAIT] for i in range(0, max(len(texte) - CHEVAUCHEMENT, 1), pas)]


class RAGPlugin:
    """Recherche documentaire (BM25) dans les PDF du dossier RAG_DOSSIER_PDF."""

    def __init__(self, dossier: str | None = None):
        load_dotenv()
        self.dossier = Path(dossier or os.getenv("RAG_DOSSIER_PDF", "fiches_fournisseurs")).resolve()
        if not self.dossier.is_dir():
            raise FileNotFoundError(f"Dossier PDF introuvable : {self.dossier}")
        self.extraits: list[dict] = []
        self._indexer()

    def _indexer(self) -> None:
        for chemin in sorted(self.dossier.glob("*.pdf")):
            for num_page, page in enumerate(PdfReader(chemin).pages, start=1):
                for texte in _decouper(page.extract_text() or ""):
                    self.extraits.append({
                        "source": chemin.name,
                        "page": num_page,
                        "texte": texte,
                        "termes": Counter(_normaliser(texte)),
                    })
        nb = len(self.extraits)
        self.longueur_moyenne = sum(sum(e["termes"].values()) for e in self.extraits) / nb if nb else 0
        frequences = Counter(terme for e in self.extraits for terme in e["termes"])
        self.idf = {t: math.log(1 + (nb - f + 0.5) / (f + 0.5)) for t, f in frequences.items()}

    def _score(self, termes_requete: list[str], extrait: dict) -> float:
        longueur = sum(extrait["termes"].values())
        score = 0.0
        for terme in termes_requete:
            tf = extrait["termes"].get(terme, 0)
            if tf:
                score += self.idf[terme] * tf * (K1 + 1) / (
                    tf + K1 * (1 - B + B * longueur / self.longueur_moyenne)
                )
        return score

    @kernel_function(
        description="Rechercher des informations dans les documents PDF (fiches fournisseurs). "
        "Retourne les extraits les plus pertinents avec leur fichier source et leur page."
    )
    def rechercher_documents(
        self,
        question: Annotated[str, "Question ou mots-cles a rechercher dans les documents"],
        nb_resultats: Annotated[int, "Nombre d'extraits a retourner (1 a 8)"] = 4,
    ) -> Annotated[str, "Liste JSON d'extraits avec source, page et texte"]:
        termes = _normaliser(question)
        if not termes:
            raise ValueError("La question ne doit pas etre vide.")
        nb_resultats = max(1, min(int(nb_resultats), MAX_RESULTATS))
        resultats = sorted(
            ((self._score(termes, e), e) for e in self.extraits), key=lambda r: r[0], reverse=True
        )
        return json.dumps(
            [
                {"source": e["source"], "page": e["page"], "extrait": e["texte"]}
                for score, e in resultats[:nb_resultats]
                if score > 0
            ],
            ensure_ascii=False,
        )