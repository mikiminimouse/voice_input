import pyaudio
import wave
import os
from typing import Optional, Callable
from src.utils import get_resource_path

class AudioRecorder:
    """Класс для работы с аудио записью"""
    
    CHUNK_SIZE = 8000
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    def __init__(self):
        self.pyaudio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_recording = False
        self.device_index = self._init_audio_device()
        self.callbacks = []  # Список колбэков для уведомления о состоянии записи
        
        # Путь к звуковым файлам
        self.sounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     'resources', 'sounds')

    def _init_audio_device(self) -> Optional[int]:
        """Инициализация аудио устройства"""
        try:
            # Выводим список всех устройств для отладки
            print("\nДоступные аудио устройства:")
            for i in range(self.pyaudio.get_device_count()):
                device_info = self.pyaudio.get_device_info_by_index(i)
                print(f"Device {i}: {device_info['name']}")
            
            # Сначала пробуем найти PulseAudio
            for i in range(self.pyaudio.get_device_count()):
                device_info = self.pyaudio.get_device_info_by_index(i)
                if ('pulse' in device_info['name'].lower() and 
                    device_info['maxInputChannels'] > 0):
                    print(f"Используем PulseAudio устройство: {device_info['name']}")
                    return i
                
            # Если PulseAudio не найден, используем устройство по умолчанию
            default_device = self.pyaudio.get_default_input_device_info()
            print(f"Используем устройство по умолчанию: {default_device['name']}")
            return default_device['index']
            
        except Exception as e:
            print(f"Ошибка инициализации аудио устройства: {e}")
            return None

    def add_state_callback(self, callback: Callable[[bool], None]):
        """Добавление callback для уведомления об изменении состояния записи"""
        self.callbacks.append(callback)

    def _notify_state_changed(self):
        """Уведомление всех подписчиков об изменении состояния"""
        for callback in self.callbacks:
            try:
                callback(self.is_recording)
            except Exception as e:
                print(f"Ошибка в callback обработчике: {e}")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback для обработки входящего аудио потока"""
        if self.is_recording:
            # Отправляем данные в распознаватель через callback
            for callback in self.callbacks:
                try:
                    callback(in_data)
                except Exception as e:
                    print(f"Ошибка обработки аудио данных: {e}")
        return (in_data, pyaudio.paContinue)

    def start_recording(self):
        """Запуск записи"""
        if not self.is_recording and self.device_index is not None:
            try:
                self.stream = self.pyaudio.open(
                    format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    input_device_index=self.device_index,
                    frames_per_buffer=self.CHUNK_SIZE,
                    stream_callback=self._audio_callback
                )
                self.is_recording = True
                self._notify_state_changed()
                self.play_sound("start_recording.wav")
            except Exception as e:
                print(f"Ошибка запуска записи: {e}")

    def stop_recording(self):
        """Остановка записи"""
        if self.is_recording:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.is_recording = False
                self._notify_state_changed()
                self.play_sound("stop_recording.wav")
            except Exception as e:
                print(f"Ошибка остановки записи: {e}")

    def play_sound(self, sound_file: str):
        """Воспроизведение звукового сигнала"""
        try:
            sound_path = get_resource_path('sounds', sound_file)
            if os.path.exists(sound_path):
                wf = wave.open(sound_path, 'rb')
                stream = self.pyaudio.open(
                    format=self.pyaudio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                data = wf.readframes(1024)
                while data:
                    stream.write(data)
                    data = wf.readframes(1024)
                    
                stream.stop_stream()
                stream.close()
                wf.close()
        except Exception as e:
            print(f"Ошибка воспроизведения звука: {e}")

    def cleanup(self):
        """Очистка ресурсов"""
        if self.stream:
            self.stop_recording()
        self.pyaudio.terminate() 