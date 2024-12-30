import gi
gi.require_version('Gtk', '3.0')

import sys
from gi.repository import Gtk, GLib
from dbus.mainloop.glib import DBusGMainLoop

from src.gui.application import VoiceInputApp
from src.audio.recorder import AudioRecorder
from src.recognition.vosk_service import VoskRecognizer

class VoiceInput:
    def __init__(self):
        print("\n=== Инициализация приложения ===")
        
        # Инициализация сервисов
        self.audio = AudioRecorder()
        print("✓ Аудио рекордер создан")
        
        self.recognizer = VoskRecognizer()
        print("✓ Распознаватель речи создан")
        
        from src.input.keyboard_layout import KeyboardLayout
        self.keyboard_layout = KeyboardLayout()
        print("✓ Монитор раскладки создан")
        
        print("===============================")
            
    def start_recording(self):
        """Начало записи"""
        try:
            print("\n=== Начало записи ===")
            
            # Получаем текущую раскладку единожды при старте
            current_layout = self.keyboard_layout.current_layout
            print(f"Текущая раскладка: {current_layout}")
            
            # Устанавливаем язык распознавания
            self.recognizer.set_language(current_layout)
            print(f"Установлен язык распознавания: {current_layout}")
            
            # Запускаем мониторинг изменений раскладки
            self.keyboard_layout.start_layout_monitoring()
            
            # Запускаем запись
            self.audio.add_state_callback(self.on_audio_data)
            self.audio.start_recording()
            print("✓ Запись активирована")
            
        except Exception as e:
            print(f"! Ошибка начала записи: {e}")
            
    def get_current_layout(self):
        """Получение текущей раскладки клавиатуры"""
        try:
            from src.input.keyboard_layout import KeyboardLayout
            layout = KeyboardLayout()
            return layout.get_current_layout()
        except Exception as e:
            print(f"Ошибка получения раскладки: {e}")
            return None
            
    def stop_recording(self):
        """Остановка записи"""
        try:
            self.audio.stop_recording()
        except Exception as e:
            print(f"Ошибка остановки записи: {e}")
            
    def on_audio_data(self, data):
        """Обработка аудио данных"""
        try:
            if self.recognizer.accept_waveform(data):
                result = self.recognizer.get_result()
                text = result.get('text', '')
                if text:
                    print(f"Распознано [{self.recognizer.current_language}]: {text}")
        except Exception as e:
            print(f"Ошибка обработки аудио: {e}")

def main():
    try:
        # Инициализация DBus
        DBusGMainLoop(set_as_default=True)
        
        # Создаем экземпляр VoiceInput
        voice_input = VoiceInput()
        
        # Создаем и запускаем приложение с voice_input
        app = VoiceInputApp(voice_input)
        return app.run(None)
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
