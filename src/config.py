# config.py
# Crée le "Kernel" de Semantic Kernel, connecté à notre déploiement Azure OpenAI.
# Tous les scripts du projet l'importent : from config import creer_kernel
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from connexion import DEPLOIEMENT, client

load_dotenv()

def creer_kernel():
    # Le "service" = le LLM que le Kernel va utiliser
    service = OpenAIChatCompletion(
        ai_model_id=DEPLOIEMENT,  # le NOM DU DÉPLOIEMENT
        async_client=client,
    )

    # Le Kernel = le chef d'orchestre : il connaît le LLM et les plugins
    kernel = Kernel()
    kernel.add_service(service)
    return kernel
