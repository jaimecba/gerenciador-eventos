from functools import wraps
from flask import flash, redirect, url_for, abort # 'abort' é mantido, mas não usado diretamente no erro de permissão
from flask_login import current_user

def role_required(*roles):
    """
    Decorator para restringir acesso a rotas com base no papel (role) do usuário.
    Permite especificar múltiplos papéis permitidos, comparando de forma case-insensitive.
    Exemplo de uso:
    @role_required('admin')
    @role_required('admin', 'project manager', 'editor')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa estar logado para acessar esta página.', 'warning')
                # Assumindo que a rota de login está na blueprint 'main'
                return redirect(url_for('main.login'))
            
            # Converte o papel do usuário logado para minúsculas para comparação
            # e os papéis passados para o decorador também.
            # Isso garante que 'admin' == 'Admin' == 'ADMIN' para a verificação.
            user_role_lower = current_user.role.lower()
            allowed_roles_lower = [r.lower() for r in roles]

            if user_role_lower not in allowed_roles_lower:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                # <--- ALTERADO AQUI: Redireciona para a home em vez de abortar com 403
                return redirect(url_for('main.home')) 
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator para exigir que o usuário tenha o papel 'admin'.
    Equivalente a @role_required('admin').
    """
    # Garante que 'admin' seja passado em minúsculas para o role_required
    return role_required('admin')(f)

def project_manager_required(f):
    """
    Decorator para exigir que o usuário tenha o papel 'project manager' ou 'admin'.
    Equivalente a @role_required('admin', 'project manager').
    """
    # Garante que os papéis sejam passados em minúsculas para o role_required
    # Lembre-se que o nome 'Project Manager' deve corresponder ao que está na sua tabela Role
    return role_required('admin', 'project manager')(f)