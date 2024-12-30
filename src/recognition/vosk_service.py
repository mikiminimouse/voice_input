import os
import json
from vosk import Model, KaldiRecognizer
from typing import Dict, Optional, Callable
import subprocess
import ast

class VoskRecognizer:
    """Класс для распознавания речи с использованием Vosk"""
    
    def __init__(self):
        print("=== Инициализация распознавания речи ===")
        print("1. Загрузка языковых моделей...")
        
        # Загружаем модели для разных языков
        self.models = {
            'ru': Model('models/model-ru'),
            'en': Model('models/model-en')
        }
        
        # Создаем распознаватели для каждого языка
        self.recognizers = {
            'ru': KaldiRecognizer(self.models['ru'], 16000),
            'en': KaldiRecognizer(self.models['en'], 16000)
        }
        
        self.current_language = 'ru'  # Язык по умолчанию
        print("✓ Языковые модели загружены")
        
        self.callbacks = []
        
    def add_result_callback(self, callback: Callable[[str], None]):
        """Добавление callback для получения результатов распознавания"""
        self.callbacks.append(callback)
        
    def set_language(self, language: str):
        """Установка языка распознавания"""
        if language in self.models and language != self.current_language:
            print(f"\n=== Смена языка распознавания ===")
            print(f"Старый язык: {self.current_language}")
            print(f"Новый язык: {language}")
            
            self.current_language = language
            self.recognizers[language] = KaldiRecognizer(self.models[language], 16000)
            print(f"✓ Распознаватель переключен на {language}")
            
    def process_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """Обработка аудио чанка"""
        if self.recognizers[self.current_language].AcceptWaveform(audio_chunk):
            result = json.loads(self.recognizers[self.current_language].Result())
            if 'text' in result and result['text'].strip():
                text = result['text'].strip()
                print(f"\nРаспознано [{self.current_language}]: {text}")
                for callback in self.callbacks:
                    try:
                        callback(text)
                    except Exception as e:
                        print(f"! Ошибка в обработчике результатов: {e}")
                return text
        return None 

    def accept_waveform(self, audio_data):
        """Обработка аудио данных"""
        return self.recognizers[self.current_language].AcceptWaveform(audio_data)

    def get_result(self):
        """Получение результата распознавания"""
        return json.loads(self.recognizers[self.current_language].Result()) 

    def toggle_language(self):
        """Переключение языка распознавания"""
        if self.current_language == 'ru':
            self.set_language('en')
        else:
            self.set_language('ru')
        print(f"\n=== Переключение языка распознавания на: {self.current_language} ===") 