# C:\gerenciador-eventos\decorators.py
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user

def role_required(*roles):
    """
    Decorator para restringir acesso a rotas com base no papel (role) do usuário.
    Permite especificar múltiplos papéis permitidos, comparando de forma case-insensitive.
    Redireciona para 'main.login' se não autenticado.
    Redireciona para 'main.home' se não tiver o papel necessário.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa estar logado para acessar esta página.', 'warning')
                # APONTANDO PARA O BLUEPRINT 'main'
                return redirect(url_for('main.login'))

            user_role_lower = current_user.role.lower() if current_user.role else ''
            allowed_roles_lower = [r.lower() for r in roles]

            if user_role_lower not in allowed_roles_lower:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                # APONTANDO PARA O BLUEPRINT 'main'
                return redirect(url_for('main.home')) 
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator para exigir que o usuário tenha o papel 'admin'.
    Equivalente a @role_required('admin').
    """
    return role_required('admin')(f)

def project_manager_required(f):
    """
    Decorator para exigir que o usuário tenha o papel 'project manager' ou 'admin'.
    Equivalente a @role_required('admin', 'project manager').
    """
    return role_required('admin', 'project manager')(f)

def permission_required(permission_name):
    """
    Decorator genérico para restringir acesso a rotas com base em uma permissão específica
    do usuário (atributo do objeto current_user, geralmente definido pelo seu Role).
    Redireciona para 'main.login' se não autenticado.
    Redireciona para 'main.home' se não tiver a permissão necessária.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Você precisa estar logado para acessar esta página.', 'info')
                # APONTANDO PARA O BLUEPRINT 'main'
                return redirect(url_for('main.login'))
            if not getattr(current_user, permission_name, False):
                flash('Você não tem permissão para realizar esta ação.', 'danger')
                # APONTANDO PARA O BLUEPRINT 'main'
                return redirect(url_for('main.home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator