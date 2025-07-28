import streamlit as st
from supabase_agent import SupabaseAgent
from typing import List, Dict, Any, Optional


# Definição dos cargos e suas permissões
CARGOS_FUNCIONARIO = {
    'funcionario': {
        'permissions': ['solicitar_patente', 'ver_proprias_patentes'],
        'menu_items': ['Solicitar Serviço de Patente', 'Minhas Patentes']
    },
    'engenheiro': {
        'permissions': ['ver_proprias_patentes', 'gerenciar_patentes'],
        'menu_items': ['Minhas Patentes']
    },
    'administrador': {
        'permissions': ['solicitar_patente', 'ver_proprias_patentes', 'gerenciar_patentes', 'gerenciar_buscas', 'ver_todas_buscas'],
        'menu_items': ['Solicitar Busca', 'Minhas Buscas', 'Solicitar Serviço de Patente', 'Minhas Patentes']
    }
}

CARGOS_CONSULTOR = {
    'consultor': {
        'permissions': ['solicitar_busca', 'ver_proprias_buscas', 'solicitar_patente', 'ver_proprias_patentes', 'gerenciar_buscas', 'gerenciar_patentes'],
        'menu_items': ['Solicitar Busca', 'Minhas Buscas', 'Solicitar Serviço de Patente', 'Minhas Patentes']
    },
    'avaliador de marca': {
        'permissions': ['ver_proprias_buscas'],
        'menu_items': ['Minhas Buscas']
    },
    'admin': {
        'permissions': ['solicitar_busca', 'ver_proprias_buscas', 'gerenciar_buscas', 'ver_todas_buscas', 'solicitar_patente', 'ver_proprias_patentes', 'gerenciar_patentes'],
        'menu_items': ['Solicitar Busca', 'Minhas Buscas', 'Solicitar Serviço de Patente', 'Minhas Patentes']
    }
}


class CargoPermissionManager:
    """
    Gerencia permissões baseadas em cargos do usuário.
    Suporta tanto funcionários (tabela funcionario) quanto consultores (tabela perfil).
    """

    def __init__(self, supabase_agent: SupabaseAgent):
        self.supabase_agent = supabase_agent
        self.cargos_funcionario = CARGOS_FUNCIONARIO
        self.cargos_consultor = CARGOS_CONSULTOR

    def get_user_cargo_info(self, user_id: str) -> Dict[str, Any]:
        """
        Retorna informações completas do cargo do usuário.
        Verifica primeiro na tabela funcionario, depois na tabela perfil.
        """
        # Primeiro verificar se é funcionário
        funcionario = self.supabase_agent.get_funcionario_by_id(user_id)
        if funcionario:
            cargo_func = funcionario.get('cargo_func', 'funcionario')
            is_admin = funcionario.get('is_admin', False)

            return {
                'tipo': 'funcionario',
                'cargo': cargo_func,
                'is_admin': is_admin,
                'dados': funcionario,
                'nome': funcionario.get('name', ''),
                'email': funcionario.get('email', '')
            }

        # Se não é funcionário, verificar se é consultor na tabela perfil
        perfil = self.supabase_agent.get_profile(user_id)
        if perfil:
            is_admin = perfil.get('is_admin', False)
            # Usar o cargo real da tabela perfil
            cargo = perfil.get('cargo', 'consultor')

            return {
                'tipo': 'consultor',
                'cargo': cargo,
                'is_admin': is_admin,
                'dados': perfil,
                'nome': perfil.get('name', ''),
                'email': perfil.get('email', '')
            }

        # Se não encontrou em nenhuma tabela, tratar como consultor básico
        return {
            'tipo': 'consultor',
            'cargo': 'consultor',
            'is_admin': False,
            'dados': None,
            'nome': 'Usuário',
            'email': ''
        }

    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        Verifica se usuário tem permissão específica.

        Args:
            user_id: ID do usuário
            permission: Permissão a ser verificada

        Returns:
            bool: True se tem permissão, False caso contrário
        """
        cargo_info = self.get_user_cargo_info(user_id)
        tipo = cargo_info['tipo']
        cargo = cargo_info['cargo']
        is_admin = cargo_info['is_admin']

        # Se é admin (exatamente True), tem acesso total
        if is_admin is True:
            return True

        if tipo == 'funcionario':
            cargo_permissions = self.cargos_funcionario.get(
                cargo, {}).get('permissions', [])
        else:
            cargo_permissions = self.cargos_consultor.get(
                cargo, {}).get('permissions', [])

        return '*' in cargo_permissions or permission in cargo_permissions

    def get_available_menu_items(self, user_id: str) -> List[str]:
        """
        Retorna itens de menu disponíveis para o usuário.

        Args:
            user_id: ID do usuário

        Returns:
            List[str]: Lista de itens de menu disponíveis
        """
        cargo_info = self.get_user_cargo_info(user_id)
        tipo = cargo_info['tipo']
        cargo = cargo_info['cargo']

        # Menu baseado apenas no cargo, não no is_admin
        if tipo == 'funcionario':
            return self.cargos_funcionario.get(cargo, {}).get('menu_items', [])
        else:
            return self.cargos_consultor.get(cargo, {}).get('menu_items', [])

    def get_user_display_info(self, user_id: str) -> Dict[str, Any]:
        """
        Retorna informações para exibição do usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Dict: Informações para exibição
        """
        cargo_info = self.get_user_cargo_info(user_id)
        tipo = cargo_info['tipo']
        cargo = cargo_info['cargo']

        return {
            'nome': cargo_info['nome'],
            'email': cargo_info['email'],
            'cargo': cargo,
            'tipo': tipo,
            'is_admin': cargo_info['is_admin']
        }

    def get_icons_for_menu(self, menu_items: List[str]) -> List[str]:
        """
        Retorna ícones correspondentes aos itens de menu.

        Args:
            menu_items: Lista de itens de menu

        Returns:
            List[str]: Lista de ícones
        """
        icon_mapping = {
            'Solicitar Busca': 'search',
            'Minhas Buscas': 'list-task',
            'Solicitar Serviço de Patente': 'file-earmark-arrow-up',
            'Minhas Patentes': 'file-earmark-text'
        }

        return [icon_mapping.get(item, 'question') for item in menu_items]

    def check_page_permission(self, user_id: str, page_name: str) -> bool:
        """
        Verifica se usuário tem permissão para acessar uma página específica.

        Args:
            user_id: ID do usuário
            page_name: Nome da página

        Returns:
            bool: True se tem permissão, False caso contrário
        """
        page_permissions = {
            'Solicitar Busca': 'solicitar_busca',
            'Minhas Buscas': 'ver_proprias_buscas',
            'Solicitar Serviço de Patente': 'solicitar_patente',
            'Minhas Patentes': 'ver_proprias_patentes'
        }

        required_permission = page_permissions.get(page_name)
        if not required_permission:
            return True  # Se não há permissão definida, permite acesso

        return self.has_permission(user_id, required_permission)
