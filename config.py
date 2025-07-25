import os
import logging
from dotenv import load_dotenv


def carregar_configuracoes():
    """
    Carrega as configurações do ambiente.

    Returns:
        dict: Dicionário com as configurações
    """
    load_dotenv()

    return {
        "smtp_host": os.getenv("smtp_host", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("smtp_port", 587)),
        "smtp_user": os.getenv("smtp_user", ""),
        "smtp_pass": os.getenv("smtp_pass", ""),
        "destinatarios": os.getenv("destinatarios", "").split(","),
        "destinatario_enge": os.getenv("destinatario_enge", ""),
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_key": os.getenv("SUPABASE_KEY")
    }


def configurar_logging():
    """Configura o sistema de logging"""
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        filename='logs/app.log',
        level=logging.WARNING,
        format='%(asctime)s %(levelname)s %(message)s'
    )
