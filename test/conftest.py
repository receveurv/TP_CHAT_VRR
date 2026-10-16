from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv(
    dotenv_path=Path(__file__).resolve().parent.parent / ".env.example",
    override=True,
)
os.environ["MYSQL_PORT"] = "3306"