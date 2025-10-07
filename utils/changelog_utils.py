# app/utils/changelog_utils.py

def diff_dicts(old_data, new_data):
    """
    Compara dois dicionários (old_data e new_data) e retorna as diferenças.
    Retorna um dicionário com chaves 'changed', 'added' e 'removed'.
    """
    if old_data is None:
        old_data = {}
    if new_data is None:
        new_data = {}

    changed_fields = {}
    added_fields = {}
    removed_fields = {}

    # Encontrar campos modificados e removidos
    for key, old_value in old_data.items():
        if key in new_data:
            new_value = new_data[key]
            if old_value != new_value:
                changed_fields[key] = {"old": old_value, "new": new_value}
        else:
            removed_fields[key] = old_value

    # Encontrar campos adicionados
    for key, new_value in new_data.items():
        if key not in old_data:
            added_fields[key] = new_value

    return {
        "changed": changed_fields,
        "added": added_fields,
        "removed": removed_fields
    }

# Exemplo de uso (para testar a função):
if __name__ == '__main__':
    old = {
        "title": "Old Title",
        "description": "Old description for testing purposes.",
        "status": "pending",
        "due_date": "2023-01-01",
        "priority": "medium",
        "assigned_to": "UserA"
    }
    new = {
        "title": "New Title",
        "description": "Updated description for testing purposes.",
        "status": "completed",
        "due_date": "2023-01-01", # unchanged
        "priority": "high",
        "new_field": "This was added",
        "assigned_to": "UserB"
    }

    # Testando modificações, adições e remoções
    diff = diff_dicts(old, new)
    print("Diff completo:", diff)
    """
    Saída esperada:
    {
        'changed': {
            'title': {'old': 'Old Title', 'new': 'New Title'},
            'description': {'old': 'Old description for testing purposes.', 'new': 'Updated description for testing purposes.'},
            'status': {'old': 'pending', 'new': 'completed'},
            'priority': {'old': 'medium', 'new': 'high'},
            'assigned_to': {'old': 'UserA', 'new': 'UserB'}
        },
        'added': {
            'new_field': 'This was added'
        },
        'removed': {} # Não há campos removidos neste exemplo
    }
    """

    # Testando apenas adição (old_data vazio)
    diff_add = diff_dicts(None, {"name": "New Item"})
    print("\nDiff apenas adição:", diff_add)
    """
    Saída esperada:
    {
        'changed': {},
        'added': {'name': 'New Item'},
        'removed': {}
    }
    """

    # Testando apenas remoção (new_data vazio)
    diff_remove = diff_dicts({"name": "Old Item"}, None)
    print("\nDiff apenas remoção:", diff_remove)
    """
    Saída esperada:
    {
        'changed': {},
        'added': {},
        'removed': {'name': 'Old Item'}
    }
    """

    # Testando sem mudanças
    diff_no_change = diff_dicts({"name": "Item"}, {"name": "Item"})
    print("\nDiff sem mudanças:", diff_no_change)
    """
    Saída esperada:
    {
        'changed': {},
        'added': {},
        'removed': {}
    }
    """