import os
import code
import ctypes
import subprocess
import sys
import random
import datetime
import hashlib
import math
import string
import json
import locale
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PlaylistEditor import PlaylistEditor  # Импорт нового класса
from Localization import Localization
from FontLoader import FontLoader

def is_shift_pressed():
    """Проверяет, зажата ли клавиша Shift при запуске"""
    VK_SHIFT = 0x10
    return ctypes.windll.user32.GetKeyState(VK_SHIFT) & 0x8000

def setup_console():
    """Настраивает консоль и перенаправляет потоки вывода"""
    if sys.platform == 'win32':
        ctypes.windll.kernel32.AllocConsole()
        # Перенаправляем стандартные потоки
        sys.stdout = open('CONOUT$', 'w')
        sys.stderr = open('CONOUT$', 'w')
        sys.stdin = open('CONIN$', 'r')

def handle_exception(type, value, traceback):
    """Обработчик неотловленных исключений"""
    if sys.stdout:  # Если вывод доступен
        print("\n=== НЕОБРАБОТАННОЕ ИСКЛЮЧЕНИЕ ===")
        print(f"Тип: {type.__name__}")
        print(f"Ошибка: {value}")
        if 'is_shift_pressed' in globals() and is_shift_pressed():
            import traceback as tb
            tb.print_exception(type, value, traceback)
    messagebox.showerror("Критическая ошибка", str(value))



