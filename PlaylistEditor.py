import os
import sys
import random
import datetime
import hashlib
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import string

class PlaylistEditor:
    def __init__(self, root, file_path):
        self.root = root
        self.root.title("Редактор плейлиста")
        self.file_path = file_path
        self.original_paths = []  # Храним оригинальный порядок
        self.full_paths = []      # Текущий порядок
        self.display_names = []
        self.current_seed = ""
        self.current_reverse_step = None
        self.seed_format = "Только цифры"  # По умолчанию
        
        try:
            self.load_playlist()
            self.original_paths = self.full_paths.copy()  # Сохраняем оригинал
            self.create_widgets()
            self.center_window(540, 600)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить плейлист: {str(e)}")
            self.root.destroy()
            raise

    def center_window(self, width, height):
        """Центрирование окна"""
        self.root.resizable(width=False, height=False)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(540, 600)

    def load_playlist(self):
        """Загружает плейлист и устанавливает имя по умолчанию"""
        temp_files = []
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    self.full_paths.append(line)
                    self.display_names.append(os.path.basename(line))
                    temp_files.append(line)

        # Сортируем файлы по именам (без учета регистра)
        temp_files.sort(key=lambda x: os.path.basename(x).lower())
        
        # Заполняем основные списки
        self.full_paths = temp_files
        self.display_names = [os.path.basename(f) for f in temp_files]
        
        # Получаем имя файла без пути и расширения
        filename = os.path.basename(self.file_path)
        if filename.lower().endswith('.m3u8'):
            filename = filename[:-5]  # Удаляем .m3u8
        
        # Удаляем _mixed если уже есть
        if filename.endswith('_mixed'):
            filename = filename[:-6]
        
        # Устанавливаем имя плейлиста
        self.playlist_name = f"{filename}_mixed"

    def stable_hash(self, s):
        """Детерминированная замена hash() с использованием hashlib"""
        return int(hashlib.md5(str(s).encode()).hexdigest(), 16) % (10**20)

    def create_widgets(self):
        """Создает интерфейс редактора"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Фрейм для таблицы с ползунком
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Таблица треков с ползунком
        self.tree = ttk.Treeview(table_frame, columns=('num', 'name'), show='headings')
        self.tree.heading('num', text='№')
        self.tree.heading('name', text='Название трека')
        self.tree.column('num', width=50, anchor='center')
        self.tree.column('name', width=440, anchor='w')
        
        # Вертикальный ползунок
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        for i, name in enumerate(self.display_names, 1):
            self.tree.insert('', 'end', values=(i, name))
        
        # Фрейм для полей ввода
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        # Поле имени плейлиста (увеличенная ширина)
        ttk.Label(input_frame, text="Имя плейлиста:").grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.name_entry = ttk.Entry(input_frame, width=45)  # Увеличенная ширина
        self.name_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.name_entry.insert(0, self.playlist_name)  # Автоматическое заполнение
        
        # Поле сида (увеличенная ширина)
        ttk.Label(input_frame, text="Сид (оставьте пустым для случайного):").grid(
            row=1, column=0, sticky="w", padx=5, pady=3)
        self.seed_entry = ttk.Entry(input_frame, width=45)  # Увеличенная ширина
        self.seed_entry.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
        
        # Остальные элементы без изменений
        ttk.Label(input_frame, text="Шаг реверса (0=выкл, 1-20):").grid(
            row=2, column=0, sticky="w", padx=5, pady=3)
        self.step_entry = ttk.Entry(input_frame, width=5)
        self.step_entry.insert(0, "")
        self.step_entry.grid(row=2, column=1, padx=5, pady=3, sticky="w")
        
        ttk.Label(input_frame, text="Формат сида:").grid(
            row=3, column=0, sticky="w", padx=5, pady=3)
        self.seed_format_combobox = ttk.Combobox(
            input_frame, 
            values=["Только цифры", "Цифры и буквы"], 
            state="readonly",
            width=18
        )
        self.seed_format_combobox.current(0)
        self.seed_format_combobox.grid(row=3, column=1, padx=5, pady=3, sticky="w")
        self.seed_format_combobox.bind("<<ComboboxSelected>>", self.update_seed_format)
        
        # Фрейм для кнопок
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 15))
        
        ttk.Button(btn_frame, text="Перемешать", command=self.shuffle_tracks).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Сохранить", command=self.save_playlist).pack(side=tk.LEFT)
        
        # Поле для сообщений
        self.seed_info = tk.Label(main_frame, text="", fg="red")
        self.seed_info.pack(pady=(5, 0))
        
    def update_seed_format(self, event=None):
        """Обновляет выбранный формат сида"""
        self.seed_format = self.seed_format_combobox.get()

    def generate_seed(self, num_tracks, date, length=None):
        """Полная копия из PlaylistGenerator.py"""
        date_part = date.strftime("%Y%m%d%H%M%S")
        random_part = random.getrandbits(512)
    
        # Расчет длины сида
        base_length = math.ceil(math.log2(num_tracks + 1)) * 2
        max_reasonable_length = 128
        seed_length = min(max(2, base_length), 128)
    
        # Генерация хеша
        entropy = f"{num_tracks}{date.timestamp()}{random_part}"
        hash_str = hashlib.sha512(entropy.encode()).hexdigest()
    
        # Форматирование
        format_type = self.seed_format_combobox.get()
        if format_type == "Только цифры":
            return ''.join(c for c in hash_str if c.isdigit())[:seed_length]
        return hash_str[:seed_length]


    def apply_reverse_step(self, files, step):
        """Реверс блоков (идентично генератору)"""
        reversed_files = files.copy()
        for i in range(0, len(reversed_files), step):
            reversed_files[i:i+step] = reversed(reversed_files[i:i+step])
        return reversed_files


    def shuffle_tracks(self):
        """Перемешивание с фиксированным результатом для одинакового сида"""
        try:
            user_seed = self.seed_entry.get()
            step_value = self.step_entry.get()
            num_tracks = len(self.original_paths)  # Используем оригинальный список
            now = datetime.datetime.now()
        
            # Сохраняем отсортированный список как оригинальный
            if not hasattr(self, 'original_paths') or not self.original_paths:
                self.original_paths = self.full_paths.copy()
        
            # 1. Генерация/получение сида
            if not user_seed or user_seed == "0":
                seed_length = max(2, min(128, math.ceil(math.log2(num_tracks + 1) * 2)))
                seed = self.generate_seed(num_tracks, now, seed_length)
                self.seed_entry.delete(0, tk.END)
            else:
                seed = user_seed
            
            # 2. Валидация шага реверса
            step = 0
            if step_value.strip():
                try:
                    step = int(step_value)
                    if step < 0 or step > 20:
                        raise ValueError("Шаг реверса должен быть от 0 до 20")
                except ValueError as e:
                    self.seed_info.config(text=f"Ошибка: {str(e)}", fg="red")
                    return
            
            # 3. Всегда начинаем с оригинального порядка
            files_to_shuffle = self.original_paths.copy()
            
            # 4. Применяем перемешивание
            random.seed(abs(self.stable_hash(str(seed))))
            shuffled = files_to_shuffle.copy()
            random.shuffle(shuffled)
            
            # 5. Применяем реверс если нужно
            reverse_step = None
            if step > 0:
                reverse_step = step
                shuffled = self.apply_reverse_step(shuffled, reverse_step)
                info_text = f"Перемешано! Сид: {seed} | Шаг реверса: {reverse_step}"
            else:
                info_text = f"Перемешано! Сид: {seed}"
            
            # 6. Обновляем данные
            self.current_seed = seed
            self.current_reverse_step = reverse_step if step > 0 else None
            self.full_paths = shuffled
            self.display_names = [os.path.basename(f) for f in shuffled]
            
            self.update_table()
            self.seed_info.config(text=info_text, fg="green")
            
        except Exception as e:
            self.seed_info.config(text=f"Ошибка: {str(e)}", fg="red")


    def shuffle_files(self, files_list, seed_value):
        """Полная копия из PlaylistGenerator.py"""
        random.seed(abs(self.stable_hash(seed_value)))
        shuffled = files_list.copy()
        random.shuffle(shuffled)
        return shuffled

    def update_table(self):
        """Обновление таблицы с треками"""
        self.tree.delete(*self.tree.get_children())
        for i, name in enumerate(self.display_names, 1):
            self.tree.insert('', 'end', values=(i, name))

    def save_playlist(self):
        """Сохранение плейлиста с информацией о сиде"""
        try:
            if not self.full_paths:
                raise ValueError("Нет треков для сохранения")
                
            if getattr(sys, 'frozen', False):
                script_dir = os.path.dirname(sys.executable)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
            
            playlist_name = self.name_entry.get().strip()
            if not playlist_name:
                raise ValueError("Укажите имя плейлиста")
            
            save_path = os.path.join(script_dir, f"{playlist_name}.m3u8")
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write("#Created by VolfLife's Playlist Generator\n")
                f.write(f"#GENERATED:{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"#PLAYLIST:{playlist_name}\n")
                
                if hasattr(self, 'current_seed') and self.current_seed:
                    f.write(f"#SEED:{self.current_seed}\n")
                    if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                        f.write(f"#REVERSE_STEP:{self.current_reverse_step}\n")
                
                f.write(f"#TRACKS:{len(self.full_paths)}\n\n")
                
                for path in self.full_paths:
                    f.write(f"#EXTINF:-1,{os.path.basename(path)}\n")
                    f.write(f"{os.path.normpath(path)}\n")
            
            message = f"Плейлист сохранен: {playlist_name}.m3u8"
            if hasattr(self, 'current_seed') and self.current_seed:
                message += f" | Сид: {self.current_seed}"
                if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                    message += f" | Шаг реверса: {self.current_reverse_step}"
            
            self.seed_info.config(text=message, fg="green")
            
        except Exception as e:
            self.seed_info.config(text=f"Ошибка сохранения: {str(e)}", fg="red")