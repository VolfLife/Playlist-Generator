import os
import sys
import random
import datetime
import hashlib
import math
import string
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

class PlaylistGenerator:
    def __init__(self, root, file_path=None):
        self.root = root
        self.root.title("Генератор плейлистов")
        self.last_folder = ""
        self.load_settings()
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
    
    def show_version_info(self):
        from version_info import version_info
        version_label = tk.Label(
            self.root, 
            text=f"{version_info['product_name']} v{version_info['version']} | {version_info['author']}",
            fg="gray"
        )
        version_label.grid(row=8, column=0, columnspan=3, pady=5)
    
    def create_widgets(self):
        # Настройка сетки для растягивания
        self.root.grid_columnconfigure(1, weight=1)
        
        # Метки и поля ввода
        tk.Label(self.root, text="Папка с музыкой:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.folder_entry = tk.Entry(self.root, width=40)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        if self.last_folder:
            self.folder_entry.insert(0, self.last_folder)
            
        tk.Button(self.root, text="Обзор", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=10)
        
        tk.Label(self.root, text="Имя плейлиста:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.playlist_entry = tk.Entry(self.root, width=40)
        self.playlist_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.playlist_entry.insert(0, "my_playlist")
        
        tk.Label(self.root, text="Сид (оставьте пустым для случайного):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.seed_entry = tk.Entry(self.root, width=40)
        self.seed_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Поле для шага реверса
        tk.Label(self.root, text="Шаг реверса (0=выкл, 1-20):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.step_entry = tk.Entry(self.root, width=40)
        self.step_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.step_entry.insert(0, "")

        # Выбор формата сида
        tk.Label(self.root, text="Формат сида:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.seed_format = ttk.Combobox(self.root, 
                                      values=["Только цифры", "Цифры и буквы"], 
                                      state="readonly")
        self.seed_format.current(0)
        self.seed_format.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Чекбокс для теневого сида
        self.use_shadow_seed = tk.BooleanVar()
        self.shadow_seed_check = tk.Checkbutton(
            self.root, 
            text="Использовать теневой сид для сложного перемешивания",
            variable=self.use_shadow_seed,
            command=self.toggle_step_entry
        )
        self.shadow_seed_check.grid(row=5, column=0, columnspan=3, pady=5)
        
        # Кнопка генерации
        tk.Button(self.root, text="Создать плейлист", command=self.generate_playlist).grid(row=6, column=1, pady=5)
        
        # Поле для вывода информации
        self.seed_info = tk.Label(self.root, text="")
        self.seed_info.grid(row=7, column=0, columnspan=3, pady=5)

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
        if folder_selected:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_selected)
    
    def load_settings(self):
        try:
            with open('playlist_settings.json', 'r') as f:
                settings = json.load(f)
                self.last_folder = settings.get('last_folder', '')
        except (FileNotFoundError, json.JSONDecodeError):
            self.last_folder = ""
    
    def save_settings(self):
        with open('playlist_settings.json', 'w') as f:
            json.dump({'last_folder': self.last_folder}, f)
    
    def stable_hash(self, s):
        """Детерминированная замена hash() с использованием hashlib"""
        return int(hashlib.md5(str(s).encode()).hexdigest(), 16) % (10**20)
       
    
    def generate_playlist(self):
        music_folder = self.folder_entry.get()
        playlist_name = self.playlist_entry.get()
        user_seed = self.seed_entry.get()
        step_value = self.step_entry.get()
    
    # Валидация ввода
        if not music_folder:
            self.seed_info.config(text="Ошибка: Укажите папку с музыкой!", fg="red")
            return
    
        if not playlist_name:
            self.seed_info.config(text="Ошибка: Укажите имя плейлиста!", fg="red")
            return
    
        if not os.path.isdir(music_folder):
            self.seed_info.config(text="Ошибка: Папка не существует!", fg="red")
            return
    
        step = 0  # Значение по умолчанию (реверс выключен)
        if step_value.strip():  # Если поле не пустое
            try:
                step = int(step_value)
                if step < 0 or step > 20:
                    raise ValueError
            except ValueError:
                self.seed_info.config(text="Ошибка: Шаг реверса должен быть числом от 0 до 20!", fg="red")
                return
    
        audio_files = self.get_audio_files(music_folder)
        if not audio_files:
            self.seed_info.config(text="Ошибка: В указанной папке нет поддерживаемых аудиофайлов!", fg="red")
            return
    
        num_tracks = len(audio_files)
        total_size = sum(os.path.getsize(f) for f in audio_files)
        now = datetime.datetime.now()
    
        # Новая логика генерации сидов
        if not user_seed or user_seed == "0":
            # Автоматическая генерация основного сида на основе количества треков
            seed_length = max(2, min(128, math.ceil(math.log2(num_tracks + 1) * 2)))
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
            
            info_text = f"Основной сид: {seed} \nТеневой сид: {shadow_seed} \nРеверс: {reverse_step}"
        elif step > 0:
            # Ручной шаг реверса
            reverse_step = step
            shuffled = self.shuffle_files(audio_files, str(seed))
            shuffled_files = self.apply_reverse_step(shuffled, reverse_step)
            info_text = f"Основной сид: {seed} | Ручной реверс: {reverse_step}"
        else:
            # Без реверса
            random.seed(abs(self.stable_hash(seed)))
            shuffled_files = self.shuffle_files(audio_files, str(seed))
            info_text = f"Основной сид: {seed}"
    
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
        self.seed_info.config(text=f"Плейлист создан! {info_text}", fg="green")
    
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
        
        return audio_files
    
    def generate_seed(self, num_tracks, date, length=None):
        """Генерация сида переменной длины на основе треков и даты"""
        date_part = date.strftime("%Y%m%d%H%M%S")
        random_part = random.getrandbits(512)
    
        # Расчет длины сида
        base_length = math.ceil(math.log2(num_tracks + 1)) * 2
        max_reasonable_length = 128  # SHA-512 дает максимум 128 символов
        seed_length = min(max(2, base_length), max_reasonable_length, length)  # Учитываем все ограничения
    
        # Генерация хеша
        entropy = f"{num_tracks}{date.timestamp()}{random_part}"
        hash_str = hashlib.sha512(entropy.encode()).hexdigest()
    
        # Форматирование
        format_type = self.seed_format.get()
        if format_type == "Только цифры":
            return ''.join(c for c in hash_str if c.isdigit())[:seed_length]
        return hash_str[:seed_length]
        
       
    
    def shuffle_files(self, files, seed_value):
        """Улучшенное перемешивание с явным указанием сида"""
        random.seed(abs(self.stable_hash(seed_value)))
        shuffled = files.copy()
        random.shuffle(shuffled)
        return shuffled

if __name__ == "__main__":
    root = tk.Tk()
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = PlaylistGenerator(root, file_path)
    root.mainloop()
    
