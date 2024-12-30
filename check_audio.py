import pyaudio
import wave
import os

def test_microphone():
    p = pyaudio.PyAudio()
    
    print("\nПроверка доступных аудио устройств:")
    info = p.get_host_api_info_by_index(0)
    for i in range(info.get('deviceCount')):
        try:
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"\nУстройство {i}: {device_info.get('name')}")
                print(f"    Каналы: {device_info.get('maxInputChannels')}")
                print(f"    Частота дискретизации: {int(device_info.get('defaultSampleRate'))}")
                print(f"    Устройство по умолчанию: {'Да' if device_info.get('isDefaultInput') else 'Нет'}")
        except Exception as e:
            print(f"Ошибка при получении информации об устройстве {i}: {e}")

    try:
        # Записываем короткий тестовый файл
        print("\nПопытка записи тестового аудио...")
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        RECORD_SECONDS = 3
        
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)

        frames = []
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        
        # Сохраняем тестовый файл
        test_file = "test_audio.wav"
        wf = wave.open(test_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"Тестовая запись сохранена в {test_file}")
        
    except Exception as e:
        print(f"Ошибка при тестировании микрофона: {e}")
    finally:
        p.terminate()

if __name__ == "__main__":
    test_microphone() 