from src.input.keyboard_layout import KeyboardLayout
import subprocess
import os
import time
import json

def print_environment_info(prefix=""):
    """Вывод информации об окружении"""
    print(f"\n=== {prefix} Информация об окружении ===")
    
    # Важные переменные окружения
    important_vars = [
        'DBUS_SESSION_BUS_ADDRESS',
        'XDG_RUNTIME_DIR',
        'DISPLAY',
        'GSETTINGS_BACKEND',
        'G_MESSAGES_DEBUG',
        'DCONF_PROFILE',
        'USER',
        'HOME',
        'GDK_BACKEND',
        'XDG_SESSION_TYPE'
    ]
    
    env_info = {var: os.environ.get(var, 'NOT SET') for var in important_vars}
    print(json.dumps(env_info, indent=2))
    
    # Проверка процессов
    print("\nАктивные процессы:")
    processes = [
        'dconf-service',
        'gnome-shell',
        'pulseaudio'
    ]
    
    for proc in processes:
        result = subprocess.run(['pgrep', '-l', proc], capture_output=True, text=True)
        print(f"{proc}: {'запущен' if result.stdout else 'не запущен'}")
        if result.stdout:
            print(f"  {result.stdout.strip()}")

def get_layout_from_terminal():
    """Получение раскладки через терминал пользователя"""
    try:
        print("\n=== Раскладка из терминала ===")
        print_environment_info("Терминал")
        
        cmd = "gsettings get org.gnome.desktop.input-sources mru-sources"
        result = subprocess.run(['sudo', '-u', os.environ.get('USER', ''), 'bash', '-c', cmd],
                              capture_output=True, text=True)
        
        print(f"\nКоманда: {cmd}")
        print(f"Результат: {result.stdout.strip()}")
        print(f"Ошибки: {result.stderr if result.stderr else 'нет'}")
        return result.stdout.strip()
    except Exception as e:
        print(f"Ошибка получения раскладки из терминала: {e}")
        return None

def get_layout_from_app():
    """Получение раскладки через приложение"""
    try:
        print("\n=== Раскладка из приложения ===")
        print_environment_info("Приложение")
        
        env = os.environ.copy()
        env['G_DEBUG'] = 'fatal-warnings'
        env['G_MESSAGES_DEBUG'] = ''
        
        cmd = ['gsettings', 'get', 'org.gnome.desktop.input-sources', 'mru-sources']
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        print(f"\nКоманда: {' '.join(cmd)}")
        print(f"Результат: {result.stdout.strip()}")
        print(f"Ошибки: {result.stderr if result.stderr else 'нет'}")
        
        # Дополнительная проверка через dconf
        print("\nПроверка через dconf:")
        dconf_cmd = ['dconf', 'read', '/org/gnome/desktop/input-sources/mru-sources']
        dconf_result = subprocess.run(dconf_cmd, capture_output=True, text=True, env=env)
        print(f"Команда: {' '.join(dconf_cmd)}")
        print(f"Результат: {dconf_result.stdout.strip()}")
        print(f"Ошибки: {dconf_result.stderr if dconf_result.stderr else 'нет'}")
        
        return result.stdout.strip()
    except Exception as e:
        print(f"Ошибка получения раскладки из приложения: {e}")
        return None

def main():
    print("\n=== Тест определения раскладки ===")
    print("\nТекущий PID:", os.getpid())
    print("Текущий пользователь:", os.environ.get('USER'))
    
    terminal_layout = get_layout_from_terminal()
    time.sleep(1)
    app_layout = get_layout_from_app()
    
    print("\n=== Сравнение результатов ===")
    print(f"Терминал: {terminal_layout}")
    print(f"Приложение: {app_layout}")
    print(f"Совпадают: {'Да' if terminal_layout == app_layout else 'Нет'}")
    
    print("\n=== Проверка через KeyboardLayout ===")
    layout = KeyboardLayout()
    current = layout.get_current_layout()
    print(f"Итоговая раскладка: {current}")

if __name__ == "__main__":
    main() 