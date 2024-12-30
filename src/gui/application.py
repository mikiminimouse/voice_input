import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, Gio, GLib, Gdk, AyatanaAppIndicator3 as AppIndicator
from src.utils import get_resource_path

class VoiceInputApp(Gtk.Application):
    def __init__(self, voice_input):
        super().__init__(
            application_id='org.example.VoiceInput',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.voice_input = voice_input
        self.window = None
        self.is_recording = False
        
        # Настройка горячих клавиш
        self.START_KEYS = "<Alt>v"
        self.QUIT_KEYS = "<Alt>q"
        self.LANG_KEYS = "<Alt>space"
        
        # Создаем действия приложения
        self.create_actions()
        
    def create_actions(self):
        """Создание действий приложения"""
        # Действие для переключения записи
        toggle_action = Gio.SimpleAction.new('toggle-recording', None)
        toggle_action.connect('activate', self.on_toggle_recording)
        self.add_action(toggle_action)
        
        # Действие для выхода
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.on_quit)
        self.add_action(quit_action)
        
        # Действие для переключения языка
        lang_action = Gio.SimpleAction.new('toggle-language', None)
        lang_action.connect('activate', self.on_toggle_language)
        self.add_action(lang_action)
    def do_activate(self):
        """Активация приложения"""
        # Создаем главное окно
        self.window = Gtk.Window.new(Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Voice Input")
        self.window.set_default_size(1, 1)
        
        # Добавляем обработчики клавиш
        self.setup_keyboard_shortcuts()
        
        # Создаем статус-иконку
        self.setup_status_icon()
        
        # Скрываем окно, но держим приложение активным
        self.window.hide()
        self.hold()
        
        # Подключаем обработчик закрытия окна
        self.window.connect('delete-event', lambda w, e: self.release())

    def setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш"""
        # Добавляем обработчик клавиш напрямую к окну
        self.window.connect('key-press-event', self.on_key_pressed_gtk3)

    def setup_status_icon(self):
        """Настройка иконки в системном трее"""
        try:
            print("Создание индикатора...")
            # Создаем индикатор
            self.indicator = AppIndicator.Indicator.new(
                "voice-input-indicator",
                get_resource_path('icons', 'microphone-off.png'),
                AppIndicator.IndicatorCategory.APPLICATION_STATUS
            )
            
            print("Создание меню...")
            # Создаем меню
            menu = Gtk.Menu()
            
            item_toggle = Gtk.MenuItem(label="Start/Stop (Alt+V)")
            item_toggle.connect('activate', 
                lambda _: self.activate_action('toggle-recording', None))
            menu.append(item_toggle)
            
            item_lang = Gtk.MenuItem(label="Switch Language (Alt+Space)")
            item_lang.connect('activate', 
                lambda _: self.activate_action('toggle-language', None))
            menu.append(item_lang)
            
            item_quit = Gtk.MenuItem(label="Quit (Alt+Q)")
            item_quit.connect('activate', 
                lambda _: self.activate_action('quit', None))
            menu.append(item_quit)
            
            menu.show_all()
            
            print("Установка меню...")
            # Устанавливаем меню и активируем индикатор
            self.indicator.set_menu(menu)
            self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            print("Индикатор успешно создан и активирован")
            
        except Exception as e:
            print(f"Ошибка создания индикатора: {e}")
            import traceback
            traceback.print_exc()

    def on_status_icon_popup(self, icon, button, time):
        """Обработка правого клика по иконке"""
        menu = Gtk.Menu()
        
        item_toggle = Gtk.MenuItem(label="Start/Stop (Alt+V)")
        item_toggle.connect('activate', 
            lambda _: self.activate_action('toggle-recording', None))
        menu.append(item_toggle)
        
        item_lang = Gtk.MenuItem(label="Switch Language (Alt+Space)")
        item_lang.connect('activate', 
            lambda _: self.activate_action('toggle-language', None))
        menu.append(item_lang)
        
        item_quit = Gtk.MenuItem(label="Quit (Alt+Q)")
        item_quit.connect('activate', 
            lambda _: self.activate_action('quit', None))
        menu.append(item_quit)
        
        menu.show_all()
        menu.popup_at_pointer(None)

    def on_status_icon_click(self, icon):
        """Обработка левого клика по иконке"""
        self.activate_action('toggle-recording', None)

    def on_key_pressed_gtk3(self, widget, event):
        """Обработка нажатий клавиш для GTK3"""
        keyval = event.keyval
        state = event.state
        
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        
        # Alt+V для старта/остановки записи
        if keyval == Gdk.KEY_v and modifiers == Gdk.ModifierType.MOD1_MASK:
            self.activate_action('toggle-recording', None)
            return True
            
        # Alt+Q для выхода
        if keyval == Gdk.KEY_q and modifiers == Gdk.ModifierType.MOD1_MASK:
            self.activate_action('quit', None)
            return True
            
        # Alt+Space для переключения языка
        if keyval == Gdk.KEY_space and modifiers == Gdk.ModifierType.MOD1_MASK:
            self.activate_action('toggle-language', None)
            return True
            
        return False

    def on_toggle_recording(self, action, param):
        """Обработка переключения записи"""
        try:
            self.is_recording = not self.is_recording
            print(f"\n=== {'Включение' if self.is_recording else 'Выключение'} записи ===")
            
            if self.is_recording:
                self.voice_input.start_recording()
            else:
                self.voice_input.stop_recording()
                
            self.update_status_icon()
        except Exception as e:
            print(f"Ошибка переключения записи: {e}")

    def on_toggle_language(self, action, param):
        """Обработка переключения языка"""
        # Делегируем обработку в сервис распознавания
        self.voice_input.recognizer.toggle_language()

    def on_quit(self, action, param):
        """Обработка выхода из приложения"""
        self.voice_input.audio.stop_recording()
        self.quit() 

    def update_status_icon(self):
        """Обновление иконки в трее"""
        try:
            icon_path = get_resource_path('icons', 
                'microphone-on.png' if self.is_recording else 'microphone-off.png')
            self.indicator.set_icon_full(icon_path, "Voice Input")
        except Exception as e:
            print(f"Ошибка обновления иконки: {e}") 

    def on_speech_recognized(self, text: str):
        """Обработка результатов распознавания речи"""
        print(f"Распознано: {text}")
        # Здесь можно добавить дополнительную обработку
        # Например, отправку текста в буфер обмена или эмуляцию ввода 