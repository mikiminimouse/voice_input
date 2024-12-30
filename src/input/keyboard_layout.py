import subprocess
import ast
import os
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import threading
import time

class KeyboardLayout:
    """Класс для работы с раскладкой клавиатуры"""
    
    def __init__(self):
        print("\n=== Инициализация определения раскладки ===")
        self.current_layout = None
        self.layout_callbacks = []
        
        # Получаем начальную раскладку
        self.current_layout = self.get_current_layout()
        print(f"Начальная раскладка: {self.current_layout}")
        print("=========================================")
        
    def _get_session_environment(self):
        try:
            # Получаем переменные окружения текущей сессии
            session_bus = self.bus.get_object('org.gnome.SessionManager',
                                            '/org/gnome/SessionManager')
            return session_bus.GetEnvironment(
                dbus_interface='org.gnome.SessionManager'
            )
        except Exception as e:
            print(f"Ошибка получения переменных окружения: {e}")
            return {}

    def get_current_layout(self):
        """Получение текущей раскладки клавиатуры"""
        print("\n=== Определение текущей раскладки ===")
        try:
            # Получаем через gsettings
            print("1. Выполняем команду: gsettings get org.gnome.desktop.input-sources mru-sources")
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.input-sources', 'mru-sources'],
                capture_output=True,
                text=True
            )
            print(f"2. Получены сырые данные: '{result.stdout.strip()}'")
            
            print("3. Парсинг данных...")
            if result.stdout.strip():
                layouts = ast.literal_eval(result.stdout.strip())
                print(f"3.1. Преобразованные данные: {layouts}")
                if layouts:
                    current_source = layouts[0]
                    print(f"3.2. Текущий источник: {current_source}")
                    layout_code = current_source[1]
                    print(f"3.3. Код раскладки: {layout_code}")
                    layout = 'en' if layout_code == 'us' else layout_code
                    print(f"4. Итоговая раскладка: {layout}")
                    return layout
            
            print("! Не удалось получить текущую раскладку")
            return 'en'
            
        except Exception as e:
            print(f"! Критическая ошибка получения раскладки: {e}")
            return 'en'

    def compare_dconf_environments(self):
        """Сравнение окружения терминала и приложения"""
        print("\n=== Сравнение окружений ===")
        
        # 1. Получаем вывод команды из терминала
        print("1. Проверка команды в терминале:")
        terminal_cmd = "env | grep -E 'DBUS|XDG|DISPLAY|DCONF|USER|HOME' && echo '---' && /usr/bin/dconf read /org/gnome/desktop/input-sources/mru-sources"
        terminal = subprocess.run(['bash', '-c', terminal_cmd], 
                                capture_output=True, text=True)
        
        print("Окружение и результат терминала:")
        print(terminal.stdout)
        if terminal.stderr:
            print("Ошибки терминала:", terminal.stderr)
        
        # 2. Окружение приложения
        print("\n2. Окружение приложения:")
        app_env = {k:v for k,v in os.environ.items() 
                  if any(x in k for x in ['DBUS', 'XDG', 'DISPLAY', 'DCONF', 'USER', 'HOME'])}
        for key, value in app_env.items():
            print(f"{key}={value}")
        
        # 3. Пробуем без DCONF_PROFILE
        print("\n3. Тест команды без DCONF_PROFILE:")
        env = os.environ.copy()
        if 'DCONF_PROFILE' in env:
            del env['DCONF_PROFILE']
        
        result = subprocess.run(['/usr/bin/dconf', 'read', 
                               '/org/gnome/desktop/input-sources/mru-sources'],
                              env=env, capture_output=True, text=True)
        print("Результат:", result.stdout.strip())
        if result.stderr:
            print("Ошибки:", result.stderr)
        
        # 4. Пробуем с правами текущего пользователя
        print("\n4. Тест с sudo -u:")
        user = os.environ.get('USER', '')
        if user:
            cmd = f"sudo -u {user} /usr/bin/dconf read /org/gnome/desktop/input-sources/mru-sources"
            sudo_result = subprocess.run(['bash', '-c', cmd], 
                                       capture_output=True, text=True)
            print("Результат:", sudo_result.stdout.strip())
            if sudo_result.stderr:
                print("Ошибки:", sudo_result.stderr) 

    def start_layout_monitoring(self):
        """Запуск мониторинга изменений раскладки через dconf watch"""
        print("\n=== Запуск мониторинга раскладки ===")
        try:
            # Создаем процесс для мониторинга dconf
            cmd = ['dconf', 'watch', '/org/gnome/desktop/input-sources/']
            print(f"Запуск команды: {' '.join(cmd)}")
            
            self.monitor_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Запускаем поток для чтения вывода
            self.monitor_thread = threading.Thread(
                target=self._monitor_layout_changes,
                daemon=True
            )
            self.monitor_thread.start()
            print("✓ Мониторинг раскладки активирован")
            
        except Exception as e:
            print(f"! Ошибка запуска мониторинга: {e}")

    def _monitor_layout_changes(self):
        """Поток мониторинга изменений раскладки"""
        try:
            while True:
                output = self.monitor_process.stdout.readline()
                if output:
                    # При любом изменении в /org/gnome/desktop/input-sources/
                    # получаем текущую раскладку через gsettings
                    new_layout = self.get_current_layout()
                    if new_layout != self.current_layout:
                        print(f"\n=== Смена раскладки: {self.current_layout} -> {new_layout} ===")
                        self.current_layout = new_layout
                        self._notify_layout_changed(new_layout)
        except Exception as e:
            print(f"! Ошибка в мониторинге: {e}")
        finally:
            self.stop_layout_monitoring()

    def stop_layout_monitoring(self):
        """Остановка мониторинга раскладки"""
        if hasattr(self, 'monitor_process'):
            self.monitor_process.terminate()
            self.monitor_process = None

    def add_layout_callback(self, callback):
        """Добавление обработчика изменения раскладки"""
        self.layout_callbacks.append(callback)

    def _notify_layout_changed(self, new_layout):
        """Уведомление подписчиков об изменении раскладки"""
        for callback in self.layout_callbacks:
            try:
                callback(new_layout)
            except Exception as e:
                print(f"! Ошибка в обработчике раскладки: {e}") 

    def sync_with_system(self):
        """Синхронизация с системными настройками"""
        try:
            # Принудительно обновляем кэш dconf
            subprocess.run(['dconf', 'reset', '-f', '/org/gnome/desktop/input-sources/'],
                         check=True, capture_output=True)
            time.sleep(0.1)  # Даем время на применение изменений
            
            # Получаем актуальную раскладку
            self.current_layout = self.get_current_layout()
            print(f"Синхронизирована раскладка: {self.current_layout}")
            return self.current_layout
        except Exception as e:
            print(f"Ошибка синхронизации: {e}")
            return None 