import json
import os
import sys
import pyaudio
import threading
from vosk import Model, KaldiRecognizer
import time
import gi

# Явно указываем версии до импорта
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')

from gi.repository import Gtk, GLib, Gio, Gdk, AyatanaAppIndicator3 as AppIndicator3
import dbus
from dbus.mainloop.glib import DBusGMainLoop

class VoiceInputIndicator:
    def __init__(self, voice_input):
        self.voice_input = voice_input
        self.current_icon = "microphone-off"
        self.is_pulsing = False
        
        # Путь к иконкам
        self.ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
        
        # Создаем индикатор
        self.indicator = AppIndicator3.Indicator.new(
            "voice-input-indicator",
            os.path.join(self.ICON_PATH, "microphone-off.png"),
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Создаем меню
        self.menu = Gtk.Menu()
        
        # Добавляем пункты меню
        item_toggle = Gtk.MenuItem(label="Старт/Стоп (Alt+V)")
        item_toggle.connect('activate', self.toggle_recording)
        self.menu.append(item_toggle)
        
        item_quit = Gtk.MenuItem(label="Выход (Alt+Q)")
        item_quit.connect('activate', self.quit)
        self.menu.append(item_quit)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        
        # Запускаем пульсацию
        GLib.timeout_add(500, self.pulse_icon)

    def set_recording(self, is_recording):
        self.is_pulsing = is_recording
        if not is_recording:
            self.indicator.set_icon_full(
                os.path.join(self.ICON_PATH, "microphone-off.png"),
                "Микрофон выключен"
            )

    def pulse_icon(self):
        if self.is_pulsing:
            self.pulse_state = not getattr(self, 'pulse_state', False)
            icon_name = "microphone-on.png" if self.pulse_state else "microphone-pulse.png"
            self.indicator.set_icon_full(
                os.path.join(self.ICON_PATH, icon_name),
                "Микрофон включен"
            )
        return True

    def toggle_recording(self, _):
        self.voice_input.toggle_listening()

    def quit(self, _):
        self.voice_input.stop_program()

class SoundPlayer:
    def __init__(self):
        self.SOUND_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds')
        
    def play_sound(self, sound_file):
        try:
            sound_path = os.path.join(self.SOUND_PATH, sound_file)
            if os.path.exists(sound_path):
                wf = wave.open(sound_path, 'rb')
                p = pyaudio.PyAudio()
                
                stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                              channels=wf.getnchannels(),
                              rate=wf.getframerate(),
                              output=True)
                
                data = wf.readframes(1024)
                while data:
                    stream.write(data)
                    data = wf.readframes(1024)
                
                stream.stop_stream()
                stream.close()
                p.terminate()
        except Exception as e:
            print(f"Ошибка воспроизведения звука: {e}")