class PlaylistGenerator:
    def __init__(self, root, file_to_open=None):
        
        self.debug_mode = is_shift_pressed() or not getattr(sys, 'frozen', False)
        
        if self.debug_mode:
            print("Инициализация PlaylistGenerator")
            print(f"Загружено файлов: {len(file_paths) if file_paths else 0}")
        
        
        self.root = root
        self.localization = Localization()
        self.last_folders = []
        self.visited_github = False
        self.github_link = None
        self.format_m3u8 = "m3u8"  # Строка для хранения формата
        self.format_combobox = None  # Виджет Combobox
        self.load_settings()
        self.root.title(self.localization.tr("window_title_generator"))

        
        # Обработка переданного файла ДО создания виджетов
        if file_to_open:
            self.root.withdraw()
            file_to_open = file_to_open.strip('"')
            if file_to_open.lower().endswith('.m3u8'):
                self.root.after(1, lambda: self.open_editor(file_to_open))
                return  # Прерываем инициализацию основного окна                   
            if file_to_open.lower().endswith('.m3u'):
                self.root.after(1, lambda: self.open_editor(file_to_open))
                return
            if file_to_open.lower().endswith('.txt'):
                self.root.after(1, lambda: self.open_editor(file_to_open))
                return
        
        self.create_widgets()
        self.show_version_info()

        
        if self.last_folders:
            if len(self.last_folders) == 1:
                display_text = self.last_folders[0]
            else:
                display_text = ', '.join(os.path.basename(p) for p in self.last_folders)
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, display_text)

        # Установка размеров окна
        window_width = 540
        window_height = 310
        root.resizable(width=False, height=False)
    
        # Получаем размеры экрана
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
    
        # Вычисляем координаты для центрирования
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
    
        # Устанавливаем положение и размер
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(540, 310)
    
        if self.last_folders:
            self.folder_entry.insert(0, self.last_folders)
        
        
        # Обновляем поле ввода с последними папками
        self.update_folder_entry()
        self.font_loader = FontLoader(root)
        self.icon_ico = self.font_loader.icon_ico
    
    def is_valid_folders(self, paths):
        """Проверяет, существуют ли все папки в списке"""
        if not paths:
            return False
        
        for path in paths:
            if not path or not os.path.isdir(path):
                return False
        return True
        
        
    def show_version_info(self):
        from version_info import version_info
        version_label = tk.Label(
            self.root, 
            text=f"{version_info['product_name']} v{version_info['version']} by {version_info['author']}",
            fg="gray"
        )
        # Размещаем в правом нижнем углу окна
        version_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-5)
    
    
    def load_settings(self):
        """Загружает все настройки из файла, включая язык и последнюю папку"""
        try:
            settings = {
                'language': self.localization.current_lang,
                'last_folders': [],
                'visited_github': self.visited_github,
                'playlist_format': self.format_m3u8
            }
            with open('playlist_settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.visited_github = settings.get('visited_github')   
                saved_format = settings.get('playlist_format')                
                saved_lang = settings.get('language')
                if saved_lang and self.localization.is_language_supported(saved_lang):
                    self.localization.set_language(saved_lang)
                    print(f"[DEBUG] Загружен язык: {saved_lang}")
                else:
                    sys_lang = self.localization.detect_system_language()
                    self.localization.set_language(sys_lang)
                    print(f"[DEBUG] Неподдерживаемый язык в настройках. Авто–язык: {sys_lang}")
                    self.save_settings()       
                
                # Устанавливаем значение напрямую, если оно есть в списке
                if saved_format in ["m3u8", "m3u", "txt"]:
                    self.format_m3u8 = saved_format
                    print(f"[DEBUG] Загружен формат: {saved_format}")
                else:
                    
                    self.format_m3u8 = "m3u8"
                    print(f"[DEBUG] Неподдерживаемый формат '{saved_format}'. Авто–формат: m3u8")
                    
                    
                if 'last_folders' in settings and isinstance(settings['last_folders'], list):
                    # Оставляем только существующие папки
                    self.last_folders = [f for f in settings['last_folders'] if self.is_valid_folders([f])]
                return settings
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"[DEBUG] Файл настроек не найден. Был создан новый.")
            sys_lang = self.localization.detect_system_language()
            print(f"[DEBUG] Автоматический выбор языка: {sys_lang}")
            self.localization.set_language(sys_lang)
            self.visited_github = False
            self.last_folders = []
            self.format_m3u8 = "m3u8"
            print(f"[DEBUG] Автоматический выбор формата: m3u8")
            self.save_settings()
            
    
    def save_settings(self):
        """Сохраняет все настройки в файл"""
        
        settings = {
            'language': self.localization.current_lang,
            'last_folders': self.last_folders,
            'visited_github': self.visited_github,
            'playlist_format': self.format_m3u8
        }
        try:
            with open('playlist_settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(self.localization.tr("error_save_settings").format(error=e))
    
   
    
    def open_github(self, event=None):
        """Обработчик клика по GitHub ссылке"""
        import webbrowser
        webbrowser.open("https://github.com/VolfLife/Playlist-Generator/")
        print(f"[DEBUG] Ссылка: https://github.com/VolfLife/Playlist-Generator/")
        if not self.visited_github:
            self.visited_github = True
            self.save_settings()  # Сначала сохраняем
            
            # Затем обновляем виджет
            if self.github_link:
                self.github_link.config(fg="gray")
            else:
                self.create_github_link()  # Пересоздаем если не существует     
            
    def create_github_link(self):
        """Создает кликабельную GitHub ссылку"""
        if hasattr(self, 'github_link') and self.github_link:
            self.github_link.destroy()
        
        color = "gray" if self.visited_github else "black"
        
        self.github_link = tk.Label(
            self.root,
            text="GitHub",
            fg=color,
            cursor="hand2",
            font=("Arial", 10, "underline"),
            bg=self.root.cget('bg')  # Фон как у основного окна
        )
        # Размещаем ссылку в левом нижнем углу ВСЕГО окна
        self.github_link.place(relx=0.0, rely=1.0, anchor="sw", x=10, y=-5)
        self.github_link.bind("<Button-1>", self.open_github)
        
            
    
    def open_editor(self, file_path):
        """Открывает редактор и корректно закрывает текущее окно"""
        # Скрываем основное окно генератора
        self.root.withdraw()
        try:
            editor_root = tk.Tk()
            PlaylistEditor(editor_root, file_path)
            self.root.destroy()  # Закрываем основное окно только после успешного создания редактора
            editor_root.mainloop()
        except Exception as e:
            print(self.localization.tr("error_open_editor").format(error=e))
            self.root.destroy()
    
    
    def process_dropped_file(self, file_path):
        """Обработка переданного файла при запуске"""
        if file_path and file_path.lower().endswith('.m3u8'):
            self.root.destroy()  # Закрываем текущее окно
            editor_root = tk.Tk()
            PlaylistEditor(editor_root, file_path)
            editor_root.mainloop()
        if file_path and file_path.lower().endswith('.m3u'):
            self.root.destroy()  # Закрываем текущее окно
            editor_root = tk.Tk()
            PlaylistEditor(editor_root, file_path)
            editor_root.mainloop()    
        if file_path and file_path.lower().endswith('.txt'):
            self.root.destroy()  # Закрываем текущее окно
            editor_root = tk.Tk()
            PlaylistEditor(editor_root, file_path)
            editor_root.mainloop()    
        
    def change_format(self, event=None):
        """Сохраняет настройки выбранного формата файла"""
        self.format_m3u8 = self.format_combobox.get()
        try:
            with open('playlist_settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}
        
        settings['playlist_format'] = self.format_m3u8
        
        with open('playlist_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        
        print(f"[DEBUG] Формат файла сохранен: {self.format_m3u8}")        

        
    def change_language(self, event=None):
        """Обработчик смены языка"""
        selected_name = self.language_var.get()
        # Находим код языка по выбранному названию
        for code, name in self.localization.lang_names.items():
            if name == selected_name:
                new_lang = code
                break
        else:
            new_lang = "en-us"  # fallback
            print(f"[DEBUG] Неподдерживаемый язык. Авто–язык: {new_lang}")
    
        if new_lang != self.localization.current_lang:
            self.localization.set_language(new_lang)
            self.save_language_settings()
            # Обновляем заголовок окна
            self.root.title(self.localization.tr("window_title_generator"))
            # Обновляем текст кнопки генерации
            self.generate_btn.config(text=self.localization.tr("generate_button"))
            self.browse_btn.config(text=self.localization.tr("browse_button"))
            self.shadow_seed_check.config(text=self.localization.tr("shadow_seed_check"))
            # Обновляем остальной интерфейс
            self.update_ui_texts()
        
            # Обновляем список форматов сида
            self.seed_format['values'] = self.localization.get_seed_format_options()

            
            # Получаем текущее значение формата сида
            current_seed_format = self.seed_format.get()
            # Список форматов, при которых текущее значение не должно меняться
            numeric_formats = ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                        "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "数字のみ"]
            # Проверяем, находится ли текущее значение в списке форматов
            if current_seed_format in numeric_formats:
                # Если текущее значение в списке, не меняем его
                self.seed_format['values'] = self.localization.get_seed_format_options()
                self.seed_format.current(0)
            else:
                # Если текущее значение не в списке, устанавливаем значение по умолчанию
                self.seed_format.current(1)  # Устанавливаем второе значение как значение по умолчанию
                
            # Обновляем имя плейлиста по умолчанию
            self.playlist_entry.delete(0, tk.END)
            self.playlist_entry.insert(0, self.localization.tr("default_playlist_name"))

    
    def save_language_settings(self):
        """Сохраняет настройки языка"""
        try:
            with open('playlist_settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}
        
        settings['language'] = self.localization.current_lang
        
        with open('playlist_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        
        print(f"[DEBUG] Язык сохранен: {self.localization.current_lang}")        
    
    def update_folder_entry(self):
        """Обновляет поле ввода с последними папками"""
        if self.last_folders:
            if len(self.last_folders) == 1:
                display_text = self.last_folders[0]
            else:
                display_text = ', '.join(os.path.basename(p) for p in self.last_folders)
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, display_text)
            
            
    def create_widgets(self):
        # Настройка сетки для растягивания
        self.root.grid_columnconfigure(1, weight=1)
        
        # Метки и поля ввода
        tk.Label(self.root, text=self.localization.tr("music_folder_label")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.folder_entry = ttk.Entry(self.root, width=40)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        
        self.browse_btn = ttk.Button(
            self.root,
            text=self.localization.tr("browse_button"),
            command=self.browse_folders
            )
        self.browse_btn.grid(row=0, column=2, padx=1, pady=10, sticky="w")
        
        tk.Label(self.root, text=self.localization.tr("playlist_name_label")).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.playlist_entry = ttk.Entry(self.root, width=40)
        self.playlist_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.playlist_entry.insert(0, self.localization.tr("default_playlist_name")) # Добавляем значение по умолчанию
        
        
        tk.Label(self.root, text=self.localization.tr("seed_label")).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.seed_entry = ttk.Entry(self.root, width=40)
        self.seed_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Поле для шага реверса
        tk.Label(self.root, text=self.localization.tr("reverse_step_label")).grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.step_entry = ttk.Entry(self.root, width=40)
        self.step_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Выбор формата сида
        tk.Label(self.root, text=self.localization.tr("seed_format_label")).grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.seed_format = ttk.Combobox(self.root, 
                                      values=self.localization.tr("seed_formats"), 
                                      state="readonly")
        self.seed_format.current(0)
        self.seed_format.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Чекбокс для теневого сида
        self.use_shadow_seed = tk.BooleanVar()
        self.shadow_seed_check = ttk.Checkbutton(
            self.root, 
            text=self.localization.tr("shadow_seed_check"),
            variable=self.use_shadow_seed,
            command=self.toggle_step_entry
        )
        self.shadow_seed_check.grid(row=5, column=0, columnspan=3, pady=5)
        
        # Добавляем подсказку при наведении курсора
        self.folder_entry_tooltip = tk.Label(self.root, text=self.localization.tr("folder_entry_tooltip"), 
                                           bg="beige", relief="solid", borderwidth=1)
        self.folder_entry_tooltip.place_forget()
        self.folder_entry.bind("<Enter>", self.show_folder_entry_tooltip)
        self.folder_entry.bind("<Leave>", self.hide_folder_entry_tooltip)
        
        # Добавляем обработчик правой кнопки мыши для очистки
        self.folder_entry.bind("<Button-3>", self.clear_folder_entry)
        
        
        # Выбор языка
        language_frame = ttk.Frame(self.root)
        language_frame.grid(row=6, column=0, columnspan=3, pady=5, sticky="ew")
    
        self.language_label = tk.Label(language_frame, text=self.localization.tr("language_label"))
        self.language_label.pack(side=tk.LEFT, padx=(10, 5))
    
        # Создаем список языков в формате (название, код)
        lang_options = [(self.localization.lang_names[code], code) 
                        for code in self.localization.languages]
    
        # Сортируем по названию языка
        lang_options.sort()
    
        self.language_var = tk.StringVar()
        # Устанавливаем текущий язык
        current_lang_name = self.localization.lang_names.get(self.localization.current_lang, "English")
        self.language_var.set(current_lang_name)
    
        self.language_dropdown = ttk.Combobox(
            language_frame, 
            textvariable=self.language_var,
            values=[name for name, code in lang_options],  # Только названия
            state="readonly"
        )
        self.language_dropdown.pack(side=tk.LEFT)
        self.language_dropdown.bind("<<ComboboxSelected>>", self.change_language)
        
        # Кнопка генерации
        self.generate_btn = ttk.Button(
            language_frame,
            text=self.localization.tr("generate_button"),
            command=self.generate_playlist
        )
        self.generate_btn.pack(side=tk.LEFT, padx=(95, 10))
        
        
        # Combobox формата
        self.format_combobox = ttk.Combobox(
            language_frame,
            values=["m3u8", "m3u", "txt"],
            state="readonly",
            width=5
        )

        self.format_combobox.pack(side=tk.LEFT)
        self.format_combobox.set(self.format_m3u8)
        self.format_combobox.bind("<<ComboboxSelected>>", self.change_format)
        
        # Поле для вывода информации
        self.seed_info = tk.Label(self.root, text="", fg="green", bg=self.root.cget('bg'))
        self.seed_info.grid(row=7, column=0, columnspan=3, pady=5)
        
        
        self.create_github_link()  # Создаем ссылку на GitHub
        
        # Убедимся, что ссылка поверх информации
        self.github_link.lift()  # Поднимаем на передний план
        

    
    def show_folder_entry_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = self.localization.tr("folder_entry_tooltip")
        self.folder_entry_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.folder_entry_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.folder_entry.winfo_x()  # Позиция поля ввода
        entry_width = self.folder_entry.winfo_width()  # Ширина поля
        tooltip_width = self.folder_entry_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + (entry_width - tooltip_width) // 2
        y = self.folder_entry.winfo_y() + 20  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.folder_entry_tooltip.place(x=x, y=y)

    def hide_folder_entry_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'folder_entry_tooltip'):
            self.folder_entry_tooltip.place_forget()
    
    
    def clear_folder_entry(self, event=None):
        # Очищаем поле ввода и список папок, сохраняем настройки
        self.folder_entry.delete(0, tk.END)
        self.last_folders = []
        self.save_settings()
        self.hide_folder_entry_tooltip()
        print(f"[DEBUG] Поле ввода очищена")
        
    def update_ui_texts(self):
        """Обновляет все тексты в интерфейсе"""
        # Обновляем language_label
        self.language_label.config(text=self.localization.tr("language_label"))
        
        widgets_to_update = [
            (0, 0, "music_folder_label"),
            (0, 2, "browse_button"),
            (1, 0, "playlist_name_label"),
            (2, 0, "seed_label"),
            (3, 0, "reverse_step_label"),
            (4, 0, "seed_format_label"),
            (5, 0, "shadow_seed_check"),
            (6, 1, "generate_button"),
            (6, 0, "language_label"), # Для label в language_frame
        ]
        
        for row, col, key in widgets_to_update:
            widget = self.root.grid_slaves(row=row, column=col)[0]
            if isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton)):
                widget.config(text=self.localization.tr(key))
        
        # Обновляем текст подсказки
        if hasattr(self, 'folder_entry_tooltip'):
            self.folder_entry_tooltip.config(text=self.localization.tr("folder_entry_tooltip"))
        

    def toggle_step_entry(self):
        """Блокировка/разблокировка поля шага реверса"""
        if self.use_shadow_seed.get():
            self.step_entry.config(state='disabled')
            self.step_entry.delete(0, tk.END)
            self.step_entry.insert(0, "0")
        else:
            self.step_entry.config(state='normal')

    def browse_folders(self):
        selected_dir = filedialog.askdirectory()
        if selected_dir:
            if not self.last_folders:
                self.last_folders = []
                print(f"[DEBUG] Нет последних папок")
            if selected_dir not in self.last_folders:
                self.last_folders.append(selected_dir)
            # Если одна папка — показываем полный путь
            if len(self.last_folders) == 1:
                display_text = self.last_folders[0]
                print(f"[DEBUG] Была выбрана папка: {display_text}")
            else:
                # Иначе показываем имена папок через запятую
                display_text = ', '.join(os.path.basename(p) for p in self.last_folders)
                print(f"[DEBUG] Были выбраны папки: {display_text}")
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, display_text)
            self.save_settings()

               
    def stable_hash(self, s):
        """Детерминированная замена hash() с использованием hashlib"""
        return int(hashlib.md5(str(s).encode()).hexdigest(), 16) % (10**12)
    

    def get_audio_files(self, folders):
        """Принимает список папок, возвращает общий список аудиофайлов всех папок"""
        audio_extensions = {
                # Аудио
                '.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.wma', '.opus', '.aiff',
                # Видео
                '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'
            }
        audio_files = []
        for folder in folders:
            try:
                for root, _, files in os.walk(folder):
                    for file in files:
                        if Path(file).suffix.lower() in audio_extensions:
                            full_path = os.path.join(root, file)
                            try:
                                with open(full_path, 'rb'):
                                    pass
                                audio_files.append(full_path)
                            except (IOError, OSError):
                                continue
            except (OSError, UnicodeDecodeError) as e:
                print(self.localization.tr("error_scanning_folder").format(error=e))
                continue
        
        # Сортируем аудиофайлы сначала по ASCII символам, затем A-Z
        # Т.к. sort стабилен, сортируем дважды
        audio_files.sort(key=lambda x: (not os.path.basename(x)[0].isalpha(), os.path.basename(x).lower()))
        return audio_files


    def generate_seed(self, num_tracks, date, total_size, iteration=0):
        """Генерация предсказуемого основного сида на основе даты и n!"""
        import _pylong
        sys.set_int_max_str_digits(0)
        # Вычисляем факториал
        fact = math.factorial(num_tracks)
        print(f"[DEBUG] Факториал {num_tracks}! = {fact} \n===================================================================")
        
        # Предсказуемая часть: дата + количество треков
        date_part = int(date.timestamp())
        base_seed = (date_part * num_tracks * total_size) % fact
        
        if not hasattr(self, '_base_seed'):
            self._base_seed = (int(date.timestamp()) * num_tracks * total_size) % fact
            
        # Добавляем итерацию для плавного изменения
        modified_seed = self._base_seed + iteration % fact
        
        print(f"[DEBUG] ГЕНЕРАЦИЯ ОСНОВНОГО СИДА \n=================================================================== \n Дата = {date_part} \n Размер = {total_size} \n Количество треков = {num_tracks} \n Базовый сид = {base_seed} \n Результат = {modified_seed}")
        # Форматируем в соответствии с выбранным форматом
        if self.seed_format.get() in ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                        "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "数字のみ", "Kun tal", "Endast siffror", "Vain numerot", "Slegs Syfers", "Chỉ số"]:
            return str(modified_seed).zfill(len(str(fact)))
        else:
            # Для буквенно-цифрового формата используем хеш
            hash_obj = hashlib.sha256(str(modified_seed).encode())
            return hash_obj.hexdigest()[:len(str(fact))]
        
        
        
    def generate_shadow_seed(self, num_tracks, seed_trimmed):
        """Генерация непредсказуемого теневого сида"""
        import _pylong
        sys.set_int_max_str_digits(0)
        
        # Вычисляем факториал
        fact = math.factorial(num_tracks)
        
        # Непредсказуемая часть: хеш основного сида + случайное число
        random_part = random.getrandbits(256)
        random_nbr = random.getrandbits(128)
        random_nbrr = random.getrandbits(64)
        number = [1, random_nbr, random_nbrr, 1]
        random_divisor = random.choice(number)
        result = (random_part // random_divisor)
        
        seed_num = int(seed_trimmed) if isinstance(seed_trimmed, str) else seed_trimmed
        
        predictable_num = (seed_num + result + 1) % fact
        
        
        print(f"[DEBUG] ГЕНЕРАЦИЯ ТЕНЕВОГО СИДА \n=================================================================== \n Количество треков = {num_tracks} \n Случайное число = {random_part} \n Делитель = {random_divisor} \n Разность = {result} \n Основной сид = {seed_num} \n Результат = {predictable_num}")
        # Форматируем аналогично основному сиду
        if self.seed_format.get() in ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                        "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "Kun tal", "Endast siffror", "Vain numerot", "Slegs Syfers", "Chỉ số"]:
            return str(predictable_num).zfill(len(str(fact)))
        else:
            # Для буквенно-цифрового формата используем хеш
            hash_obj = hashlib.sha256(str(predictable_num).encode())
            return hash_obj.hexdigest()[:len(str(fact))]
        
        
        
    def generate_playlist(self):
        import _pylong
        sys.set_int_max_str_digits(0)
        print(f"[DEBUG] ПРОЦЕСС ПЕРЕМЕШИВАНИЯ \n===================================================================")
        # Разбор введённого текста в поле папок (несколько, разделены ',')
        input_text = self.folder_entry.get()
        # По запятым, с очисткой пробелов
        input_paths = [p.strip() for p in input_text.split(',') if p.strip()]
        
        if not input_paths:
            self.seed_info.config(text=self.localization.tr("error_no_music_folder"), fg="red")
            return
        valid_paths = [p for p in self.last_folders if os.path.isdir(p)]
        if not valid_paths:
            self.seed_info.config(text=self.localization.tr("error_folder_not_exist"), fg="red")
            return
        
        playlist_name = self.playlist_entry.get()
        if not playlist_name:
            self.seed_info.config(text=self.localization.tr("error_no_playlist_name"), fg="red")
            return
        
        user_seed = self.seed_entry.get()
        step_value = self.step_entry.get()


        # Обработка шага реверса
        step = 0
        if step_value.strip():
            try:
                step = int(step_value)
                if step < 0 or step > 20:
                    raise ValueError
            except ValueError:
                self.seed_info.config(text=self.localization.tr("error_reverse_step"), fg="red")
                return

        # Получаем аудиофайлы
        audio_files = self.get_audio_files(valid_paths)
        if not audio_files:
            self.seed_info.config(text=self.localization.tr("error_no_audio_files"), fg="red")
            return


        num_tracks = len(audio_files)
        total_size = sum(os.path.getsize(f) for f in audio_files)
        now = datetime.datetime.now()

    
        # Счетчик итераций (сбрасывается при ручном вводе сида)
        if not hasattr(self, '_generation_iteration'):
            self._generation_iteration = 0
        elif not user_seed:  # только для автоматического сида
            self._generation_iteration += 1
        
        
        # Генерация сидов
        if not user_seed or user_seed == "0":
            seed = self.generate_seed(num_tracks, now, total_size, self._generation_iteration)
        else:
            seed = user_seed

        # Обрезаем нули
        seed_trimmed = seed.lstrip('0') or '0'
        
        
        # Всегда генерируем теневой сид, даже если не используется
        shadow_seed = self.generate_shadow_seed(num_tracks, seed_trimmed)
        
        # Обрезаем нули
        shadow_seed_trimmed = shadow_seed.lstrip('0') or '0'
        
        
        print(f"[DEBUG] Основной сид = {seed}")
        print(f"[DEBUG] Теневой сид = {shadow_seed} ")
        
        print(f"[DEBUG] Использованный основной сид = {seed_trimmed}")
        print(f"[DEBUG] Использованный теневой сид = {shadow_seed_trimmed}")

        # Определяем путь для сохранения
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        # Получаем выбранный формат
        playlist_format = self.format_m3u8
        if not playlist_format:  # Защита на случай пустого значения
            playlist_format = "m3u8" 
                
        playlist_path = os.path.join(script_dir, f"{playlist_name}.{playlist_format}")


        # Обработка перемешивания
        reverse_step = None
        if self.use_shadow_seed.get():       
            # Определяем шаг реверса (1-20)
            reverse_step = random.randint(1, 20)
            print(f"[DEBUG] Реверс = {reverse_step}")
            
            # Основное перемешивание по теневому сиду
            shuffled = self.shuffle_files(audio_files, str(shadow_seed_trimmed))
            
            # Применяем реверс блоков
            shuffled_files = self.apply_reverse_step(shuffled, reverse_step)
            
            info_text = self.localization.tr("seed_info_shadow").format(
                seed=seed_trimmed, shadow_seed=shadow_seed_trimmed, step=reverse_step
            )
        elif step > 0:
            # Ручной шаг реверса
            reverse_step = step
            print(f"[DEBUG] Реверс = {reverse_step}")
            shuffled = self.soft_shuffle(audio_files, str(seed_trimmed))
            shuffled_files = self.apply_reverse_step(shuffled, reverse_step)
            info_text = self.localization.tr("seed_info_step").format(
                seed=seed_trimmed, step=reverse_step
            )
        else:
            if user_seed:
                shuffled_files = self.shuffle_files(audio_files, str(seed_trimmed))
                info_text = self.localization.tr("seed_info_basic").format(seed=seed_trimmed)
            else:
                # Без реверса
                shuffled_files = self.soft_shuffle(audio_files, str(seed_trimmed))
                info_text = self.localization.tr("seed_info_basic").format(seed=seed_trimmed)

        # Создание плейлиста
        self.save_m3u8_playlist(
            path=playlist_path,
            files=shuffled_files,
            name=playlist_name,
            seed=seed_trimmed,
            shadow_seed=shadow_seed_trimmed,
            num_tracks=num_tracks,
            date=now,
            reverse_step=reverse_step,
            playlist_format=playlist_format
        )

        self.last_folder = valid_paths
        self.save_settings()
        self.seed_info.config(text=self.localization.tr("playlist_created").format(info=info_text), fg="green")
    
    
    def save_m3u8_playlist(self, path, files, name, seed, shadow_seed, num_tracks, date, reverse_step=None, playlist_format=None):
        """Создает M3U8 файл плейлиста"""
        date_str = date.strftime("%Y-%m-%d %H:%M:%S")
        if playlist_format in ["m3u8", "m3u"]:      
            with open(path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write("#Made with VolfLife's Playlist Generator\n")
                f.write(f"#GENERATED:{date_str}\n")
                f.write(f"#PLAYLIST:{name}\n")
                f.write(f"#SEED:{seed}\n")
                f.write(f"#SHADOW_SEED:{shadow_seed}\n")
                
                if reverse_step is not None and reverse_step > 0:
                    f.write(f"#REVERSE_STEP:{reverse_step}\n")
                
                f.write(f"#TRACKS:{num_tracks}\n")

                f.write("\n")  # Разделитель
                
                for file_path in files:
                    file_path = os.path.normpath(file_path)
                    escaped_path = file_path.replace('\\', '/')
                    f.write(f"#EXTINF:-1,{os.path.basename(file_path)}\n")
                    f.write(f"{escaped_path}\n")
        
        if playlist_format in ["txt"]:      
            with open(path, 'w', encoding='utf-8') as f:
                f.write("#Made with VolfLife's Playlist Generator\n")
                f.write(f"#GENERATED:{date_str}\n")
                f.write(f"#TRACKLIST:{name}\n")
                f.write(f"#SEED:{seed}\n")
                f.write(f"#SHADOW_SEED:{shadow_seed}\n")
                
                if reverse_step is not None and reverse_step > 0:
                    f.write(f"#REVERSE_STEP:{reverse_step}\n")
                
                f.write(f"#TRACKS:{num_tracks}\n")

                f.write("\n")  # Разделитель
                
                for file_path in files:
                    file_path = os.path.normpath(file_path)
                    escaped_path = file_path.replace('\\', '/')
                    f.write(f"{escaped_path}\n")
        
        
    def apply_reverse_step(self, files, step):
        """Применяет реверс блоков без повторной фиксации генератора"""
        # Создаем копию списка, чтобы не менять оригинал
        reversed_files = files.copy()
        for i in range(0, len(reversed_files), step):
            reversed_files[i:i+step] = reversed(reversed_files[i:i+step])
        return reversed_files
    
           
    
    def shuffle_files(self, files, seed_value):
        """Улучшенное перемешивание с явным указанием сида"""
        random.seed(abs(self.stable_hash((str(seed_value)))))
        shuffled = files.copy()
        random.shuffle(shuffled)
        return shuffled
    
    
    def soft_shuffle(self, files, seed_value, intensity=0.2):
        """Перемешивание с небольшими изменениями"""
        random.seed(abs(self.stable_hash(str(seed_value))))
        files = files.copy()
        
        # Количество перестановок = 30% от числа треков (можно регулировать)
        num_swaps = max(1, int(len(files) * intensity))
        
        for _ in range(num_swaps):
            i, j = random.sample(range(len(files)), 2)
            files[i], files[j] = files[j], files[i]
        
        return files
        
if __name__ == "__main__":
    
    # Устанавливаем обработчик исключений ДО всего остального
    sys.excepthook = handle_exception
    
    # Проверяем режим отладки
    debug_mode = is_shift_pressed() or not getattr(sys, 'frozen', False)
    
    if debug_mode:
        setup_console()
        print("===========================================")
        print("    Playlist Generator v4.3 by VolfLife    ")
        print("                                           ")
        print("   github.com/VolfLife/Playlist-Generator  ")
        print("                                           ")
        print("====== : РЕЖИМ ОТЛАДКИ АКТИВИРОВАН : ======")
        print(f"Аргументы: {sys.argv}")
    
    
    
    try:
        # Проверяем зажат ли Shift ИЛИ это не собранный exe
        if is_shift_pressed() or not getattr(sys, 'frozen', False):
            setup_console()
        
        # Теперь все print() будут выводиться в консоль
        print("Программа запущена с аргументами:", sys.argv)
    except Exception as e:
        print(f"ОШИБКА: {str(e)}", file=sys.stderr)
        if 'is_shift_pressed' in globals() and is_shift_pressed():
            import traceback
            traceback.print_exc()
        messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")
        sys.exit(1)
        
    root = tk.Tk()
    
    # Получаем все переданные файлы (игнорируем первый аргумент - это путь к скрипту)
    file_paths = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Если переданы файлы, открываем редактор
    if file_paths and any(fp.lower().endswith(('.m3u8', '.m3u', '.txt')) for fp in file_paths):
        root.withdraw()  # Скрываем основное окно генератора
        editor_root = tk.Tk()
        PlaylistEditor(editor_root, file_paths)
        root.destroy()  # Закрываем генератор
        editor_root.mainloop()
    else:
        # Иначе открываем генератор
        app = PlaylistGenerator(root, file_paths[0] if file_paths else None)
        root.mainloop()
    
