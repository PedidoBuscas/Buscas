#!/usr/bin/env python3
"""
Script de teste para verificar a lógica de permissões
"""

import os
import sys
from permission_manager import CargoPermissionManager
from supabase_agent import SupabaseAgent


def test_permission_logic():
    """Testa a lógica de permissões"""

    # Inicializar agentes
    supabase_agent = SupabaseAgent()
    permission_manager = CargoPermissionManager(supabase_agent)

    print("=== TESTE DE PERMISSÕES ===")

    # Simular diferentes tipos de usuários
    test_cases = [
        {
            'name': 'Consultor Normal',
            'user_id': 'test_consultor_1',
            'expected_cargo': 'consultor',
            'expected_is_admin': False,
            'expected_menu': ['Solicitar Busca', 'Minhas Buscas', 'Solicitar Serviço de Patente', 'Minhas Patentes']
        },
        {
            'name': 'Consultor Admin',
            'user_id': 'test_consultor_admin',
            'expected_cargo': 'consultor',
            'expected_is_admin': True,
            'expected_menu': ['Solicitar Busca', 'Minhas Buscas', 'Solicitar Serviço de Patente', 'Minhas Patentes']
        },
        {
            'name': 'Engenheiro',
            'user_id': 'test_engenheiro',
            'expected_cargo': 'engenheiro',
            'expected_is_admin': False,
            'expected_menu': ['Minhas Patentes']
        },
        {
            'name': 'Funcionário',
            'user_id': 'test_funcionario',
            'expected_cargo': 'funcionario',
            'expected_is_admin': False,
            'expected_menu': ['Solicitar Serviço de Patente', 'Minhas Patentes']
        }
    ]

    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")

        # Simular dados do usuário (mock)
        if 'admin' in test_case['name']:
            # Mock para consultor admin
            cargo_info = {
                'tipo': 'consultor',
                'cargo': 'consultor',
                'is_admin': True,
                'nome': test_case['name'],
                'email': 'admin@test.com'
            }
        elif 'Consultor' in test_case['name']:
            # Mock para consultor normal
            cargo_info = {
                'tipo': 'consultor',
                'cargo': 'consultor',
                'is_admin': False,
                'nome': test_case['name'],
                'email': 'consultor@test.com'
            }
        elif 'Engenheiro' in test_case['name']:
            # Mock para engenheiro
            cargo_info = {
                'tipo': 'funcionario',
                'cargo': 'engenheiro',
                'is_admin': False,
                'nome': test_case['name'],
                'email': 'engenheiro@test.com'
            }
        else:
            # Mock para funcionário
            cargo_info = {
                'tipo': 'funcionario',
                'cargo': 'funcionario',
                'is_admin': False,
                'nome': test_case['name'],
                'email': 'funcionario@test.com'
            }

        # Testar menu items
        menu_items = permission_manager.get_available_menu_items(
            test_case['user_id'])
        print(f"Menu items: {menu_items}")
        print(f"Esperado: {test_case['expected_menu']}")
        print(f"✅ Menu correto: {menu_items == test_case['expected_menu']}")

        # Testar permissões
        permissions_to_test = [
            'solicitar_busca',
            'ver_proprias_buscas',
            'solicitar_patente',
            'ver_proprias_patentes',
            'gerenciar_buscas',
            'gerenciar_patentes'
        ]

        print("Permissões:")
        for perm in permissions_to_test:
            has_perm = permission_manager.has_permission(
                test_case['user_id'], perm)
            print(f"  {perm}: {has_perm}")

        # Testar verificação de página
        pages_to_test = [
            'Solicitar Busca',
            'Minhas Buscas',
            'Solicitar Serviço de Patente',
            'Minhas Patentes'
        ]

        print("Acesso às páginas:")
        for page in pages_to_test:
            can_access = permission_manager.check_page_permission(
                test_case['user_id'], page)
            print(f"  {page}: {can_access}")


if __name__ == "__main__":
    test_permission_logic()
