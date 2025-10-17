import re

def analyze_routes_file():
    """Analisa o arquivo routes.py para encontrar todas as duplicatas"""
    try:
        with open('routes.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        functions = {}
        routes = {}
        current_route = None
        
        print("=== ANÁLISE COMPLETA DO ARQUIVO ROUTES.PY ===\n")
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Detecta rotas
            if line_stripped.startswith('@route('):
                route_match = re.search(r"@main\.route\('([^']+)'", line)
                if route_match:
                    current_route = route_match.group(1)
                    if current_route in routes:
                        routes[current_route].append(i)
                    else:
                        routes[current_route] = [i]
            
            # Detecta funções
            elif line_stripped.startswith('def '):
                func_match = re.match(r'def\s+(\w+)\s*\(', line_stripped)
                if func_match:
                    func_name = func_match.group(1)
                    if func_name in functions:
                        functions[func_name].append((i, current_route))
                    else:
                        functions[func_name] = [(i, current_route)]
        
        # Relatório de funções duplicadas
        print("🔍 FUNÇÕES DUPLICADAS:")
        duplicates_found = False
        for func_name, occurrences in functions.items():
            if len(occurrences) > 1:
                duplicates_found = True
                print(f"\n❌ Função '{func_name}':")
                for line_num, route in occurrences:
                    print(f"   - Linha {line_num}: {route or 'sem rota'}")
        
        if not duplicates_found:
            print("   ✅ Nenhuma função duplicada encontrada!")
        
        # Relatório de rotas duplicadas
        print(f"\n🔍 ROTAS DUPLICADAS:")
        route_duplicates_found = False
        for route_path, line_numbers in routes.items():
            if len(line_numbers) > 1:
                route_duplicates_found = True
                print(f"\n❌ Rota '{route_path}':")
                for line_num in line_numbers:
                    print(f"   - Linha {line_num}")
        
        if not route_duplicates_found:
            print("   ✅ Nenhuma rota duplicada encontrada!")
        
        # Busca específica por reject_attachment_art
        print(f"\n🎯 BUSCA ESPECÍFICA POR 'reject_attachment_art':")
        reject_functions = [item for item in functions.items() if 'reject_attachment_art' in item[0]]
        if reject_functions:
            for func_name, occurrences in reject_functions:
                print(f"\n📍 Função '{func_name}':")
                for line_num, route in occurrences:
                    print(f"   - Linha {line_num}: {route or 'sem rota'}")
                    # Mostra o contexto da linha
                    if line_num <= len(lines):
                        print(f"     Código: {lines[line_num-1].strip()}")
        else:
            print("   ✅ Nenhuma função 'reject_attachment_art' encontrada!")
            
    except FileNotFoundError:
        print("❌ Arquivo routes.py não encontrado!")
    except Exception as e:
        print(f"❌ Erro ao analisar arquivo: {e}")

def search_specific_pattern():
    """Busca por padrões específicos que podem causar conflitos"""
    try:
        with open('routes.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n🔎 BUSCA POR PADRÕES ESPECÍFICOS:")
        
        # Busca por reject_attachment_art
        reject_matches = list(re.finditer(r'def\s+reject_attachment_art', content))
        if reject_matches:
            print(f"\n📍 Encontradas {len(reject_matches)} definições de 'reject_attachment_art':")
            for i, match in enumerate(reject_matches, 1):
                line_num = content[:match.start()].count('\n') + 1
                print(f"   {i}. Linha {line_num}")
        
        # Busca por approve_attachment_art (para confirmar se foi removido)
        approve_matches = list(re.finditer(r'def\s+approve_attachment_art', content))
        if approve_matches:
            print(f"\n�� Ainda existem {len(approve_matches)} definições de 'approve_attachment_art':")
            for i, match in enumerate(approve_matches, 1):
                line_num = content[:match.start()].count('\n') + 1
                print(f"   {i}. Linha {line_num}")
        else:
            print(f"\n✅ 'approve_attachment_art' foi removido com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro na busca por padrões: {e}")

if __name__ == "__main__":
    analyze_routes_file()
    search_specific_pattern()