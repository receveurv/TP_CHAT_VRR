import json
from pathlib import Path

import pytest

from src.plugins.rag_plugin import RAGPlugin, _decouper, _normaliser

DOSSIER = Path(__file__).resolve().parent.parent / "fiches_fournisseurs"


@pytest.fixture(scope="module")
def plugin():
    return RAGPlugin(str(DOSSIER))


def test_normaliser_retire_accents_et_casse():
    assert _normaliser("Délai de LIVRAISON é") == ["delai", "de", "livraison"]


def test_decouper_texte_long_avec_chevauchement():
    morceaux = _decouper("a" * 2000)
    assert len(morceaux) > 1
    assert all(len(m) <= 800 for m in morceaux)
    assert _decouper("   ") == []


def test_dossier_inexistant():
    with pytest.raises(FileNotFoundError):
        RAGPlugin(str(DOSSIER / "absent"))


def test_dossier_configurable_par_env(monkeypatch):
    monkeypatch.setenv("RAG_DOSSIER_PDF", str(DOSSIER))
    assert RAGPlugin().dossier == DOSSIER


def test_indexe_tous_les_pdf(plugin):
    assert {e["source"] for e in plugin.extraits} == {p.name for p in DOSSIER.glob("*.pdf")}


def test_recherche_retourne_sources_et_pages(plugin):
    resultats = json.loads(plugin.rechercher_documents("NovaTech", 3))
    assert resultats
    assert resultats[0]["source"] == "FRN-001_NovaTech_Distribution.pdf"
    assert all({"source", "page", "extrait"} <= r.keys() for r in resultats)


def test_recherche_sans_correspondance(plugin):
    assert json.loads(plugin.rechercher_documents("zzqxw")) == []


def test_question_vide_refusee(plugin):
    with pytest.raises(ValueError):
        plugin.rechercher_documents("  ")


def test_nb_resultats_borne(plugin):
    assert len(json.loads(plugin.rechercher_documents("fournisseur", 100))) <= 8
