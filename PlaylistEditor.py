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
from tkinter import ttk, messagebox
import string
from Localization import Localization
            

class PlaylistEditor:
    def __init__(self, root, file_path):
        self.root = root
        self.localization = Localization()
        self.load_language_settings()
        self.root.title(self.localization.tr("window_title_editor"))
        
        self.file_path = file_path
        self.original_paths = []  # Храним оригинальный порядок
        self.full_paths = []      # Текущий порядок
        self.display_names = []
        self.current_seed = ""
        self.current_reverse_step = None
        self.seed_format = self.localization.tr("seed_formats")[0]  # По умолчанию
        
        try:
            self.load_playlist()
            self.original_paths = self.full_paths.copy()  # Сохраняем оригинал
            self.create_widgets()
            self.center_window(540, 600)
        except Exception as e:
            messagebox.showerror(
                self.localization.tr("error"),
                self.localization.tr("error_load_playlist").format(error=str(e))
            )
            self.root.destroy()
            raise


    def load_language_settings(self):
        """Загружает настройки языка с той же логикой"""
        try:
            with open('playlist_settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
                saved_lang = settings.get('language')
                if saved_lang and self.localization.is_language_supported(saved_lang):
                    self.localization.set_language(saved_lang)
                else:
                    sys_lang = self.localization.detect_system_language()
                    self.localization.set_language(sys_lang)
                    # Для редактора не сохраняем, т.к. это может быть нежелательно
                
        except (FileNotFoundError, json.JSONDecodeError):
            sys_lang = self.localization.detect_system_language()
            self.localization.set_language(sys_lang)



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
                    if self.file_path.lower().endswith('.txt'):
                        line = line.replace('"', '')    
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
        if filename.lower().endswith('.m3u'):
            filename = filename[:-4]  # Удаляем .m3u
        if filename.lower().endswith('.txt'):
            filename = filename[:-4]  # Удаляем .txt            
        
        # Удаляем _mixed если уже есть
        if filename.endswith('_mixed'):
            filename = filename[:-6]
        
        # Устанавливаем имя плейлиста
        self.playlist_name = (self.localization.tr("shuffled").format(filename=filename))

    def stable_hash(self, s):
        """Детерминированная замена hash() с использованием hashlib"""
        return int(hashlib.md5(str(s).encode()).hexdigest(), 16) % (10**12)

    def create_widgets(self):
        """Создает интерфейс редактора"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Фрейм для таблицы с ползунком
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Таблица треков с ползунком
        self.tree = ttk.Treeview(table_frame, columns=('num', 'name'), show='headings')
        self.tree.heading('num', text=self.localization.tr("track_number"))
        self.tree.heading('name', text=self.localization.tr("track_name"))
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
        ttk.Label(input_frame, text=self.localization.tr("playlist_name_label")).grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.name_entry = ttk.Entry(input_frame, width=45)
        self.name_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.name_entry.insert(0, self.playlist_name)
        
        # Поле сида (увеличенная ширина)
        ttk.Label(input_frame, text=self.localization.tr("seed_label")).grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.seed_entry = ttk.Entry(input_frame, width=45)
        self.seed_entry.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
        
        # Остальные элементы без изменений
        ttk.Label(input_frame, text=self.localization.tr("reverse_step_label")).grid(
            row=2, column=0, sticky="w", padx=5, pady=3)
        self.step_entry = ttk.Entry(input_frame, width=5)
        self.step_entry.insert(0, "")
        self.step_entry.grid(row=2, column=1, padx=5, pady=3, sticky="w")
        
        ttk.Label(input_frame, text=self.localization.tr("seed_format_label")).grid(
            row=3, column=0, sticky="w", padx=5, pady=3)
        self.seed_format_combobox = ttk.Combobox(
            input_frame, 
            values=self.localization.tr("seed_formats"), 
            state="readonly",
            width=18
        )
        self.seed_format_combobox.current(0)
        self.seed_format_combobox.grid(row=3, column=1, padx=5, pady=3, sticky="w")
        self.seed_format_combobox.bind("<<ComboboxSelected>>", self.update_seed_format)
        
        # Фрейм для кнопок
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 15))
        
        ttk.Button(btn_frame, text=self.localization.tr("shuffle_button"), command=self.shuffle_tracks).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=self.localization.tr("save_button"), command=self.save_playlist).pack(side=tk.LEFT)
        
        # Поле для сообщений
        self.seed_info = tk.Label(main_frame, text="", fg="red")
        self.seed_info.pack(pady=(5, 0))
        
        
        # Фрейм для новых кнопок управления
        control_frame = ttk.Frame(btn_frame)
        control_frame.pack(side=tk.RIGHT, padx=5)
        
        # Кнопки управления
        self.move_up_btn = ttk.Button(control_frame, text="▲", width=3, 
                                    command=self.move_up)
        self.move_up_btn.pack(side=tk.LEFT, padx=2)
        
        self.move_down_btn = ttk.Button(control_frame, text="▼", width=3,
                                      command=self.move_down)
        self.move_down_btn.pack(side=tk.LEFT, padx=2)
        
        self.delete_btn = ttk.Button(control_frame, text="🞭", width=3,
                                   command=self.delete_tracks)
        self.delete_btn.pack(side=tk.LEFT, padx=2)
        
        self.undo_btn = ttk.Button(control_frame, text="🡄", width=3,
                                 command=self.undo_action)
        self.undo_btn.pack(side=tk.LEFT, padx=2)
        
        self.redo_btn = ttk.Button(control_frame, text="🡆", width=3,
                             command=self.redo_action, state='disabled')
        self.redo_btn.pack(side=tk.LEFT, padx=2)
    
        # История для Redo
        self.redo_stack = []
        
        # История изменений для отмены действий
        self.history = []
        self.future = []  # Для redo (если потребуется)
        self.manual_edit = False  # Флаг ручного редактирования
        
    
    def move_up(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        positions = [int(self.tree.index(item)) for item in selected]
        if min(positions) == 0:
            return
        
        self.save_state()  # Теперь автоматически обновляет кнопки
        
        for item in selected:
            index = self.tree.index(item)
            self.tree.move(item, '', index-1)
        
        self.manual_edit = True
        self.update_undo_redo_buttons()  # Явное обновление состояния кнопок
        self.update_track_lists()  # Обновляем списки
        self.show_message(self.localization.tr("moved_up"), "green")

    def move_down(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        positions = [int(self.tree.index(item)) for item in selected]
        if max(positions) == len(self.tree.get_children())-1:
            return
        
        self.save_state()  # Теперь автоматически обновляет кнопки
        
        for item in reversed(selected):
            index = self.tree.index(item)
            self.tree.move(item, '', index+1)
        
        self.manual_edit = True
        self.update_undo_redo_buttons()  # Явное обновление состояния кнопок
        self.update_track_lists()  # Обновляем списки
        self.show_message(self.localization.tr("moved_down"), "green")

    def delete_tracks(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        self.save_state()  # Теперь автоматически обновляет кнопки
        
        for item in selected:
            self.tree.delete(item)
        
        self.manual_edit = True
        self.update_undo_redo_buttons()  # Явное обновление состояния кнопок
        self.update_track_lists()  # Обновляем списки
        self.show_message(
            self.localization.tr("deleted_tracks").format(count=len(selected)), 
            "green"
        )

    def undo_action(self):
        if not self.history:
            self.show_message(self.localization.tr("nothing_to_undo"), "red")
            return
        
        # Сохраняем текущее состояние в redo stack
        self.redo_stack.append(self.get_current_state())
        
        
      
        state = self.history.pop()
        self.restore_state(state)
        
        self.manual_edit = True
        self.update_undo_redo_buttons()
        self.update_track_lists()  # Обновляем списки после отмены
        self.show_message(self.localization.tr("action_undone"), "green")
        
        
    def redo_action(self):
        """Повтор отмененного действия"""
        if not self.redo_stack:
            return
        
        # Сохраняем текущее состояние в undo history
        self.history.append(self.get_current_state())
        
        # Восстанавливаем состояние из redo stack
        state = self.redo_stack.pop()
        self.restore_state(state)
        
        self.manual_edit = True
        self.update_undo_redo_buttons()
        self.show_message(self.localization.tr("action_redone"), "green")
    
    def update_undo_redo_buttons(self):
        """Обновляет состояние кнопок Undo/Redo"""
        self.undo_btn['state'] = 'normal' if self.history else 'disabled'
        self.redo_btn['state'] = 'normal' if self.redo_stack else 'disabled'
    
    def save_state(self):
        """Сохраняет текущее состояние для Undo/Redo"""
        current_state = self.get_current_state()
        if hasattr(self, 'history') and self.history and self.history[-1] == current_state:
            return
        
        if hasattr(self, 'history'):
            self.history.append(current_state)
            # Очищаем redo stack при новом действии
            self.redo_stack = []
            self.update_undo_redo_buttons()
        else:
            self.history = [current_state]

    def get_current_state(self):
        """Возвращает текущее состояние плейлиста"""
        return [(self.tree.item(item)['values'], item) 
                for item in self.tree.get_children()]

    def restore_state(self, state):
        """Восстанавливает состояние из истории"""
        self.tree.delete(*self.tree.get_children())
        for values, item in state:
            self.tree.insert('', 'end', values=values, iid=item)

    def show_message(self, text, color):
        """Обновляет поле сообщений"""
        self.seed_info.config(text=text, fg=color)    
        
        
        
        
    def update_seed_format(self, event=None):
        """Обновляет выбранный формат сида"""
        self.seed_format = self.seed_format_combobox.get()

    def generate_seed(self, num_tracks, date, length=None):
        """Полная копия из PlaylistGenerator.py"""
        date_part = date.strftime("%Y%m%d%H%M%S")
        random_part = random.getrandbits(64)
    
        # Расчет длины сида
        base_length = math.ceil(math.log2(num_tracks + 1))
        seed_length = min(max(1, base_length), base_length)
    
        # Генерация хеша
        entropy = f"{num_tracks}{date.timestamp()}{random_part}"
        hash_str = hashlib.sha512(entropy.encode()).hexdigest()
    
        # Форматирование
        format_type = self.seed_format_combobox.get()
        if format_type in ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", "Толькі лічбы",
                    "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Chiffres uniquement", "Sólo números", "Apenas números", 
                    "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만"]:
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
                # Автоматическая генерация основного сида на основе количества треков           
                seed_length = min(max(1, num_tracks), num_tracks)
                seed = self.generate_seed(num_tracks=num_tracks, date=now, length=seed_length)
                
                self.seed_entry.delete(0, tk.END)
            else:
                seed = user_seed
            
            # 2. Валидация шага реверса
            step = 0
            if step_value.strip():
                try:
                    step = int(step_value)
                    if step < 0 or step > 20:
                        raise ValueError(self.localization.tr("error_reverse_step"))
                except ValueError as e:
                    self.seed_info.config(text=f"{self.localization.tr('error_reverse_step')}", fg="red")
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
                info_text = self.localization.tr("seed_info_step").format(seed=seed, step=reverse_step)
            else:
                info_text = self.localization.tr("seed_info_basic").format(seed=seed)
            
            # 6. Обновляем данные
            self.manual_edit = False
            self.current_seed = seed
            self.current_reverse_step = reverse_step if step > 0 else None
            self.full_paths = shuffled
            self.display_names = [os.path.basename(f) for f in shuffled]
            
            self.update_table()
            self.seed_info.config(text=info_text, fg="green")
            
        except Exception as e:
            self.seed_info.config(text=f"{self.localization.tr('error')}: {str(e)}", fg="red")


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
            # Получаем текущие треки из Treeview
            current_tracks = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                if len(values) >= 2:  # Проверяем, что есть путь к файлу
                    current_tracks.append(values[1])  # values[1] - это путь к файлу
        
            if not current_tracks:
                raise ValueError(self.localization.tr("error_no_tracks"))
               
               
            script_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
                        else os.path.dirname(os.path.abspath(__file__))
            
            playlist_name = self.name_entry.get().strip()
            if not playlist_name:
                raise ValueError(self.localization.tr("error_no_playlist_name"))
            
            save_path = os.path.join(script_dir, f"{playlist_name}.m3u8")
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write("#Created by VolfLife's Playlist Generator\n")
                f.write(f"#GENERATED:{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"#PLAYLIST:{playlist_name}\n")
                
                # Не сохраняем сид, если было ручное редактирование
                if not self.manual_edit and hasattr(self, 'current_seed') and self.current_seed:
                    f.write(f"#SEED:{self.current_seed}\n")
                if not self.manual_edit and hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                    f.write(f"#REVERSE_STEP:{self.current_reverse_step}\n")
                
                f.write(f"#TRACKS:{len(self.full_paths)}\n\n")
                
                for path in self.full_paths:
                    f.write(f"#EXTINF:-1,{os.path.basename(path)}\n")
                    f.write(f"{os.path.normpath(path)}\n")
            
            
            # Обновляем внутренний список треков
            self.full_paths = current_tracks
            self.display_names = [os.path.basename(path) for path in current_tracks]
            
            # Формируем сообщение
            message = self.localization.tr("playlist_saved").format(name=f"{playlist_name}.m3u8")
            
            # Добавляем информацию о сиде ТОЛЬКО если не было ручного редактирования
            if not self.manual_edit:
                if hasattr(self, 'current_seed') and self.current_seed:
                    message += f" | {self.localization.tr('seed_info_value')}: {self.current_seed}"
                    if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                        message += f" | {self.localization.tr('reverse_info_value')}: {self.current_reverse_step}"
            
            self.seed_info.config(text=message, fg="green")
            
        except Exception as e:
            self.seed_info.config(
                text=f"{self.localization.tr('error_save')}: {str(e)}", 
                fg="red"
            )
    
    def update_track_lists(self):
        """Обновляет внутренние списки треков на основе текущего состояния Treeview"""
        self.full_paths = []
        self.display_names = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if len(values) >= 2:
                self.full_paths.append(values[1])
                self.display_names.append(values[0])  # Имя трека
                