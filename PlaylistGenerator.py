import os
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




class PlaylistGenerator:
    def __init__(self, root, file_to_open=None):
        self.root = root
        self.localization = Localization()
        self.last_folder = ""
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
    
        if self.last_folder:
            self.folder_entry.insert(0, self.last_folder)
                
    
    def is_valid_folder(self, path):
        """Проверяет, существует ли папка, с обработкой возможных ошибок"""
        if not path:  # Если путь пустой
            return False
    
        try:
            return os.path.isdir(path)
        except (OSError, TypeError):
            # Ловим ошибки, связанные с:
            # - некорректными символами в пути
            # - неправильным типом данных
            # - другими системными ошибками доступа
            return False
        
    def show_version_info(self):
        from version_info import version_info
        version_label = tk.Label(
            self.root, 
            text=f"{version_info['product_name']} v{version_info['version']} by {version_info['author']}",
            fg="gray"
        )
        version_label.grid(row=8, column=0, columnspan=3, pady=5)
    
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
            
    
    def create_widgets(self):
        # Настройка сетки для растягивания
        self.root.grid_columnconfigure(1, weight=1)
        
        # Метки и поля ввода
        tk.Label(self.root, text=self.localization.tr("music_folder_label")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.folder_entry = tk.Entry(self.root, width=40)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        tk.Button(self.root, text=self.localization.tr("browse_button"), command=self.browse_folder).grid(row=0, column=2, padx=5, pady=10)
        
        tk.Label(self.root, text=self.localization.tr("playlist_name_label")).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.playlist_entry = tk.Entry(self.root, width=40)
        self.playlist_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.playlist_entry.insert(0, self.localization.tr("default_playlist_name")) # Добавляем значение по умолчанию
        
        
        tk.Label(self.root, text=self.localization.tr("seed_label")).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.seed_entry = tk.Entry(self.root, width=40)
        self.seed_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Поле для шага реверса
        tk.Label(self.root, text=self.localization.tr("reverse_step_label")).grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.step_entry = tk.Entry(self.root, width=40)
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
        self.shadow_seed_check = tk.Checkbutton(
            self.root, 
            text=self.localization.tr("shadow_seed_check"),
            variable=self.use_shadow_seed,
            command=self.toggle_step_entry
        )
        self.shadow_seed_check.grid(row=5, column=0, columnspan=3, pady=5)
        
        # Выбор языка
        language_frame = tk.Frame(self.root)
        language_frame.grid(row=6, column=0, columnspan=3, pady=5, sticky="ew")
    
        tk.Label(language_frame, text=self.localization.tr("language_label")).pack(side=tk.LEFT, padx=(10, 5))
    
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
        
        tk.Button(self.root, text=self.localization.tr("generate_button"), command=self.generate_playlist).grid(row=6, column=1, pady=5)
        
        # Поле для вывода информации
        self.seed_info = tk.Label(self.root, text="", fg="green")
        self.seed_info.grid(row=7, column=0, columnspan=3, pady=5)
    
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
    
        if new_lang != self.localization.current_lang:
            self.localization.set_language(new_lang)
            self.save_language_settings()
            # Обновляем заголовок окна
            self.root.title(self.localization.tr("window_title_generator"))
            # Обновляем остальной интерфейс
            self.update_ui_texts()
        
            # Обновляем список форматов сида
            self.seed_format['values'] = self.localization.get_seed_format_options()
            self.seed_format.current(0)
        
            # Обновляем имя плейлиста по умолчанию
            self.playlist_entry.delete(0, tk.END)
            self.playlist_entry.insert(0, self.localization.tr("default_playlist_name"))
    
    def update_ui_texts(self):
        """Обновляет все тексты в интерфейсе"""
        widgets_to_update = [
            (0, 0, "music_folder_label"),
            (0, 2, "browse_button"),
            (1, 0, "playlist_name_label"),
            (2, 0, "seed_label"),
            (3, 0, "reverse_step_label"),
            (4, 0, "seed_format_label"),
            (5, 0, "shadow_seed_check"),
            (6, 1, "generate_button"),
            (6, 0, "language_label")  # Для label в language_frame
        ]
        
        for row, col, key in widgets_to_update:
            widget = self.root.grid_slaves(row=row, column=col)[0]
            if isinstance(widget, (tk.Label, tk.Button, tk.Checkbutton)):
                widget.config(text=self.localization.tr(key))
        
        # Обновляем значения в Combobox
        self.seed_format['values'] = self.localization.tr("seed_formats")
        self.seed_format.current(0)
        

    def toggle_step_entry(self):
        """Блокировка/разблокировка поля шага реверса"""
        if self.use_shadow_seed.get():
            self.step_entry.config(state='disabled')
            self.step_entry.delete(0, tk.END)
            self.step_entry.insert(0, "0")
        else:
            self.step_entry.config(state='normal')

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        settings = {
            'language': self.localization.current_lang,
            'last_folder': self.last_folder
        }
        if folder_selected:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_selected)
            
            settings['last_folder'] = self.folder_entry.get()
            
            with open('playlist_settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
    
    def load_settings(self):
        """Загружает все настройки из файла, включая язык и последнюю папку"""
        try:
            settings = {
                'language': self.localization.current_lang,
                'last_folder': self.last_folder
            }
            
            with open('playlist_settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
                # 1. Пробуем загрузить сохраненный язык
                saved_lang = settings.get('language')
                if saved_lang and self.localization.is_language_supported(saved_lang):
                    self.localization.set_language(saved_lang)
                else:
                    # 2. Если нет файла или язык не поддерживается, определяем язык системы
                    sys_lang = self.localization.detect_system_language()
                    self.localization.set_language(sys_lang)
                    # Сохраняем новый язык
                    self.save_settings()
                
                # 2. Загружаем последнюю папку (с проверкой существования)
                self.last_folder = settings.get('last_folder', '')
                if self.last_folder and not self.is_valid_folder(self.last_folder):
                    self.last_folder = ""  # Сбрасываем если папка не существует
                if 'last_folder' in settings:
                    settings['last_folder'] = os.path.normpath(settings['last_folder'])
                return settings
                
        except (FileNotFoundError, json.JSONDecodeError):
            # 3. Если файла нет вообще, используем язык системы и сохраняем
            sys_lang = self.localization.detect_system_language()
            self.localization.set_language(sys_lang)
            self.last_folder = ""
            self.save_settings()
    
    def save_settings(self):
        """Сохраняет все настройки в файл"""
        settings = {
            'language': self.localization.current_lang,
            'last_folder': self.last_folder
        }
        try:
            with open('playlist_settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(self.localization.tr("error_save_settings").format(error=e))
    
    
    def stable_hash(self, s):
        """Детерминированная замена hash() с использованием hashlib"""
        return int(hashlib.md5(str(s).encode()).hexdigest(), 16) % (10**12)
       
    
    def generate_playlist(self):
        music_folder = self.folder_entry.get()
        playlist_name = self.playlist_entry.get()
        user_seed = self.seed_entry.get()
        step_value = self.step_entry.get()
    
    # Валидация ввода
        if not music_folder:
            self.seed_info.config(text=self.localization.tr("error_no_music_folder"), fg="red")
            return

        if not playlist_name:
            self.seed_info.config(text=self.localization.tr("error_no_playlist_name"), fg="red")
            return

        if not self.is_valid_folder(music_folder):
            self.seed_info.config(text=self.localization.tr("error_folder_not_exist"), fg="red")
            return
    
        step = 0  # Значение по умолчанию (реверс выключен)
        if step_value.strip():  # Если поле не пустое
            try:
                step = int(step_value)
                if step < 0 or step > 20:
                    raise ValueError
            except ValueError:
                self.seed_info.config(text=self.localization.tr("error_reverse_step"), fg="red")
                return
    
        audio_files = self.get_audio_files(music_folder)
        if not audio_files:
            self.seed_info.config(text=self.localization.tr("error_no_audio_files"), fg="red")
            return
    
        num_tracks = len(audio_files)
        total_size = sum(os.path.getsize(f) for f in audio_files)
        now = datetime.datetime.now()
    
        # Новая логика генерации сидов
        if not user_seed or user_seed == "0":
            # Автоматическая генерация основного сида на основе количества треков
            base_length = math.ceil(math.log2(num_tracks + 1))           
            seed_length = min(max(1, base_length), base_length)
            seed = self.generate_seed(num_tracks=num_tracks, date=now, length=seed_length)
        else:
            # Используем пользовательский сид без ограничения длины
            seed = user_seed  # Теперь сохраняем как строку
        
        # Теневой сид генерируется на основе основного без ограничений
        try:
            seed_num = int(seed) if seed.isdigit() else abs(self.stable_hash(seed))
        except:
            seed_num = abs(self.stable_hash(seed))
            
        shadow_seed = (seed_num * 12345 + 67890 * total_size)
    
    
        # Определяем путь для сохранения
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        playlist_path = os.path.join(script_dir, f"{playlist_name}.m3u8")

        # Обработка шага реверса
        reverse_step = None  # По умолчанию реверс выключен
        if self.use_shadow_seed.get():
            # Фиксируем генератор случайных чисел по теневому сиду
            random.seed(abs(self.stable_hash(shadow_seed)))
    
            # 1. Определяем шаг реверса (1-5)
            reverse_step = random.randint(1, 20)
    
            # 2. Основное перемешивание по теневому сиду
            shuffled = self.shuffle_files(audio_files, str(shadow_seed))
    
            # 3. Применяем реверс блоков
            shuffled_files = self.apply_reverse_step(shuffled, reverse_step)  # Убрали лишний параметр
            
            info_text = self.localization.tr("seed_info_shadow").format(
                seed=seed, shadow_seed=shadow_seed, step=reverse_step
            )
        elif step > 0:
            # Ручной шаг реверса
            reverse_step = step
            shuffled = self.shuffle_files(audio_files, str(seed))
            shuffled_files = self.apply_reverse_step(shuffled, reverse_step)
            info_text = self.localization.tr("seed_info_step").format(
                seed=seed, step=reverse_step
            )
        else:
            # Без реверса
            random.seed(abs(self.stable_hash(seed)))
            shuffled_files = self.shuffle_files(audio_files, str(seed))
            info_text = self.localization.tr("seed_info_basic").format(seed=seed)
    
        # Создание плейлиста
        self.save_m3u8_playlist(
            path=playlist_path,
            files=shuffled_files,
            name=playlist_name,
            seed=str(seed),
            shadow_seed=shadow_seed,
            num_tracks=num_tracks,
            date=now,
            reverse_step=reverse_step  # Теперь переменная определена
        )
    
        self.last_folder = music_folder
        self.save_settings()
        self.seed_info.config(text=self.localization.tr("playlist_created").format(info=info_text), fg="green")
    
    
    def save_m3u8_playlist(self, path, files, name, seed, shadow_seed, num_tracks, date, reverse_step=None):
        """Создает M3U8 файл плейлиста"""
        date_str = date.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            f.write("#Created by VolfLife's Playlist Generator\n")
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

    def apply_reverse_step(self, files, step):
        """Применяет реверс блоков без повторной фиксации генератора"""
        # Создаем копию списка, чтобы не менять оригинал
        reversed_files = files.copy()
        for i in range(0, len(reversed_files), step):
            reversed_files[i:i+step] = reversed(reversed_files[i:i+step])
        return reversed_files
    
    def get_audio_files(self, folder):
        audio_extensions = {'.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac'}
        audio_files = []
    
        try:
            for root, _, files in os.walk(folder):
                for file in files:
                    if Path(file).suffix.lower() in audio_extensions:
                        full_path = os.path.join(root, file)
                        try:
                            # Проверяем, можно ли открыть файл
                            with open(full_path, 'rb'):
                                pass
                            audio_files.append(full_path)
                        except (IOError, OSError):
                            continue
        except (OSError, UnicodeDecodeError) as e:
            print(self.localization.tr("error_scanning_folder").format(error=e))
            return []
    
        return audio_files
    
    def generate_seed(self, num_tracks, date, length=None):
        """Генерация сида переменной длины на основе треков и даты"""
        date_part = date.strftime("%Y%m%d%H%M%S")
        random_part = random.getrandbits(64)
    
        # Расчет длины сида
        base_length = math.ceil(math.log2(num_tracks + 1))
        seed_length = min(max(1, base_length), num_tracks)
    
        # Генерация хеша
        entropy = f"{num_tracks}{date.timestamp()}{random_part}"
        hash_str = hashlib.sha512(entropy.encode()).hexdigest()
    
        # Форматирование
        format_type = self.seed_format.get()
        if format_type in ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", "Толькі лічбы",
                    "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Chiffres uniquement", "Sólo números", "Apenas números", 
                    "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만"]:
            return ''.join(c for c in hash_str if c.isdigit())[:seed_length]
        return hash_str[:seed_length]
        
       
    
    def shuffle_files(self, files, seed_value):
        """Улучшенное перемешивание с явным указанием сида"""
        random.seed(abs(self.stable_hash(seed_value)))
        shuffled = files.copy()
        random.shuffle(shuffled)
        return shuffled

if __name__ == "__main__":
    print("Аргументы командной строки:", sys.argv)
    root = tk.Tk()
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = PlaylistGenerator(root, file_path)
    root.mainloop()
    
