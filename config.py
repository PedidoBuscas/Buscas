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


USUARIOS_ADMIN = [
    "admin@agpmarcas.com",
    "buscas@agpmarcas.com"  # Exemplo de novo admin
]


def verificar_admin(user):
    """
    Verifica se o usuário é admin.

    Args:
        user: Objeto do usuário

    Returns:
        bool: True se for admin
    """
    email = None
    if hasattr(user, 'email'):
        email = user.email
    elif isinstance(user, dict):
        email = user.get('email')
    return email in USUARIOS_ADMIN
