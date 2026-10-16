import json
from decimal import Decimal
from unittest.mock import MagicMock

import mysql.connector
import pytest
from semantic_kernel import Kernel

from src.agent import SQLPlugin


@pytest.fixture
def base_simulee(monkeypatch):
    monkeypatch.setenv("MYSQL_PASSWORD", "test-only")
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchall.return_value = []
    connecter = MagicMock(return_value=connexion)
    monkeypatch.setattr("src.agent.mysql.connector.connect", connecter)
    return SQLPlugin(), connexion, curseur, connecter


@pytest.mark.parametrize(
    "methode,arguments,condition,parametres",
    [
        ("recherche_par_mot_cle", ("cable",), "(libelle LIKE %s ESCAPE '!' OR categorie LIKE %s ESCAPE '!')", ("%cable%", "%cable%")),
        ("recherche_par_mot_cle", ("50%_!",), "(libelle LIKE %s ESCAPE '!' OR categorie LIKE %s ESCAPE '!')", ("%50!%!_!!%", "%50!%!_!!%")),
        ("produits_fournisseur", ("L'entreprise",), "fournisseur = %s", ("L'entreprise",)),
        ("produits_fournisseur", ("' OR 1=1 --",), "fournisseur = %s", ("' OR 1=1 --",)),
        ("rupture_de_stock", (), "stock = %s", (0,)),
        ("fourchette_de_prix", (10, 20), "prix BETWEEN %s AND %s", (10, 20)),
        ("fourchette_de_prix", (0, 0), "prix BETWEEN %s AND %s", (0, 0)),
    ],
)
def test_requetes_parametrees(base_simulee, methode, arguments, condition, parametres):
    plugin, connexion, curseur, _ = base_simulee
    assert json.loads(getattr(plugin, methode)(*arguments)) == []
    curseur.execute.assert_called_once_with(
        "SELECT id, libelle, categorie, prix, stock, fournisseur FROM produits WHERE "
        + condition + " ORDER BY id",
        parametres,
    )
    connexion.cursor.assert_called_once_with(dictionary=True)
    connexion.close.assert_called_once()


@pytest.mark.parametrize(
    "methode,arguments",
    [
        ("recherche_par_mot_cle", ("  ",)),
        ("produits_fournisseur", ("",)),
        ("fourchette_de_prix", (-1, 20)),
        ("fourchette_de_prix", (20, 10)),
        ("fourchette_de_prix", (0, float("inf"))),
        ("fourchette_de_prix", (float("nan"), 20)),
    ],
)
def test_arguments_invalides(base_simulee, methode, arguments):
    plugin, _, _, connecter = base_simulee
    with pytest.raises(ValueError):
        getattr(plugin, methode)(*arguments)
    connecter.assert_not_called()


def test_serialisation_prix_decimal(base_simulee):
    plugin, _, curseur, _ = base_simulee
    curseur.fetchall.return_value = [{"id": 1, "prix": Decimal("12.50")}]
    assert json.loads(plugin.rupture_de_stock()) == [{"id": 1, "prix": "12.50"}]


def test_reessaie_la_connexion_apres_un_echec(base_simulee, monkeypatch):
    plugin, connexion, _, connecter = base_simulee
    connecter.side_effect = [mysql.connector.Error("Erreur temporaire"), connexion]
    attendre = MagicMock()
    monkeypatch.setattr("src.agent.time.sleep", attendre)

    assert json.loads(plugin.rupture_de_stock()) == []

    assert connecter.call_count == 2
    attendre.assert_called_once_with(1)


def test_arrete_apres_trois_retry(base_simulee, monkeypatch):
    plugin, _, _, connecter = base_simulee
    connecter.side_effect = mysql.connector.Error("Erreur persistante")
    attendre = MagicMock()
    monkeypatch.setattr("src.agent.time.sleep", attendre)

    with pytest.raises(mysql.connector.Error, match="Erreur persistante"):
        plugin.rupture_de_stock()

    assert connecter.call_count == 4
    assert attendre.call_count == 3


def test_fermeture_sur_erreur(base_simulee):
    plugin, connexion, curseur, _ = base_simulee
    curseur.execute.side_effect = RuntimeError("Erreur SQL")
    with pytest.raises(RuntimeError, match="Erreur SQL"):
        plugin.rupture_de_stock()
    connexion.close.assert_called_once()


def test_outils_enregistres():
    kernel = Kernel()
    plugin = kernel.add_plugin(SQLPlugin(), plugin_name="catalogue")
    assert set(plugin.functions) == {
        "recherche_par_mot_cle", "produits_fournisseur",
        "rupture_de_stock", "fourchette_de_prix",
    }