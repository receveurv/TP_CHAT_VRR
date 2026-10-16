import json
import math
import os
import time
from typing import Annotated, Any

import mysql.connector
from dotenv import load_dotenv
from semantic_kernel.functions import kernel_function

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1


class SQLPlugin:
    """Consultation MySQL via MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE,
    MYSQL_USER et MYSQL_PASSWORD. Utiliser un compte limite a SELECT.
    """

    def __init__(self):
        load_dotenv()
        self.CONFIG_BD = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.environ["MYSQL_USER"],
            "password": os.environ["MYSQL_PASSWORD"],
            "database": os.getenv("MYSQL_DATABASE", "boutique"),
        }

    _REQUETES = {
        "recherche_par_mot_cle": "SELECT id, libelle, categorie, prix, stock, fournisseur FROM produits WHERE (libelle LIKE %s ESCAPE '!' OR categorie LIKE %s ESCAPE '!') ORDER BY id",
        "produits_fournisseur": "SELECT id, libelle, categorie, prix, stock, fournisseur FROM produits WHERE fournisseur = %s ORDER BY id",
        "rupture_de_stock": "SELECT id, libelle, categorie, prix, stock, fournisseur FROM produits WHERE stock = %s ORDER BY id",
        "fourchette_de_prix": "SELECT id, libelle, categorie, prix, stock, fournisseur FROM produits WHERE prix BETWEEN %s AND %s ORDER BY id",
    }

    def _requeter(self, type_requete: str, parametres: tuple[Any, ...] = ()) -> str:
        for tentative in range(MAX_RETRIES + 1):
            try:
                connexion = mysql.connector.connect(
                    host=self.CONFIG_BD["host"],
                    port=self.CONFIG_BD["port"],
                    database=self.CONFIG_BD["database"],
                    user=self.CONFIG_BD["user"],
                    password=self.CONFIG_BD["password"],
                    connection_timeout=10,
                )
                break
            except mysql.connector.Error:
                if tentative == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY_SECONDS)

        try:
            with connexion.cursor(dictionary=True) as curseur:
                curseur.execute(self._REQUETES[type_requete], parametres)
                return json.dumps(curseur.fetchall(), ensure_ascii=False, default=str)
        finally:
            connexion.close()

    @kernel_function(description="Rechercher un mot-cle dans le libelle ou la categorie des produits.")
    def recherche_par_mot_cle(
        self, mot_cle: Annotated[str, "Mot-cle a rechercher dans le catalogue"]
    ) -> Annotated[str, "Liste JSON des produits correspondants"]:
        if not mot_cle.strip():
            raise ValueError("Le mot-cle ne doit pas etre vide.")
        motif = "%" + mot_cle.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
        return self._requeter("recherche_par_mot_cle", (motif, motif))

    @kernel_function(description="Lister les produits d'un fournisseur par son nom exact.")
    def produits_fournisseur(
        self, fournisseur: Annotated[str, "Nom du fournisseur"]
    ) -> Annotated[str, "Liste JSON des produits du fournisseur"]:
        if not fournisseur.strip():
            raise ValueError("Le fournisseur ne doit pas etre vide.")
        return self._requeter("produits_fournisseur", (fournisseur.strip(),))

    @kernel_function(description="Lister les produits en rupture de stock (stock egal a zero).")
    def rupture_de_stock(self) -> Annotated[str, "Liste JSON des produits en rupture"]:
        return self._requeter("rupture_de_stock", (0,))

    @kernel_function(description="Lister les produits dans une fourchette de prix HT, bornes incluses.")
    def fourchette_de_prix(
        self,
        prix_min: Annotated[float, "Prix minimum HT en euros, inclus"],
        prix_max: Annotated[float, "Prix maximum HT en euros, inclus"],
    ) -> Annotated[str, "Liste JSON des produits dans la fourchette"]:
        if not math.isfinite(prix_min) or not math.isfinite(prix_max) or not 0 <= prix_min <= prix_max:
            raise ValueError("Les prix doivent etre finis et respecter 0 <= prix_min <= prix_max.")
        return self._requeter("fourchette_de_prix", (prix_min, prix_max))