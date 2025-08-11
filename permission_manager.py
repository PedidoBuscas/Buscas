import streamlit as st
from supabase_agent import SupabaseAgent
from typing import List, Dict, Any, Optional


# Definição dos cargos e suas permissões
CARGOS_JURIDICO = {
    'advogado': {
        'permissions': ['ver_proprias_objecoes'],
        'menu_items': ['Minhas Solicitações Jurídicas']
    },
    'funcionario': {
        'permissions': ['solicitar_objecao', 'ver_proprias_objecoes'],
        'menu_items': ['Solicitação para o Jurídico', 'Minhas Solicitações Jurídicas']
    },
    'administrador': {
        'permissions': ['solicitar_objecao', 'ver_proprias_objecoes', 'gerenciar_objecoes', 'ver_todas_objecoes', 'relatorio_custos'],
        'menu_items': ['Solicitação para o Jurídico', 'Minhas Solicitações Jurídicas', 'Relatório de Custos']
    }
}

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
        'permissions': ['solicitar_patente', 'ver_proprias_patentes', 'gerenciar_patentes', 'gerenciar_buscas', 'ver_todas_buscas', 'relatorio_custos'],
        'menu_items': ['Solicitar Busca', 'Minhas Buscas', 'Relatório de Custos', 'Solicitar Serviço de Patente', 'Minhas Patentes']
    }
}

CARGOS_CONSULTOR = {
    'consultor': {
        'permissions': ['solicitar_busca', 'ver_proprias_buscas', 'solicitar_patente', 'ver_proprias_patentes', 'gerenciar_buscas', 'gerenciar_patentes', 'solicitar_objecao', 'ver_proprias_objecoes'],
        'menu_items': ['Solicitar Busca', 'Minhas Buscas', 'Solicitar Serviço de Patente', 'Minhas Patentes', 'Solicitação para o Jurídico', 'Minhas Solicitações Jurídicas']
    },
    'avaliador de marca': {
        'permissions': ['ver_proprias_buscas'],
        'menu_items': ['Minhas Buscas']
    },
    'financeiro': {
        'permissions': ['relatorio_custos'],
        'menu_items': ['Relatório de Custos']
    },
    'admin': {
        'permissions': ['solicitar_busca', 'ver_proprias_buscas', 'gerenciar_buscas', 'ver_todas_buscas', 'solicitar_patente', 'ver_proprias_patentes', 'gerenciar_patentes', 'solicitar_objecao', 'ver_proprias_objecoes', 'gerenciar_objecoes', 'ver_todas_objecoes', 'relatorio_custos'],
        'menu_items': ['Solicitar Busca', 'Minhas Buscas', 'Relatório de Custos', 'Solicitar Serviço de Patente', 'Minhas Patentes', 'Solicitação para o Jurídico', 'Minhas Solicitações Jurídicas']
    }
}


