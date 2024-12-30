import subprocess
from typing import Optional
from .keyboard_layout import KeyboardLayout

class KeyboardEmulator:
    """Класс для эмуляции клавиатуры"""
    
    def __init__(self):
        self.current_language = 'ru'  # По умолчанию русский
        self.keyboard_layout = KeyboardLayout()
        
    def get_system_layout(self) -> Optional[str]:
        """Получение текущей системной раскладки"""
        try:
            # Используем общие системные настройки
            result = subprocess.run(
                ['dconf', 'read', '/org/gnome/desktop/input-sources/mru-sources'],
                capture_output=True,
                text=True
            )
            # Обработка результата...
            
        except Exception as e:
            print(f"Ошибка проверки окна: {e}")
            return True

    def is_text_input_window(self, window_id: int) -> bool:
        """Проверка, является ли окно текстовым редактором"""
        try:
            result = subprocess.run(
                ['xprop', '-id', str(window_id), 'WM_CLASS'],
                capture_output=True,
                text=True
            )
            wm_class = result.stdout.lower()
            
            text_input_classes = ['gedit', 'code', 'terminal', 'firefox', 
                                'chrome', 'libreoffice', 'sublime']
            
            return any(cls in wm_class for cls in text_input_classes)
            
        except Exception as e:
            print(f"Ошибка проверки окна: {e}")
            return True
