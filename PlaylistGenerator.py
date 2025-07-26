import os
import atexit
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
import logging
import traceback
import urllib.parse
import xml.sax.saxutils as saxutils
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from FontLoader import FontLoader
from Localization import Localization
from PlaylistEditor import PlaylistEditor 



def is_shift_pressed():
    """Проверяет, зажата ли клавиша Shift при запуске"""
    VK_SHIFT = 0x10
    return ctypes.windll.user32.GetKeyState(VK_SHIFT) & 0x8000

def setup_logging_and_console():
    """Настраивает запись логов в файл и консоль"""
    # Определяем путь для сохранения
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
    log_file = os.path.join(script_dir, 'debug.log')
    
    # Очищаем предыдущий лог-файл
    open(log_file, 'w').close()

    # Создаем класс для дублирования вывода в файл и консоль
    class DualOutput:
        def __init__(self, file, console):
            self.file = file
            self.console = console
            
        def write(self, message):
            self.file.write(message)
            self.file.flush()  # Принудительно записываем в файл сразу
            self.console.write(message)
            self.console.flush()
            
        def flush(self):
            self.file.flush()
            self.console.flush()

    # Настраиваем консоль для вывода (только для Windows)
    if sys.platform == 'win32':
        ctypes.windll.kernel32.AllocConsole()
        # Открываем консольные потоки
        console_out = open('CONOUT$', 'w', encoding='utf-8')
        console_err = open('CONOUT$', 'w', encoding='utf-8')
        
        # Открываем файловые потоки
        file_out = open(log_file, 'a', encoding='utf-8', buffering=1)  # buffering=1 для построчной записи
        file_err = open(log_file, 'a', encoding='utf-8', buffering=1)
        
        # Создаем дублирующие потоки
        sys.stdout = DualOutput(file_out, console_out)
        sys.stderr = DualOutput(file_err, console_err)
    else:
        # Для других ОС просто пишем в файл
        file_out = open(log_file, 'a', encoding='utf-8', buffering=1)
        file_err = open(log_file, 'a', encoding='utf-8', buffering=1)
        sys.stdout = file_out
        sys.stderr = file_err
    
    
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
    def __init__(self, root, file_to_open=None, font_loader=None):
        
        self.debug_mode = is_shift_pressed() or not getattr(sys, 'frozen', False)
        
        if self.debug_mode:
            print("Инициализация PlaylistGenerator")
            print(f"Загружено файлов: {len(file_paths) if file_paths else 0}")
        
        
        self.root = root
        self.font_loader = font_loader if font_loader is not None else FontLoader()
        # Получаем путь к иконке правильно
        self.icon_path = icon_path if icon_path is not None else (
            self.font_loader.icon_ico if hasattr(self.font_loader, 'icon_ico') else None
        )
        print(f"Иконка {self.icon_path}")
        self.localization = Localization()
        self.last_folders = []
        self.visited_github = False
        self.github_link = None
        self.format_m3u8 = "m3u8"  # Строка для хранения формата
        self.format_combobox = None  # Виджет Combobox
        self.formatted_duration = None
        self.load_settings()
        self.root.title(self.localization.tr("window_title_generator"))
        
        self.create_widgets()
        self.show_version_info()
        self.load_time()
        
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
        self.root.minsize(540, 344)
    
        if self.last_folders:
            self.folder_entry.insert(0, self.last_folders)
        
        
        # Обновляем поле ввода с последними папками
        self.update_folder_entry()
        
        try:
            if self.icon_path and os.path.exists(self.icon_path):
                self.root.iconbitmap(self.icon_path)
            else:
                print(f"[WARNING] Файл иконки не найден: {self.icon_path}")
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки иконки: {e}")
    
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
                if saved_format in ["m3u8", "m3u", "txt", "pls", "asx", "xspf", "xspf+url", "json", "wpl", "xml"]:
                    self.format_m3u8 = saved_format
                    print(f"[DEBUG] Загружен формат: {saved_format}")
                else:
                    
                    self.format_m3u8 = "m3u8"
                    print(f"[DEBUG] Неподдерживаемый формат '{saved_format}'. Авто–формат: m3u8")
                    
                    
                if 'last_folders' in settings and isinstance(settings['last_folders'], list):
                    # Оставляем только существующие папки
                    self.last_folders = [f for f in settings['last_folders'] if self.is_valid_folders([f])]
                    print(f"[DEBUG] Выбраны папки: {self.last_folders}")          
                            
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

    def load_time(self):
        # Вызываем подсчет времени для загруженных папок
         if self.last_folders:
            total_seconds = self.time_count(self.last_folders)
            if total_seconds > 0:
                self.formatted_duration = self.format_duration(total_seconds)
                self.seed_info.config(
                    text=self.localization.tr("total_duration").format(duration=self.formatted_duration),
                    fg="green"
                )     
                
                
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
            self.browse_btn.config(text=self.localization.tr("browse_button"))
            self.seed_label.config(text=self.localization.tr("seed_label"))
            self.swaps_label.config(text=self.localization.tr("intensity_label"))
            self.seed_format_label.config(text=self.localization.tr("seed_format_label"))
            self.reverse_label.config(text=self.localization.tr("reverse_step_label"))
            self.shadow_seed_check.config(text=self.localization.tr("shadow_seed_check"))
            self.generate_btn.config(text=self.localization.tr("generate_button"))
            # Обновляем остальной интерфейс
            self.update_ui_texts()
        
            # Обновляем список форматов сида
            self.seed_format['values'] = self.localization.get_seed_format_options()

            
            # Получаем текущее значение формата сида
            current_seed_format = self.seed_format.get()
            # Список форматов, при которых текущее значение не должно меняться
            numeric_formats = ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                            "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "数字のみ", "Kun tal", "Endast siffror", "Vain numerot", "Slegs Syfers", "Chỉ số", "Hanya angka", "Dhigití amháin", "Μόνο αριθμοί", "Само цифри", "Tik skaičiai", "Tikai cipari", "Numri biss", "Само бројки", "Iba číslice", "מספרים בלבד", "எண்கள் மட்டும்", "అంకెలు మాత్రమే", "Nombor sahaja", "ቁጥሮች ብቻ", "Nambari pekee", "Izinombolo kuphela"]
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
        
        self.playlist_entry.bind("<Button-3>", self.clear_playlist_entry)
        
        self.seed_label = tk.Label(self.root, text=self.localization.tr("seed_label"))
        self.seed_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.seed_entry = ttk.Entry(self.root, width=40)
        self.seed_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.seed_entry.bind("<Button-3>", self.clear_seed_entry)

        # Поле для перестановок
        self.swaps_label = tk.Label(self.root, text=self.localization.tr("intensity_label"))
        self.swaps_label.grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.intensity_entry = ttk.Entry(self.root, width=10)
        self.intensity_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.intensity_entry.bind("<Button-3>", self.clear_intensity_entry)

        # Выбор формата сида
        self.seed_format_label = tk.Label(self.root, text=self.localization.tr("seed_format_label"))
        self.seed_format_label.grid(row=3, column=1, sticky="w", padx=85, pady=5)
                

        # Поле для шага реверса
        self.reverse_label = tk.Label(self.root, text=self.localization.tr("reverse_step_label"))
        self.reverse_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.step_entry = ttk.Entry(self.root, width=10)
        self.step_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        self.step_entry.bind("<Button-3>", self.clear_step_entry)

        # Ползунок формата сида
        self.seed_format = ttk.Combobox(self.root, 
                                      values=self.localization.tr("seed_formats"), 
                                      state="readonly")
        self.seed_format.current(0)
        self.seed_format.grid(row=4, column=1, sticky="w", padx=85, pady=5)

        # Чекбокс для теневого сида
        self.use_shadow_seed = tk.BooleanVar()
        self.shadow_seed_check = ttk.Checkbutton(
            self.root, 
            text=self.localization.tr("shadow_seed_check"),
            variable=self.use_shadow_seed
            #command=self.toggle_step_entry
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
        
        # Добавляем подсказку при наведении курсора для языка
        self.translation_tooltip = tk.Label(self.root, text="Translations are machine-generated \nand may contain errors", 
                                           bg="beige", relief="solid", borderwidth=1)
        self.translation_tooltip.place_forget()
        self.language_dropdown.bind("<Enter>", self.show_translation_tooltip)
        self.language_dropdown.bind("<Leave>", self.hide_translation_tooltip)
        
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
            values=["m3u8", "m3u", "pls", "wpl", "asx", "xspf", "xspf+url", "json", "xml", "txt"],
            state="readonly",
            width=8
        )

        self.format_combobox.pack(side=tk.LEFT)
        self.format_combobox.set(self.format_m3u8)
        self.format_combobox.bind("<<ComboboxSelected>>", self.change_format)
        
        # Поле для вывода информации
        self.seed_info = tk.Label(self.root, text="", fg="green", bg=self.root.cget('bg'))
        self.seed_info.grid(row=8, column=0, columnspan=3, pady=5)

        # Добавляем подсказку при наведении курсора для сида
        self.seed_tooltip = tk.Label(self.root, text="0=off, 1=auto, 2-∞", 
                                           bg="beige", relief="solid", borderwidth=1)
        self.seed_tooltip.place_forget()
        self.seed_entry.bind("<Enter>", self.show_seed_tooltip)
        self.seed_entry.bind("<Leave>", self.hide_seed_tooltip)
  
        # Добавляем подсказку при наведении курсора для перестановок
        self.swaps_tooltip = tk.Label(self.root, text="0=off, 1=auto, 2-∞", 
                                           bg="beige", relief="solid", borderwidth=1)
        self.swaps_tooltip.place_forget()
        self.intensity_entry.bind("<Enter>", self.show_swaps_tooltip)
        self.intensity_entry.bind("<Leave>", self.hide_swaps_tooltip)
  
        # Добавляем подсказку при наведении курсора для реверса
        self.reverse_tooltip = tk.Label(self.root, text="0=off, 1=auto, 2-∞", 
                                           bg="beige", relief="solid", borderwidth=1)
        self.reverse_tooltip.place_forget()
        self.step_entry.bind("<Enter>", self.show_reverse_tooltip)
        self.step_entry.bind("<Leave>", self.hide_reverse_tooltip)
        
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
    
    def show_translation_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = " Translations are machine-generated \nand may contain errors"
        self.translation_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.translation_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.language_dropdown.winfo_x()  # Позиция поля ввода
        entry_width = self.language_dropdown.winfo_width()  # Ширина поля
        tooltip_width = self.translation_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + (entry_width - tooltip_width) // 2
        y = self.language_dropdown.winfo_y() + 172  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.translation_tooltip.place(x=x, y=y)

    def hide_translation_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'translation_tooltip'):
            self.translation_tooltip.place_forget()

    def show_seed_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = " 0-∞, empty=random "
        self.seed_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.seed_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.seed_entry.winfo_x()  # Позиция поля ввода
        entry_width = self.seed_entry.winfo_width()  # Ширина поля
        tooltip_width = self.seed_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + (entry_width - tooltip_width) // 2
        y = self.seed_entry.winfo_y() + 20  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.seed_tooltip.place(x=x, y=y)

    def hide_seed_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'seed_tooltip'):
            self.seed_tooltip.place_forget()

    def show_swaps_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = " empty=off, 1=auto, 2-∞ "
        self.swaps_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.swaps_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.intensity_entry.winfo_x()  # Позиция поля ввода
        entry_width = self.intensity_entry.winfo_width()  # Ширина поля
        tooltip_width = self.swaps_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + (entry_width - tooltip_width) // 2
        y = self.intensity_entry.winfo_y() + 20  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.swaps_tooltip.place(x=x, y=y)

    def hide_swaps_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'swaps_tooltip'):
            self.swaps_tooltip.place_forget()
    
    def show_reverse_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = " empty=off, 1=auto, 2-∞ "
        self.reverse_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.reverse_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.step_entry.winfo_x()  # Позиция поля ввода
        entry_width = self.step_entry.winfo_width()  # Ширина поля
        tooltip_width = self.reverse_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + (entry_width - tooltip_width) // 2
        y = self.step_entry.winfo_y() + 20  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.reverse_tooltip.place(x=x, y=y)

    def hide_reverse_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'reverse_tooltip'):
            self.reverse_tooltip.place_forget()
    
    
    def clear_playlist_entry(self, event=None):
        self.playlist_entry.delete(0, tk.END)

    def clear_seed_entry(self, event=None):
        self.seed_entry.delete(0, tk.END)
    
    def clear_step_entry(self, event=None):
        self.step_entry.delete(0, tk.END)
    
    def clear_intensity_entry(self, event=None):
        self.intensity_entry.delete(0, tk.END)


    def clear_folder_entry(self, event=None):
        # Очищаем поле ввода и список папок, сохраняем настройки
        self.folder_entry.delete(0, tk.END)
        self.last_folders = []
        self.save_settings()
        self.hide_folder_entry_tooltip()
        self.seed_info.config(
                        text="",
                        fg="green"
                    )
        print(f"[DEBUG] Поле ввода очищена")
        
    def update_ui_texts(self):
        """Обновляет все тексты в интерфейсе"""
        # Обновляем language_label
        self.language_label.config(text=self.localization.tr("language_label"))
        
        widgets_to_update = [
            (0, 0, "music_folder_label"),
            (0, 2, "browse_button"),
            (1, 0, "playlist_name_label"),
            (2, 0, "language_label") # Для label в language_frame   
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
            # Вызываем подсчет времени для ВСЕХ выбранных папок
            if self.last_folders:
                total_seconds = self.time_count(self.last_folders)  # Передаем все папки, а не только последнюю
                if total_seconds > 0:
                    self.formatted_duration = self.format_duration(total_seconds)
                    self.seed_info.config(
                        text=self.localization.tr("total_duration").format(duration=self.formatted_duration),
                        fg="green"
                    )
                print(f"[DEBUG] Общая продолжительность: {self.formatted_duration}")
            self.save_settings()


    def format_duration(self, total_seconds):
        """Форматирует продолжительность в формате Y:M:W:D:H:M:S, пропуская нулевые значения"""
        # Константы времени
        MINUTE = 60
        HOUR = 60 * MINUTE
        DAY = 24 * HOUR
        WEEK = 7 * DAY
        MONTH = 30 * DAY  # Упрощенное значение
        YEAR = 365 * DAY   # Упрощенное значение
        
        # Вычисляем каждую единицу времени
        years = int(total_seconds // YEAR)
        remaining = total_seconds % YEAR
        
        months = int(remaining // MONTH)
        remaining %= MONTH
        
        weeks = int(remaining // WEEK)
        remaining %= WEEK
        
        days = int(remaining // DAY)
        remaining %= DAY
        
        hours = int(remaining // HOUR)
        remaining %= HOUR
        
        minutes = int(remaining // MINUTE)
        seconds = remaining % MINUTE
        
        # Собираем только значимые значения
        parts = []
        if years > 0:
            parts.append(f"{years}")
        if months > 0 or parts:  # Добавляем месяцы если есть годы
            parts.append(f"{months}")
        if weeks > 0 or parts:  # Добавляем недели если есть более крупные единицы
            parts.append(f"{weeks}")
        if days > 0 or parts:
            parts.append(f"{days}")
        if hours > 0 or parts:
            parts.append(f"{hours:02d}")
        if minutes > 0 or parts:
            parts.append(f"{minutes:02d}")
        
        # Секунды всегда добавляем с двумя знаками после запятой
        parts.append(f"{seconds:05.2f}")  # Формат 35.00
        
        # Объединяем части через двоеточие
        formatted = ":".join(parts)
        
        # Для случаев, когда продолжительность меньше минуты
        if "H" not in formatted and "M" not in formatted and "S" in formatted:
            # Формат MM:SS.00 (например 35.00 -> 00:35.00)
            seconds_only = float(formatted.replace("S", ""))
            minutes_part = int(seconds_only // 60)
            seconds_part = seconds_only % 60
            formatted = f"{minutes_part:02d}:{seconds_part:05.2f}"
        elif "H" not in formatted and "M" in formatted and "S" in formatted:
            # Формат MM:SS.00 (например 17M:35.00S -> 17:35.00)
            m_part = formatted.split("M")[0]
            s_part = formatted.split(":")[-1].replace("S", "")
            formatted = f"{int(m_part):02d}:{float(s_part):05.2f}"
        
        return formatted

    def time_count(self, folders):
        """Подсчитывает общую продолжительность аудиофайлов в выбранных папках (в секундах)"""
        from mutagen import File
        from mutagen.flac import FLAC
        from mutagen.mp3 import MP3
        from mutagen.ogg import OggFileType
        from mutagen.wave import WAVE
        from mutagen.aiff import AIFF
        from mutagen.mp4 import MP4
        from mutagen.asf import ASF
        
        total_seconds = 0.0
        audio_extensions = {
                # Аудио
                '.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.wma', '.opus', '.aiff', '.aif', '.alac', '.dsf', '.dff', '.mka', '.ac3', '.dts',
                # Видео
                '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.3gp', '.vob', '.ogv'
            }
        
        for folder in folders:  # Обрабатываем каждую папку в списке
            try:
                for root, _, files in os.walk(folder):
                    for file in files:
                        if Path(file).suffix.lower() in audio_extensions:
                            full_path = os.path.join(root, file)
                            try:
                                audio = File(full_path)
                                if audio and hasattr(audio, 'info'):
                                    total_seconds += audio.info.length
                            except Exception as e:
                                print(f"[WARNING] Ошибка чтения {file}: {e}")
            except (OSError, UnicodeDecodeError) as e:
                print(f"[ERROR] Ошибка сканирования {folder}: {e}")
            
        return total_seconds

    
    def stable_hash(self, s):
        """Детерминированная замена hash() с использованием hashlib"""
        return int(hashlib.md5(str(s).encode()).hexdigest(), 16) % (10**12)
    

    def get_audio_files(self, folders):
        """Принимает список папок, возвращает общий список аудиофайлов всех папок"""
        audio_extensions = {
                # Аудио
                '.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.wma', '.opus', '.aiff', '.aif', '.alac', '.dsf', '.dff', '.mka', '.ac3', '.dts',
                # Видео
                '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.3gp', '.vob', '.ogv'
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
                            "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "数字のみ", "Kun tal", "Endast siffror", "Vain numerot", "Slegs Syfers", "Chỉ số", "Hanya angka", "Dhigití amháin", "Μόνο αριθμοί", "Само цифри", "Tik skaičiai", "Tikai cipari", "Numri biss", "Само бројки", "Iba číslice", "מספרים בלבד", "எண்கள் மட்டும்", "అంకెలు మాత్రమే", "Nombor sahaja", "ቁጥሮች ብቻ", "Nambari pekee", "Izinombolo kuphela"]:
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
        
        # Выбираем подходящий делитель
        random_divisor = random.choice(number)
        if random_divisor == 0 or (random_divisor > random_part and random_divisor != 1):
            random_divisor = max([x for x in number if x <= random_part])
        
        result = (random_part // random_divisor)
        
        seed_num = int((seed_trimmed), 16) if isinstance(seed_trimmed, str) else seed_trimmed
        
        predictable_num = (seed_num + result + 1) % fact
        
        
        print(f"[DEBUG] ГЕНЕРАЦИЯ ТЕНЕВОГО СИДА \n=================================================================== \n Количество треков = {num_tracks} \n Случайное число = {random_part} \n Делитель = {random_divisor} \n Разность = {result} \n Основной сид = {seed_num} \n Результат = {predictable_num}")
        # Форматируем аналогично основному сиду
        if self.seed_format.get() in ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                            "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "数字のみ", "Kun tal", "Endast siffror", "Vain numerot", "Slegs Syfers", "Chỉ số", "Hanya angka", "Dhigití amháin", "Μόνο αριθμοί", "Само цифри", "Tik skaičiai", "Tikai cipari", "Numri biss", "Само бројки", "Iba číslice", "מספרים בלבד", "எண்கள் மட்டும்", "అంకెలు మాత్రమే", "Nombor sahaja", "ቁጥሮች ብቻ", "Nambari pekee", "Izinombolo kuphela"]:
            return str(predictable_num).zfill(len(str(fact)))
        else:
            # Для буквенно-цифрового формата используем хеш
            hash_obj = hashlib.sha256(str(predictable_num).encode())
            return hash_obj.hexdigest()[:len(str(fact))]
        
        
        
    def generate_playlist(self, num_swaps=None):
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
                if step < 0:
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
        
        print(f"[DEBUG] Основной сид = {seed}")
        print(f"[DEBUG] Использованный основной сид = {seed_trimmed}")
        
        
        # Генерируем теневой сид
        if self.use_shadow_seed.get():
            shadow_seed = self.generate_shadow_seed(num_tracks, seed_trimmed)
            print(f"[DEBUG] Теневой сид = {shadow_seed} ")
            # Обрезаем нули
            shadow_seed_trimmed = shadow_seed.lstrip('0') or '0'
            print(f"[DEBUG] Использованный теневой сид = {shadow_seed_trimmed}")
        else:
            shadow_seed = None
            shadow_seed_trimmed = None
        

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
        if step == 1:       
            # Определяем шаг реверса (1-20)
            reverse_step = random.randint(2, 21)
            print(f"[DEBUG] Реверс = {reverse_step}")
            
            if self.use_shadow_seed.get():
                seed_trimmed = shadow_seed_trimmed
                # Основное перемешивание по теневому сиду
                shuffled, num_swaps = self.soft_shuffle(audio_files, str(shadow_seed_trimmed))
                shuffled_files = self.apply_reverse_step(shuffled, reverse_step)
            
                if num_swaps:
                    info_text = self.localization.tr("seed_info_shadow_intensity_step").format(
                        shadow_seed=shadow_seed_trimmed, step=reverse_step, num_swaps=num_swaps
                    )
                else:
                    info_text = self.localization.tr("seed_info_shadow_step").format(
                        shadow_seed=shadow_seed_trimmed, step=reverse_step
                    )
            else:
            
                # Основное перемешивание по основному сиду
                shuffled, num_swaps = self.soft_shuffle(audio_files, str(seed_trimmed))
            
                # Применяем реверс блоков
                shuffled_files = self.apply_reverse_step(shuffled, reverse_step)
                
                if num_swaps:
                    info_text = self.localization.tr("seed_info_intensity_step").format(
                        seed=seed_trimmed, step=reverse_step, num_swaps=num_swaps
                    )
                else:
                    info_text = self.localization.tr("seed_info_step").format(
                        seed=seed_trimmed, step=reverse_step
                    )
            
            print(f"[DEBUG] : Перестановленный список (Теневой сид + {reverse_step}) ============================")
            for i, path in enumerate(shuffled_files, 1):
                print(f"{i}. {os.path.basename(path)}")
            print("===================================================================")
            
        elif step > 0:
            # Ручной шаг реверса
            reverse_step = step
            print(f"[DEBUG] Реверс = {reverse_step}")
            
            if self.use_shadow_seed.get():
                shuffled, num_swaps = self.soft_shuffle(audio_files, str(shadow_seed_trimmed))
                shuffled_files = self.apply_reverse_step(shuffled, reverse_step)
                
                if num_swaps:
                    info_text = self.localization.tr("seed_info_shadow_intensity_step").format(
                        shadow_seed=shadow_seed_trimmed, step=reverse_step, num_swaps=num_swaps
                    )
                else:
                    info_text = self.localization.tr("seed_info_shadow_step").format(
                        shadow_seed=shadow_seed_trimmed, step=reverse_step
                    )
                
            else:
                shuffled, num_swaps = self.soft_shuffle(audio_files, str(seed_trimmed))
                shuffled_files = self.apply_reverse_step(shuffled, reverse_step)
            
                if num_swaps:
                    info_text = self.localization.tr("seed_info_intensity_step").format(
                        seed=seed_trimmed, step=reverse_step, num_swaps=num_swaps
                    )
                else:
                    info_text = self.localization.tr("seed_info_step").format(
                        seed=seed_trimmed, step=reverse_step
                    )
            
            print(f"[DEBUG] : Новый список с реверсом {reverse_step} ============================")
            for i, path in enumerate(shuffled_files, 1):
                print(f"{i}. {os.path.basename(path)}")
            print("===================================================================")
            
        else:
            # Без реверса
            if self.use_shadow_seed.get():
                shuffled_files, num_swaps = self.soft_shuffle(audio_files, str(shadow_seed_trimmed))
                
                if num_swaps:
                    info_text = self.localization.tr("seed_info_shadow_intensity").format(
                        shadow_seed=shadow_seed_trimmed, num_swaps=num_swaps
                    )
                else:
                    info_text = self.localization.tr("seed_info_shadow").format(
                        shadow_seed=shadow_seed_trimmed
                    )
                
            else:
                shuffled_files, num_swaps = self.soft_shuffle(audio_files, str(seed_trimmed))
                
                if num_swaps:
                    info_text = self.localization.tr("seed_info_intensity").format(
                        seed=seed_trimmed, num_swaps=num_swaps
                    )
                else:
                    info_text = self.localization.tr("seed_info_basic").format(
                        seed=seed_trimmed
                    )
            
            
            print(f"[DEBUG] : Новый список ============================")
            for i, path in enumerate(shuffled_files, 1):
                print(f"{i}. {os.path.basename(path)}")
            print("===================================================================")
        
        print(f"[SUCCES] Перемешивание завершено")
       
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
            num_swaps=num_swaps,
            playlist_format=playlist_format
        )

        self.last_folder = valid_paths
        self.save_settings()
        self.seed_info.config(text=self.localization.tr("playlist_created").format(info=info_text), fg="green")
       
       
    def soft_shuffle(self, files, seed_value):
        """Перемешивание с небольшими изменениями"""
        seed_hash = abs(self.stable_hash(str(seed_value)))
        random.seed(seed_hash)
        files = files.copy()
        
        print(f"[DEBUG] : Текущий список ============================")
        for i, path in enumerate(files, 1):
            print(f"{i}. {os.path.basename(path)}")
        print("===================================================================")
        
        random.shuffle(files)
        
        print(f"[DEBUG] : Перемешанный список ============================")
        for i, path in enumerate(files, 1):
            print(f"{i}. {os.path.basename(path)}")
        print("===================================================================")
            
            
        # Обработка шага реверса
        intensity_value = self.intensity_entry.get()
        intensity = 0
        num_swaps = 0
        if intensity_value.strip():
            try:
                intensity = int(intensity_value)
                if intensity < 0:
                    raise ValueError
            except ValueError:
                self.seed_info.config(text=self.localization.tr("error_intensity"), fg="red")
                return            

            
        # Генерация intensity из сида, если не задано
        if intensity != 0 and intensity is None:
            return files, num_swaps

        elif intensity == 1:
            # Используем хеш сида для генерации значения 0.6-1.0
            hash_val = (seed_hash % 10_000_000_000) / 10_000_000_000
            intensity = 0.6 + 0.4 * hash_val  # Растягиваем на диапазон 0.6-1.0
            
            # Количество перестановок = 30% от числа треков (можно регулировать)
            num_swaps = min(int(len(files) * intensity * 1.07), int(len(files)))
            print(f"[DEBUG] Генерация intensity из сида = {intensity}")
            print(f"[DEBUG] Количество перестановок = {num_swaps}")
            for _ in range(num_swaps):
                i, j = random.sample(range(len(files)), 2)
                files[i], files[j] = files[j], files[i]
                print(f"[DEBUG] Перемешано {i}<->{j}")
            return files, num_swaps          

        else:
                
            # Количество перестановок = 30% от числа треков (можно регулировать)
            num_swaps = int(intensity)
            print(f"[DEBUG] Генерация intensity из сида = {intensity}")
            print(f"[DEBUG] Количество перестановок = {num_swaps}")
            for _ in range(num_swaps):
                i, j = random.sample(range(len(files)), 2)
                files[i], files[j] = files[j], files[i]
                print(f"[DEBUG] Перемешано {i}<->{j}")
            return files, num_swaps
        
        
    
    def save_m3u8_playlist(self, path, files, name, seed, shadow_seed, num_tracks, date, reverse_step=None, num_swaps=None, playlist_format=None):
        """Создает M3U8 файл плейлиста"""
        date_str = date.strftime("%Y-%m-%d %H:%M:%S")
        if playlist_format in ["m3u8", "m3u"]:      
            with open(path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write("#Made with VolfLife's Playlist Generator\n")
                f.write(f"#GENERATED:{date_str}\n")
                f.write(f"#PLAYLIST:{name}\n")
                if self.formatted_duration is not None:
                    f.write(f"#DURATION:{self.formatted_duration}\n")
                f.write(f"#SEED:{seed}\n")
                if self.use_shadow_seed.get():
                    f.write(f"#SHADOW_SEED:{shadow_seed}\n")
                
                if num_swaps is not None and num_swaps > 0:
                    f.write(f"#NUM_SWAPS:{num_swaps}\n")
                if reverse_step is not None and reverse_step > 0:
                    f.write(f"#REVERSE_STEP:{reverse_step}\n")
                    
                f.write(f"#TRACKS:{num_tracks}\n")

                f.write("\n")  # Разделитель
                
                for file_path in files:
                    # Нормализуем путь
                    clean_path = os.path.normpath(file_path)
                    
                    # Получаем имя файла
                    file_name = os.path.basename(clean_path)
                    name_without_ext = os.path.splitext(file_name)[0]
                    
                    
                    f.write(f"#EXTINF:-1,{saxutils.escape(name_without_ext)}\n")
                    f.write(f"{clean_path.replace('\\', '/')}\n")
            print(f"[DEBUG] Плейлист создан и сохранен: {name}.{playlist_format}")        
        
        if playlist_format in ["txt"]:      
            with open(path, 'w', encoding='utf-8') as f:
                f.write("#Made with VolfLife's Playlist Generator\n")
                f.write(f"#GENERATED:{date_str}\n")
                f.write(f"#TRACKLIST:{name}\n")
                if self.formatted_duration is not None:
                    f.write(f"#DURATION:{self.formatted_duration}\n")                
                f.write(f"#SEED:{seed}\n")
                if self.use_shadow_seed.get():
                    f.write(f"#SHADOW_SEED:{shadow_seed}\n")
                
                if num_swaps is not None and num_swaps > 0:
                    f.write(f"#NUM_SWAPS:{num_swaps}\n")    
                if reverse_step is not None and reverse_step > 0:
                    f.write(f"#REVERSE_STEP:{reverse_step}\n")
                
                f.write(f"#TRACKS:{num_tracks}\n")

                f.write("\n")  # Разделитель
                
                for file_path in files:
                    file_path = os.path.normpath(file_path)
                    escaped_path = file_path.replace('\\', '/')
                    f.write(f"{escaped_path}\n")
            print(f"[DEBUG] Треклист создан и сохранен: {name}.{playlist_format}") 
        
        if playlist_format in ["pls"]:
            with open(path, 'w', encoding='utf-8') as f:
                # Заголовок плейлиста
                f.write("[playlist]\n")
                f.write(f";Made with VolfLife's Playlist Generator\n")
                f.write(f";GENERATED:{date_str}\n")
                f.write(f";PLAYLIST:{name}\n")
                if self.formatted_duration is not None:
                    f.write(f";DURATION:{self.formatted_duration}\n")                
                f.write(f";SEED:{seed}\n")
                if self.use_shadow_seed.get():
                    f.write(f";SHADOW_SEED:{shadow_seed}\n")
                
                if num_swaps is not None and num_swaps > 0:
                    f.write(f";NUM_SWAPS:{num_swaps}\n")    
                if reverse_step is not None and reverse_step > 0:
                    f.write(f";REVERSE_STEP:{reverse_step}\n")
                
                f.write(f"NumberOfEntries={num_tracks}\n")
                f.write("Version=2\n\n")  # Версия формата PLS

                # Запись треков
                for i, file_path in enumerate(files, 1):
                    # Нормализуем путь
                    clean_path = os.path.normpath(file_path)
                    
                    # Получаем имя файла
                    file_name = os.path.basename(clean_path)
                    name_without_ext = os.path.splitext(file_name)[0]
                    
                    f.write(f"File{i}={clean_path.replace('\\', '/')}\n")
                    f.write(f"Title{i}={saxutils.escape(name_without_ext)}\n")
                    f.write(f"Length{i}=-1\n")  # -1 = длительность определит плеер
                    
                    if i < num_tracks:  # Добавляем пустую строку между треками (кроме последнего)
                        f.write("\n")

            print(f"[DEBUG] Плейлист создан и сохранен: {name}.{playlist_format}")
        
        
        if playlist_format in ["asx"]:
            with open(path, 'w', encoding='utf-8') as f:
                # Заголовок ASX
                f.write('<ASX Version="3.0">\n')
                f.write(f'<!-- Generated by VolfLife\'s Playlist Generator on {date_str} -->\n')
                f.write(f'<Title>{saxutils.escape(name)}</Title>\n')
                if self.formatted_duration is not None:
                    f.write(f'<Abstract>DURATION:{self.formatted_duration}</Abstract>\n')
                f.write(f'<Abstract>SEED:{seed}</Abstract>\n')
                if self.use_shadow_seed.get():
                    f.write(f'<Abstract>SHADOW_SEED:{shadow_seed}</Abstract>\n')
                if num_swaps is not None and num_swaps > 0:
                    f.write(f'<Abstract>NUM_SWAPS:{num_swaps}</Abstract>\n')
                if reverse_step is not None and reverse_step > 0:
                    f.write(f'<Abstract>REVERSE_STEP:{reverse_step}</Abstract>\n')
                    
                f.write(f'<Abstract>TRACKS:{num_tracks}</Abstract>\n\n')
                
                # Запись треков
                for file_path in files:
                    clean_path = os.path.normpath(file_path)
                    file_name = os.path.basename(clean_path)
                    name_without_ext = os.path.splitext(file_name)[0]
                    
                    f.write('<Entry>\n')
                    f.write(f'  <Title>{saxutils.escape(name_without_ext)}</Title>\n')
                    f.write(f'  <Ref href="{saxutils.escape(clean_path.replace("\\", "/"))}" />\n')
                    f.write('</Entry>\n\n')
                
                f.write('</ASX>')
            
            print(f"[DEBUG] Плейлист создан и сохранен: {name}.{playlist_format}")
        
        
        if playlist_format in ["xspf"]:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<playlist version="1" xmlns="http://xspf.org/ns/0/">\n')
                f.write(f'  <title>{name}</title>\n')
                f.write('  <creator>VolfLife\'s Playlist Generator</creator>\n')
                f.write(f'  <date>{date_str}</date>\n')
                
                # Метаданные
                f.write('  <annotation>\n')
                f.write(f'    GENERATED:{date_str}\n')
                if self.formatted_duration is not None:
                    f.write(f'    DURATION:{self.formatted_duration}\n')
                f.write(f'    SEED:{seed}\n')
                if self.use_shadow_seed.get():
                    f.write(f'    SHADOW_SEED:{shadow_seed}\n')
                if num_swaps:
                    f.write(f'    NUM_SWAPS:{num_swaps}\n')
                if reverse_step:
                    f.write(f'    REVERSE_STEP:{reverse_step}\n')
                f.write(f'    TRACKS:{num_tracks}\n')
                f.write('  </annotation>\n')
                
                f.write('  <trackList>\n')
                
                for file_path in files:
                    # Нормализуем путь
                    clean_path = os.path.normpath(file_path)
                    
                    # Получаем имя файла
                    file_name = os.path.basename(clean_path)
                    name_without_ext = os.path.splitext(file_name)[0]
                    
                    # Формируем file:// 
                    file_url = clean_path.replace('\\', '/')
                    #file_url = "file:///" + urllib.parse.quote(clean_path.replace('\\', '/'))
                    f.write('    <track>\n')
                    f.write(f'      <location>{file_url}</location>\n')
                    f.write(f'      <title>{saxutils.escape(name_without_ext)}</title>\n')
                    f.write(f'      <meta rel="filename">{saxutils.escape(file_name)}</meta>\n')  # Добавляем оригинальное имя файла
                    f.write('    </track>\n')
                
                f.write('  </trackList>\n')
                f.write('</playlist>\n')
            
            print(f"[DEBUG] Плейлист создан и сохранен: {name}.{playlist_format}")
    
    
        if playlist_format in ["xspf+url"]:
            # Определяем путь для сохранения
            if getattr(sys, 'frozen', False):
                script_dir = os.path.dirname(sys.executable)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
            playlist_format = "xspf"
            path = os.path.join(script_dir, f"{name}.{playlist_format}")
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<playlist version="1" xmlns="http://xspf.org/ns/0/">\n')
                f.write(f'  <title>{name}</title>\n')
                f.write('  <creator>VolfLife\'s Playlist Generator</creator>\n')
                f.write(f'  <date>{date_str}</date>\n')
                
                # Метаданные
                f.write('  <annotation>\n')
                f.write(f'    GENERATED:{date_str}\n')
                if self.formatted_duration is not None:
                    f.write(f'    DURATION:{self.formatted_duration}\n')
                f.write(f'    SEED:{seed}\n')
                if self.use_shadow_seed.get():
                    f.write(f'    SHADOW_SEED:{shadow_seed}\n')
                if num_swaps:
                    f.write(f'    NUM_SWAPS:{num_swaps}\n')
                if reverse_step:
                    f.write(f'    REVERSE_STEP:{reverse_step}\n')
                f.write(f'    TRACKS:{num_tracks}\n')
                f.write('  </annotation>\n')
                
                f.write('  <trackList>\n')
                
                for file_path in files:
                    # Нормализуем путь
                    clean_path = os.path.normpath(file_path)
                    
                    # Получаем имя файла
                    file_name = os.path.basename(clean_path)
                    name_without_ext = os.path.splitext(file_name)[0]
                    
                    # Формируем file:// URL с правильным кодированием
                    file_url = "file:///" + urllib.parse.quote(clean_path.replace('\\', '/'))
                    f.write('    <track>\n')
                    f.write(f'      <location>{file_url}</location>\n')
                    f.write(f'      <title>{saxutils.escape(name_without_ext)}</title>\n')
                    f.write(f'      <meta rel="filename">{saxutils.escape(file_name)}</meta>\n')  # Добавляем оригинальное имя файла
                    f.write('    </track>\n')
                
                f.write('  </trackList>\n')
                f.write('</playlist>\n')
            
            print(f"[DEBUG] Плейлист создан и сохранен: {name}.{playlist_format}")
        
        if playlist_format in ["json"]:          
            from datetime import datetime
            playlist_data = {
                "meta": {
                    "name": name,
                    "duration": self.formatted_duration if self.formatted_duration else None,
                    "generator": "VolfLife's Playlist Generator",
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "seed": seed,
                    "shadow_seed": shadow_seed if self.use_shadow_seed.get() else None,
                    "num_swaps": num_swaps if num_swaps and num_swaps > 0 else None,
                    "reverse_step": reverse_step if reverse_step and reverse_step > 0 else None,
                    "num_tracks": num_tracks
                },
                "tracks": []
            }

            for file_path in files:
                file_path = os.path.normpath(file_path)
                playlist_data["tracks"].append({
                    "path": file_path.replace('\\', '/'),
                    "filename": os.path.basename(file_path),
                    "title": os.path.splitext(os.path.basename(file_path))[0]
                })

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, indent=4, ensure_ascii=False)
            
            print(f"[DEBUG] Плейлист создан и сохранен: {name}.{playlist_format}")
        
        if playlist_format in ["wpl"]:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<?wpl version="1.0"?>\n')
                f.write('<smil>\n')
                f.write('  <head>\n')
                f.write('    <meta name="Generator" content="VolfLife\'s Playlist Generator"/>\n')
                f.write(f'    <meta name="ItemCount" content="{num_tracks}"/>\n')
                f.write(f'    <title>{name}</title>\n')
                
                # Метаданные в виде комментариев (альтернатива для WPL)
                f.write('    <!--\n')
                f.write(f'      GENERATED:{date_str}\n')
                if self.formatted_duration is not None:
                    f.write(f'      DURATION:{self.formatted_duration}\n')
                f.write(f'      SEED:{seed}\n')
                if self.use_shadow_seed.get():
                    f.write(f'      SHADOW_SEED:{shadow_seed}\n')
                if num_swaps:
                    f.write(f'      NUM_SWAPS:{num_swaps}\n')
                if reverse_step:
                    f.write(f'      REVERSE_STEP:{reverse_step}\n')
                f.write('    -->\n')
                
                f.write('  </head>\n')
                f.write('  <body>\n')
                f.write('    <seq>\n')
                
                for file_path in files:
                    # Нормализуем путь и экранируем спецсимволы XML
                    clean_path = os.path.normpath(file_path)
                    escaped_path = saxutils.escape(clean_path.replace('\\', '/'))
                    
                    # Записываем путь к файлу
                    f.write(f'      <media src="{escaped_path}"/>\n')
                
                f.write('    </seq>\n')
                f.write('  </body>\n')
                f.write('</smil>\n')
            
            print(f"[DEBUG] Плейлист создан и сохранен: {name}.{playlist_format}")
    
        
        elif playlist_format == 'xml':
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<playlist version="1" xmlns="http://xspf.org/ns/0/">\n')
                f.write('  <title>{}</title>\n'.format(saxutils.escape(name)))
                f.write('  <creator>VolfLife\'s Playlist Generator</creator>\n')
                f.write('  <date>{}</date>\n'.format(date_str))
                
                # Метаданные
                f.write('  <annotation>\n')
                f.write('    GENERATED:{}\n'.format(date_str))
                if self.formatted_duration is not None:
                    f.write('    DURATION:{}\n'.format(self.formatted_duration))
                f.write('    SEED:{}\n'.format(seed))
                if self.use_shadow_seed.get():
                    f.write('    SHADOW_SEED:{}\n'.format(shadow_seed))
                if num_swaps:
                    f.write('    NUM_SWAPS:{}\n'.format(num_swaps))
                if reverse_step:
                    f.write('    REVERSE_STEP:{}\n'.format(reverse_step))
                f.write('    TRACKS:{}\n'.format(num_tracks))
                f.write('  </annotation>\n')
                
                f.write('  <trackList>\n')
                
                for track_num, file_path in enumerate(files, 1):
                    # Нормализуем путь
                    clean_path = os.path.normpath(file_path)
                    file_name = os.path.basename(clean_path)
                    name_without_ext = os.path.splitext(file_name)[0]
                    
                    f.write('    <track>\n')
                    f.write('      <location>{}</location>\n'.format(
                        urllib.parse.quote(saxutils.escape(clean_path.replace('\\', '/')))))
                    f.write('      <title>{}</title>\n'.format(
                        saxutils.escape(name_without_ext)))
                    f.write('      <meta rel="trackNumber">{}</meta>\n'.format(track_num))
                    f.write('    </track>\n')
                
                f.write('  </trackList>\n')
                f.write('</playlist>\n')
            
            print(f"[DEBUG] Плейлист создан и сохранен: {name}.{playlist_format}")
        
        
        
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
    
    
        
if __name__ == "__main__":
    
    # Устанавливаем обработчик исключений ДО всего остального
    sys.excepthook = handle_exception
    
    # Проверяем режим отладки
    debug_mode = is_shift_pressed() or not getattr(sys, 'frozen', False)
    
    if debug_mode:
        setup_logging_and_console()
        print("===========================================")
        print("    Playlist Generator v4.22 by VolfLife   ")
        print("                                           ")
        print("   github.com/VolfLife/Playlist-Generator  ")
        print("                                           ")
        print("====== : РЕЖИМ ОТЛАДКИ АКТИВИРОВАН : ======")
    
    try:
            
        # Теперь все print() будут выводиться в консоль
        print("Программа запущена с аргументами:", sys.argv)
    except Exception as e:
        print(f"ОШИБКА: {str(e)}", file=sys.stderr)
        if 'is_shift_pressed' in globals() and is_shift_pressed():
            import traceback
            traceback.print_exc()
        messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")
        sys.exit(1)

    try:
                    
        # Получаем все переданные файлы (игнорируем первый аргумент - это путь к скрипту)
        file_paths = sys.argv[1:] if len(sys.argv) > 1 else None
        
        # Если переданы файлы, открываем редактор
        if file_paths and any(fp.lower().endswith(('.m3u8', '.m3u', '.txt', '.pls', '.asx', '.xspf', '.json', '.wax', '.wvx', '.wpl', '.xml')) for fp in file_paths):
            editor_root = tk.Tk()
            font_loader = FontLoader()
            # Проверяем, что иконка загружена
            icon_path = font_loader.icon_ico if font_loader.icon_ico else None
            font_path = font_loader._font_path
            PlaylistEditor(editor_root, file_paths, icon_path, font_path)
            editor_root.mainloop()
        else:
            # Иначе открываем генератор
            root = tk.Tk()
            font_loader = FontLoader()		
            # Проверяем, что иконка загружена
            icon_path = font_loader.icon_ico if font_loader.icon_ico else None
            
            
            if icon_path and not os.path.exists(icon_path):
                print(f"[WARNING] Icon path exists but file not found: {icon_path}")
                icon_path = None
            # Получаем шрифт ТОЛЬКО после создания root окна
            
            app = PlaylistGenerator(root, file_paths[0] if file_paths else None, icon_path)
            root.mainloop()
    except Exception as e:
        print(f"[CRITICAL] Main application error: {str(e)}")
        traceback.print_exc()
        messagebox.showerror("Fatal Error", f"The application failed to start:\n{str(e)}")