class CargoPermissionManager:
    """
    Gerencia permissões baseadas em cargos do usuário.
    Suporta tanto funcionários (tabela funcionario) quanto consultores (tabela perfil).
    """

    def __init__(self, supabase_agent: SupabaseAgent):
        self.supabase_agent = supabase_agent
        self.cargos_juridico = CARGOS_JURIDICO
        self.cargos_funcionario = CARGOS_FUNCIONARIO
        self.cargos_consultor = CARGOS_CONSULTOR

    def get_user_cargo_info(self, user_id: str) -> Dict[str, Any]:
        """
        Retorna informações completas do cargo do usuário.
        Verifica todas as tabelas e combina permissões quando usuário está em múltiplas tabelas.
        """
        # Verificar em todas as tabelas
        juridico = self.supabase_agent.get_juridico_by_id(user_id)
        funcionario = self.supabase_agent.get_funcionario_by_id(user_id)
        perfil = self.supabase_agent.get_profile(user_id)

        # Determinar tipo principal e permissões combinadas
        tipos_encontrados = []
        is_admin = False
        nome = 'Usuário'
        email = ''

        if juridico:
            tipos_encontrados.append('juridico')
            is_admin = is_admin or juridico.get('is_admin', False)
            nome = juridico.get('name', nome)
            email = juridico.get('email', email)

        if funcionario:
            tipos_encontrados.append('funcionario')
            is_admin = is_admin or funcionario.get('is_admin', False)
            if not nome or nome == 'Usuário':
                nome = funcionario.get('name', nome)
            if not email:
                email = funcionario.get('email', email)

        if perfil:
            tipos_encontrados.append('consultor')
            is_admin = is_admin or perfil.get('is_admin', False)
            if not nome or nome == 'Usuário':
                nome = perfil.get('name', nome)
            if not email:
                email = perfil.get('email', email)

        # Se não encontrou em nenhuma tabela, tratar como consultor básico
        if not tipos_encontrados:
            return {
                'tipo': 'consultor',
                'cargo': 'consultor',
                'is_admin': False,
                'dados': None,
                'nome': 'Usuário',
                'email': '',
                'tipos_multiplos': []
            }

        # Se está em múltiplas tabelas, priorizar funcionario > juridico > consultor
        if 'funcionario' in tipos_encontrados:
            tipo_principal = 'funcionario'
            cargo = funcionario.get('cargo_func', 'funcionario')
            dados = funcionario
        elif 'juridico' in tipos_encontrados:
            tipo_principal = 'juridico'
            cargo = juridico.get('cargo', 'advogado')
            dados = juridico
        else:
            tipo_principal = 'consultor'
            cargo = perfil.get('cargo', 'consultor')
            dados = perfil

        return {
            'tipo': tipo_principal,
            'cargo': cargo,
            'is_admin': is_admin,
            'dados': dados,
            'nome': nome,
            'email': email,
            'tipos_multiplos': tipos_encontrados
        }

    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        Verifica se usuário tem permissão específica.
        Combina permissões de todas as tabelas onde o usuário está presente.

        Args:
            user_id: ID do usuário
            permission: Permissão a ser verificada

        Returns:
            bool: True se tem permissão, False caso contrário
        """
        cargo_info = self.get_user_cargo_info(user_id)
        tipos_multiplos = cargo_info.get(
            'tipos_multiplos', [cargo_info['tipo']])
        is_admin = cargo_info['is_admin']

        # Se é admin (exatamente True), tem acesso total
        if is_admin is True:
            return True

        # Combinar permissões de todas as tabelas onde o usuário está presente
        all_permissions = set()

        for tipo in tipos_multiplos:
            if tipo == 'juridico':
                cargo = cargo_info['cargo']
                permissions = self.cargos_juridico.get(
                    cargo, {}).get('permissions', [])
                all_permissions.update(permissions)
            elif tipo == 'funcionario':
                cargo = cargo_info['cargo']
                permissions = self.cargos_funcionario.get(
                    cargo, {}).get('permissions', [])
                all_permissions.update(permissions)
            elif tipo == 'consultor':
                cargo = cargo_info['cargo']
                permissions = self.cargos_consultor.get(
                    cargo, {}).get('permissions', [])
                all_permissions.update(permissions)

        return '*' in all_permissions or permission in all_permissions

    def get_available_menu_items(self, user_id: str) -> List[str]:
        """
        Retorna itens de menu disponíveis para o usuário.
        Combina permissões de todas as tabelas onde o usuário está presente.

        Args:
            user_id: ID do usuário

        Returns:
            List[str]: Lista de itens de menu disponíveis
        """
        cargo_info = self.get_user_cargo_info(user_id)
        tipos_multiplos = cargo_info.get(
            'tipos_multiplos', [cargo_info['tipo']])

        # Combinar itens de menu de todas as tabelas
        menu_items = set()

        for tipo in tipos_multiplos:
            if tipo == 'juridico':
                cargo = cargo_info['cargo']
                items = self.cargos_juridico.get(
                    cargo, {}).get('menu_items', [])
                menu_items.update(items)
            elif tipo == 'funcionario':
                cargo = cargo_info['cargo']
                items = self.cargos_funcionario.get(
                    cargo, {}).get('menu_items', [])
                menu_items.update(items)
            elif tipo == 'consultor':
                cargo = cargo_info['cargo']
                items = self.cargos_consultor.get(
                    cargo, {}).get('menu_items', [])
                menu_items.update(items)

        # Filtrar "Relatório de Custos" apenas para admins ou cargo financeiro
        if 'Relatório de Custos' in menu_items:
            if not cargo_info['is_admin'] and cargo_info['cargo'] != 'financeiro':
                menu_items.remove('Relatório de Custos')

        # Ordenar itens de menu de forma lógica
        return self._ordenar_menu_items(list(menu_items))

    def _ordenar_menu_items(self, menu_items: List[str]) -> List[str]:
        """
        Ordena os itens de menu de forma lógica, agrupando funcionalidades relacionadas.
        """
        # Definir ordem lógica dos itens
        ordem_logica = [
            'Solicitar Busca',
            'Minhas Buscas',
            'Relatório de Custos',
            'Solicitar Serviço de Patente',
            'Minhas Patentes',
            'Solicitação para o Jurídico',
            'Minhas Solicitações Jurídicas'
        ]

        # Filtrar apenas os itens que existem no menu do usuário
        itens_ordenados = []
        for item in ordem_logica:
            if item in menu_items:
                itens_ordenados.append(item)

        # Adicionar qualquer item que não esteja na ordem lógica (por segurança)
        for item in menu_items:
            if item not in itens_ordenados:
                itens_ordenados.append(item)

        return itens_ordenados

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
            'Relatório de Custos': 'graph-up',
            'Solicitar Serviço de Patente': 'file-earmark-arrow-up',
            'Minhas Patentes': 'file-earmark-text',
            'Solicitação para o Jurídico': 'exclamation-triangle',
            'Minhas Solicitações Jurídicas': 'clipboard-check'
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
            'Minhas Patentes': 'ver_proprias_patentes',
            'Solicitação para o Jurídico': 'solicitar_objecao',
            'Minhas Solicitações Jurídicas': 'ver_proprias_objecoes',
            'Relatório de Custos': 'relatorio_custos'
        }

        required_permission = page_permissions.get(page_name)

        if not required_permission:
            return True  # Se não há permissão definida, permite acesso

        # Para relatório de custos, verificar se é admin ou tem cargo financeiro
        if page_name == "Relatório de Custos":
            cargo_info = self.get_user_cargo_info(user_id)
            # Permitir se é admin ou se tem cargo financeiro
            return cargo_info['is_admin'] is True or cargo_info['cargo'] == 'financeiro'

        return self.has_permission(user_id, required_permission)
