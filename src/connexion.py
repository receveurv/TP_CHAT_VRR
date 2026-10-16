import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

DEPLOIEMENT = os.environ["CHAT_DEPLOYMENT"]

client = AsyncOpenAI(
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/openai/v1/",
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    timeout=30,      # on n'attend pas plus de 30 secondes une réponse
    max_retries=3,   # en cas d'erreur 429 (quota) ou 5xx, 3 nouvelles tentatives automatiques
)