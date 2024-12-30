import os

def get_resource_path(resource_type: str, filename: str) -> str:
    """Получает путь к ресурсу"""
    base_path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_path, 'src', 'resources', resource_type, filename) 