class VoiceTyper:
    def __init__(self):
        # Инициализация GTK приложения
        self.app = Gtk.Application.new("org.example.VoiceInput", Gio.ApplicationFlags.FLAGS_NONE)
        self.app.connect('activate', self.on_activate)
        
        # Настройка звука
        self.device_index = self.init_audio()
        if self.device_index is None:
            print("Не удалось инициализировать аудио")
            sys.exit(1)
        
        # Настройка мониторинга раскладки
        self.setup_layout_monitor()
        
        # Инициализация моделей
        self.init_models()
        
        # Добавляем горячие клавиши
        self.START_KEYS = "<Alt>v"
        self.QUIT_KEYS = "<Alt>q"
        self.LANG_KEYS = "<Alt>space"
        
        # Инициализация плеера
        self.sound_player = SoundPlayer()
        
        # Индикатор создадим позже в on_activate
        self.indicator = None

    def init_audio(self):
        """Инициализация аудио устройства"""
        try:
            self.audio = pyaudio.PyAudio()
            # Используем PulseAudio напрямую
            device_index = None
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                if 'pulse' in device_info['name'].lower():
                    device_index = i
                    break
            return device_index
        except Exception as e:
            print(f"Ошибка инициализации аудио: {e}")
            return None

    def setup_layout_monitor(self):
        """Настройка мониторинга раскладки через D-Bus"""
        try:
            DBusGMainLoop(set_as_default=True)
            bus = dbus.SessionBus()
            
            # Подписываемся на сигналы изменения свойств
            bus.add_signal_receiver(
                self.on_layout_changed,
                dbus_interface='org.freedesktop.DBus.Properties',
                signal_name='PropertiesChanged',
                path='/org/gnome/Shell/InputSource'
            )
            
            print("Мониторинг раскладки через D-Bus успешно настроен")
            
        except Exception as e:
            print(f"Ошибка настройки мониторинга раскладки: {e}")

    def on_layout_changed(self, interface_name, changed_properties, invalidated):
        """Обработчик изменения раскладки"""
        try:
            if 'CurrentSource' in changed_properties:
                source = changed_properties['CurrentSource']
                new_language = 'en' if 'us' in str(source).lower() else 'ru'
                
                if new_language != self.current_language:
                    print(f"Смена раскладки: {self.current_language} -> {new_language}")
                    self.current_language = new_language
                    
                    if hasattr(self, 'recognizer'):
                        self.recognizer = KaldiRecognizer(
                            self.models[self.current_language], 
                            16000
                        )
                    
                    self.sound_player.play_sound('switch_language.wav')
                    
        except Exception as e:
            print(f"Ошибка в обработчике раскладки: {e}")

    def toggle_listening(self):
        try:
            if not self.is_listening:
                print("Включаем прослушивание...")
                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=self.device_index,
                    frames_per_buffer=8000,
                    stream_callback=self.audio_callback
                )
                self.is_listening = True
                self.indicator.set_recording(True)
            else:
                print("Выключаем прослушивание...")
                if self.stream:
                    self.stream.stop_stream()
                    self.stream.close()
                self.is_listening = False
                self.indicator.set_recording(False)
        except Exception as e:
            print(f"Ошибка переключения записи: {e}")

    def start_listening(self):
        try:
            self.silence_threshold = 700  # Порог тишины
            self.silence_counter = 0
            self.max_silence_frames = 50  # Максимальное количество фреймов тишины
            
            input_device = self.get_input_device_index()
            if input_device is None:
                print("Микрофон не найден!")
                return

            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=8000
            )
            print("Аудио поток открыт успешно")
            
            while self.is_listening:
                try:
                    data = self.stream.read(4000, exception_on_overflow=False)
                    
                    # Используем распознаватель текущего языка
                    current_recognizer = self.recognizers[self.current_language]
                    
                    if current_recognizer.AcceptWaveform(data):
                        result = json.loads(current_recognizer.Result())
                        text = result.get('text', '').strip()
                        if text:
                            print(f"Распознано [{self.current_language}]: {text}")
                            self.type_text(text + (' ' if text else ''))
                    else:
                        partial = json.loads(current_recognizer.PartialResult())
                        if partial.get('partial'):
                            print(f"Промежуточный результат [{self.current_language}]: {partial['partial']}")
                
                except Exception as e:
                    print(f"Ошибка при чтении аудио данных: {e}")
                    if not self.is_listening:
                        break
                    continue
                    
        except Exception as e:
            print(f"Ошибка при инициализации аудио: {e}")
            self.is_listening = False

    def preprocess_text(self, text):
        """Предварительная обработка текста перед вводом"""
        replacements = {
            'е': 'е',
            'ё': 'ё',
            # Добавьте другие замены если нужно
        }
        
        processed_text = text
        for old, new in replacements.items():
            processed_text = processed_text.replace(old, new)
        return processed_text

    def type_text(self, text):
        try:
            text = self.preprocess_text(text)
            print(f"Обработанный текст для ввода: {text}")
            
            env = os.environ.copy()
            env['DISPLAY'] = self.get_display()
            
            # Устанавливаем правильную раскладку перед вводом
            if self.current_language == 'ru':
                subprocess.run(['setxkbmap', 'ru'], env=env, check=True)
            else:
                subprocess.run(['setxkbmap', 'us'], env=env, check=True)
            
            time.sleep(0.1)  # Ждем переключения раскладки
            
            # Вводим текст
            result = subprocess.run(
                ['xdotool', 'type', '--clearmodifiers', text],
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Ошибка выполнения xdotool: {result.stderr}")
            else:
                print(f"Текст успешно введен на языке: {self.current_language}")
                
        except Exception as e:
            print(f"Ошибка ввода текста: {e}")
            print(traceback.format_exc())

    def stop_program(self):
        print("\nЗавершение программы...")
        self.is_active = False
        self.is_listening = False
        
        # Корректно закрываем аудио поток
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        
        try:
            self.audio.terminate()
        except:
            pass
        
        # Даем время на закрытие потоков
        time.sleep(0.1)
        os._exit(0)  # Принудительно завершаем процесс

    def on_activate(self, app):
        """Создание главного окна приложения"""
        try:
            # Создаем невидимое окно
            self.window = Gtk.Window()
            self.window.set_title("Voice Input")
            self.window.set_default_size(1, 1)
            
            # Добавляем обработчики клавиш
            self.window.connect('key-press-event', self.on_key_press)
            
            # Скрываем окно
            self.window.hide()
            
            # Теперь создаем индикатор
            self.indicator = VoiceInputIndicator(self)
            
        except Exception as e:
            print(f"Ошибка создания окна: {e}")
            self.audio.terminate()

    def on_key_press(self, widget, event):
        """Обработчик нажатий клавиш"""
        try:
            # Alt+V для старта/остановки записи
            if event.keyval == Gdk.KEY_v and event.state & Gdk.ModifierType.MOD1_MASK:
                self.toggle_listening()
                return True
                
            # Alt+Q для выхода
            if event.keyval == Gdk.KEY_q and event.state & Gdk.ModifierType.MOD1_MASK:
                self.stop_program()
                return True
                
        except Exception as e:
            print(f"Ошибка обработки клавиш: {e}")
        return False

    def run(self):
        """Запуск приложения"""
        try:
            print("Запуск приложения...")
            self.app.run(None)
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            self.stop_program()

    def get_input_device_index(self):
        print("\nДоступные аудио устройства:")
        default_device = None
        pulse_device = None
        
        for i in range(self.audio.get_device_count()):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                print(f"Устройство {i}: {device_info.get('name')}")
                print(f"    Каналы: {device_info.get('maxInputChannels')}")
                print(f"    По умолчанию: {'Да' if device_info.get('isDefaultInputDevice') else 'Нет'}")
                
                if device_info.get('maxInputChannels') > 0:
                    # Сначала проверяем устройство по умолчанию
                    if device_info.get('isDefaultInputDevice'):
                        default_device = i
                    # Затем проверяем PulseAudio
                    elif device_info.get('name').lower().find('pulse') != -1:
                        pulse_device = i
                        
            except Exception as e:
                print(f"Ошибка при получении информации об устройстве {i}: {e}")
        
        # Используем устройство по умолчанию, если оно доступно
        if default_device is not None:
            print(f"Выбрано устройство по умолчанию: {default_device}")
            return default_device
        # Иначе используем PulseAudio
        elif pulse_device is not None:
            print(f"Выбрано устройство PulseAudio: {pulse_device}")
            return pulse_device
        
        print("Не найдено подходящее устройство ввода")
        return None

    def is_text_input_window(self):
        """Проверяет, является ли активное окно полем ввода текста"""
        try:
            d = display.Display()
            window = d.get_input_focus().focus
            wm_class = window.get_wm_class()
            
            # Список классов окон, где разрешен ввод текста
            text_input_classes = ['gedit', 'code', 'terminal', 'firefox']
            
            return any(cls in str(wm_class).lower() for cls in text_input_classes)
        except:
            return True  # В случае ошибки разрешаем ввод

    def get_display(self):
        try:
            result = subprocess.run(['echo', '$DISPLAY'], 
                                  shell=True, 
                                  capture_output=True, 
                                  text=True)
            display = result.stdout.strip()
            if not display:
                display = ':0'
            return display
        except:
            return ':0'

    def get_system_layout(self):
        """Получение текущей системной раскладки клавиатуры"""
        try:
            # Получаем текущий индекс раскладки через dbus
            result = subprocess.run(
                ['dbus-send', '--session', '--print-reply', 
                 '--dest=org.gnome.Shell', '/org/gnome/Shell', 
                 'org.freedesktop.DBus.Properties.Get',
                 'string:org.gnome.Shell.InputSource',
                 'string:CurrentSource'],
                capture_output=True,
                text=True
            )
            
            # Анализируем вывод dbus
            output = result.stdout.strip()
            print(f"DBus output: {output}")
            
            # Определяем текущую раскладку
            if 'xkb' in output:
                if 'us' in output.lower():
                    return 'en'
                elif 'ru' in output.lower():
                    return 'ru'
            
            # Если не удалось определить через dbus, пробуем через gsettings
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.input-sources', 'current'],
                capture_output=True,
                text=True
            )
            current_index = int(result.stdout.strip().split()[-1])
            
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.input-sources', 'sources'],
                capture_output=True,
                text=True
            )
            layouts = eval(result.stdout.strip())
            
            if current_index < len(layouts):
                layout = layouts[current_index][1]
                print(f"Layout from gsettings: {layout}")
                if layout == 'us':
                    return 'en'
                elif layout == 'ru':
                    return 'ru'
            
            return self.current_language
            
        except Exception as e:
            print(f"Ошибка получения системной раскладки: {e}")
            return self.current_language

    def check_layout_change(self):
        """Проверка изменения системной раскладки"""
        try:
            new_language = self.get_system_layout()
            if new_language != self.current_language:
                print(f"Обнаружена смена раскладки с {self.current_language} на {new_language}")
                self.current_language = new_language
                
                # Пересоздаем распознаватель для нового языка
                if hasattr(self, 'recognizer'):
                    self.recognizer = KaldiRecognizer(self.models[self.current_language], 16000)
                    print(f"Распознаватель переключен на {self.current_language}")
                
                # Воспроизводим звук переключения
                self.sound_player.play_sound('switch_language.wav')
                
        except Exception as e:
            print(f"Ошибка при проверке раскладки: {e}")
        
        return True  # Для продолжения таймера

if __name__ == "__main__":
    typer = VoiceTyper()
    typer.run()
