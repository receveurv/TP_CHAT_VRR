import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from src.agent import SPEC_EXEMPLE, main


@pytest.fixture
def agent_simule(monkeypatch):
    monkeypatch.setitem(sys.modules, "config", SimpleNamespace(creer_kernel=MagicMock()))
    monkeypatch.setattr("src.agent.SQLPlugin", MagicMock())
    agent = MagicMock()
    agent.get_response = AsyncMock()
    monkeypatch.setattr("src.agent.ChatCompletionAgent", MagicMock(return_value=agent))
    return agent


def test_questions_successives_reutilisent_le_fil(agent_simule, monkeypatch, capsys):
    premier_fil = object()
    second_fil = object()
    agent_simule.get_response.side_effect = [
        SimpleNamespace(content="Produit A en rupture.", thread=premier_fil),
        SimpleNamespace(content="Fournisseur B.", thread=second_fil),
        SimpleNamespace(content="12 euros.", thread=second_fil),
    ]
    saisie = MagicMock(side_effect=[
        "Quels produits sont en rupture ?", "Qui les fournit ?", "Quel est leur prix ?", " QUITTER ",
    ])
    monkeypatch.setattr("builtins.input", saisie)

    asyncio.run(main())

    assert agent_simule.get_response.await_args_list == [
        call(messages="Quels produits sont en rupture ?", thread=None),
        call(messages="Qui les fournit ?", thread=premier_fil),
        call(messages="Quel est leur prix ?", thread=second_fil),
    ]
    sortie = capsys.readouterr().out
    assert "Produit A en rupture." in sortie
    assert "Fournisseur B." in sortie
    assert "12 euros." in sortie


def test_entree_vide_utilise_exemple_puis_ignore(agent_simule, monkeypatch):
    agent_simule.get_response.return_value = SimpleNamespace(content="Reponse", thread=object())
    monkeypatch.setattr("builtins.input", MagicMock(side_effect=["", "  ", "quitter"]))

    asyncio.run(main())

    agent_simule.get_response.assert_awaited_once_with(messages=SPEC_EXEMPLE, thread=None)


@pytest.mark.parametrize("fin", ["quitter", EOFError(), KeyboardInterrupt()])
def test_fin_sans_appel_au_modele(agent_simule, monkeypatch, fin):
    monkeypatch.setattr("builtins.input", MagicMock(side_effect=[fin]))

    asyncio.run(main())

    agent_simule.get_response.assert_not_awaited()