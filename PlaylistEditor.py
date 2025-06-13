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
from Localization import Localization
from FontLoader import FontLoader            

class PlaylistEditor:
    def __init__(self, root, file_paths=None):
        self.root = root
        self.localization = Localization()
        self.visited_github = False
        self.github_link = None
        self.format_m3u8 = "m3u8"
        self.format_file = "m3u8"
        self.load_language_settings()
        self.root.title(self.localization.tr("window_title_editor"))
        self.playlist_name = ""
        self.path_editor = None
        
        # Инициализация списков
        self.original_lists = {}  # Будем хранить оригинальные списки по ключам (original_temp_list_1 и т.д.)
        self.original_list = []   # Объединенный список
        self.temp_list = None    # Временный список после ручного редактирования
        self.sorted_list = None  # Отсортированная версия для перемешивания
        self.shuffled_list = None # Результат перемешивания
        self.tracks = []  # Формат: [{"path": "", "name": "", "num": 0}, ...]
        self.display_tracks = []  # Треки для отображения
        self.modified_paths = {}
        # Принимаем как один путь, так и список путей
        if file_paths:
            if isinstance(file_paths, str):
                file_paths = [file_paths]  # Для обратной совместимости
            self.file_paths = [fp.strip('"') for fp in file_paths]  # Очищаем пути
        else:
            self.file_paths = []
            
        
        self.original_paths = []  # Храним оригинальный порядок
        self.full_paths = []      # Текущий порядок
        self.display_names = []
        self.current_seed = ""
        self.current_reverse_step = None
        self.seed_format = self.localization.tr("seed_formats")[0]  # По умолчанию
        self.selected_for_edit = []
        
        try:
            self.font_loader = FontLoader(root)
            self.symbol_font = self.font_loader.symbol_font
            self.create_widgets(root)
            self.load_playlist()
            # История для Undo/Redo
            self.history = []
            self.history_index = -1
            self.save_state(force_save=True)  # Сохраняем начальное состояние
            
            self.save_initial_state()
            self.show_version_info()
            self.original_paths = self.full_paths.copy()  # Сохраняем оригинал
            
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
                self.visited_github = settings.get('visited_github')
                saved_format = settings.get('playlist_format')
                print(f"[DEBUG] Посетил GitHub: {self.visited_github}")
                if saved_lang and self.localization.is_language_supported(saved_lang):
                    self.localization.set_language(saved_lang)
                    print(f"[DEBUG] Загружен язык: {saved_lang}")
                else:
                    sys_lang = self.localization.detect_system_language()
                    self.localization.set_language(sys_lang)
                    print(f"[DEBUG] Неподдерживаемый язык в настройках. Авто–язык: {sys_lang}")
                    
                    # Для редактора не сохраняем, т.к. это может быть нежелательно
                
                # Устанавливаем значение напрямую, если оно есть в списке
                if saved_format in ["m3u8", "m3u", "txt"]:
                    self.format_m3u8 = saved_format 
                    print(f"[DEBUG] Загружен формат: {saved_format}")
                else:
                    self.format_m3u8 = "m3u8"
                    print(f"[DEBUG] Неподдерживаемый формат '{saved_format}'. Авто–формат: m3u8")
                
                
        
                
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"[DEBUG] Файл настроек не найден. Был создан новый.")
            sys_lang = self.localization.detect_system_language()
            self.localization.set_language(sys_lang)
            self.visited_github = False
            print(f"[DEBUG] Автоматический выбор языка: {sys_lang}")
            print(f"[DEBUG] Автоматический выбор формата: m3u8")

    def show_version_info(self):
        from version_info import version_info
        version_label = tk.Label(
            self.root, 
            text=f"{version_info['product_name']} v{version_info['version']} by {version_info['author']}",
            fg="gray"
        )
        # Размещаем в правом нижнем углу окна
        version_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-5)
    
    
    def open_github(self, event=None):
        """Обработчик клика по GitHub ссылке"""
        import webbrowser
        webbrowser.open("https://github.com/VolfLife/Playlist-Generator/")
        
        if not self.visited_github:
            self.visited_github = True
            
            try:
                with open('playlist_settings.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                settings = {}
            
            settings['visited_github'] = self.visited_github
            
            with open('playlist_settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)

            
            # Затем обновляем виджет
            if self.github_link:
                self.github_link.config(fg="gray")
            else:
                self.create_github_link()  # Пересоздаем если не существует     


    def center_window(self, width, height):
        """Центрирование окна"""
        self.root.resizable(width=False, height=False)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 3) - (height // 3)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(540, 650)

    def load_playlist(self):
        """Загружает несколько плейлистов и объединяет их"""
        supported_formats = {
            # Аудио
            '.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.wma', '.opus', '.aiff',
            # Видео
            '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'
        }
        for i, file_path in enumerate(self.file_paths, 1):
            temp_list = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                                
                                
                            # Удаляем кавычки и лишние пробелы
                            clean_path = line.strip('"\' \t')
                            
                            # Проверяем расширение файла
                            if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                continue
                                
                            # Нормализуем путь (убираем лишние слеши и т.д.)
                            normalized_path = os.path.normpath(clean_path).replace('\\', '/')    
                            
                                
                            temp_list.append({
                                    "path": normalized_path,
                                    "name": os.path.basename(normalized_path),
                                    "num": line_num,
                                    "source": f"original_temp_list_{i}",  # Добавляем источник
                                    "original_path": normalized_path,  # Добавили сохранение оригинального пути
                                    "was_modified": False
                                })    
                            
                # Сохраняем отдельный список
                self.original_lists[f"original_temp_list_{i}"] = temp_list
                # Добавляем в объединенный список
                self.original_list.extend(temp_list)
                count = len(self.file_paths)
                self.seed_info.config(text=self.localization.tr("multiple_playlists_loaded").format(count=f"{count}"), fg="green")
            except Exception as e:
                print(f"Error loading playlist {file_path}: {str(e)}")
                continue
            print(f"[DEBUG] Загружено плейлистов = {count}")    
        
        
        # Обновляем отображение
        self.display_tracks = self.original_list.copy()
        self.update_display()
        
        # Сохраняем начальное состояние
        self.save_initial_state()
    
        # Генерируем имя плейлиста
        if self.file_paths:
            base_name = os.path.basename(self.file_paths[0])
            for ext in ['.m3u8', '.m3u', '.txt']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break
            
            # Добавляем количество файлов если их >1
            if len(self.file_paths) > 1:
                self.playlist_name = f"{base_name}_and_{len(self.file_paths)-1}_more"
            else:
                self.playlist_name = base_name
            
            # Обновляем поле ввода имени
            if hasattr(self, 'name_entry'):
                self.name_entry.delete(0, tk.END)
                shuffled_text = self.localization.tr("shuffled")
                self.name_entry.insert(0, f"{self.playlist_name}_{shuffled_text}")
        
        # Инициализируем временный список как None (нет изменений)
        self.base_list = None
        self.sorted_list = None
        self.shuffled_list = None
        

    
    def get_current_list(self):
        """Возвращает актуальный список для отображения"""
        if self.shuffled_list is not None:
            return self.shuffled_list
        elif self.temp_list is not None:
            return self.temp_list
        return self.original_list


    def stable_hash(self, s):
        """Детерминированная замена hash() с использованием hashlib"""
        return int(hashlib.md5(str(s).encode()).hexdigest(), 16) % (10**12)


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



    def create_widgets(self, root):
        """Создает интерфейс редактора"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        
        # Фрейм для таблицы с ползунком
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        table_frame.grid_propagate(False) 
        #table_frame.config(height=600)
        
        # Таблица треков с ползунком
        self.tree = ttk.Treeview(
            table_frame, 
            columns=('num', 'name'), 
            show='headings', 
            selectmode='extended',
            height=17  # Количество видимых строк
            )
        self.tree.heading('num', text=self.localization.tr("track_number"))
        self.tree.heading('name', text=self.localization.tr("track_name"))
        self.tree.column('num', width=50, anchor='center')
        self.tree.column('name', width=440, anchor='w')
        
        
        # Добавляем подсказку при наведении курсора
        self.tree_tooltip = tk.Label(self.root, text=self.localization.tr("tree_tooltip"), 
                                           bg="beige", relief="solid", borderwidth=1)
        self.tree_tooltip.place_forget()
        self.tree.bind("<Enter>", self.show_tree_tooltip)
        self.tree.bind("<Leave>", self.hide_tree_tooltip)
        
        # Вертикальный ползунок
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        for i, name in enumerate(self.display_names, 1):
            self.tree.insert('', 'end', values=(i, name))
        
        # Фрейм для полей ввода
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        # Поле имени плейлиста
        tk.Label(input_frame, text=self.localization.tr("playlist_name_label")).grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.name_entry = ttk.Entry(input_frame, width=45)
        self.name_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        self.name_entry.insert(0, self.playlist_name)
        
        # Поле сида (увеличенная ширина)
        tk.Label(input_frame, text=self.localization.tr("seed_label")).grid(row=1, column=0, sticky="w", padx=5, pady=3)
        self.seed_entry = ttk.Entry(input_frame, width=45)
        self.seed_entry.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
        
        # Остальные элементы без изменений
        tk.Label(input_frame, text=self.localization.tr("reverse_step_label")).grid(
            row=2, column=0, sticky="w", padx=5, pady=3)
        self.step_entry = ttk.Entry(input_frame, width=5)
        self.step_entry.insert(0, "")
        self.step_entry.grid(row=2, column=1, padx=5, pady=3, sticky="w")
        
        tk.Label(input_frame, text=self.localization.tr("seed_format_label")).grid(
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
                

        # Combobox формата
        self.format_combobox = ttk.Combobox(
            btn_frame,
            values=["m3u8", "m3u", "txt"],
            state="readonly",
            width=5
        )
        self.format_combobox.pack(side=tk.LEFT, padx=12)
        self.format_combobox.set(self.format_m3u8)
        self.format_combobox.bind("<<ComboboxSelected>>", self.change_format)
        
        # Поле для сообщений
        message_frame = ttk.Frame(main_frame)
        message_frame.pack(fill=tk.X, pady=(6, 10))
        
        # Фиксируем высоту фрейма сообщений
        message_frame.pack_propagate(False)  # Отключаем автоматическое изменение размера
        message_frame.config(height=45)  # Устанавливаем фиксированную высоту
        
        self.seed_info = tk.Label(
            message_frame,
            text="",
            fg="red",
            justify="center"  # Выравнивание по центру при переносе строк
        )
        self.seed_info.pack(fill=tk.X, expand=True)
        
                
                
        # Обработчики drag-and-drop в Treeview
        self.tree.bind("<ButtonPress-1>", self.on_treeview_button_press)
        self.tree.bind("<B1-Motion>", self.on_treeview_mouse_move)
        self.tree.bind("<ButtonRelease-1>", self.on_treeview_button_release)
        
        # Добавляем привязку для Ctrl+A
        self.tree.bind("<Control-a>", self.select_all_tracks)
        self.tree.bind("<Control-A>", self.select_all_tracks)  # Для Caps Lock

        # Переменные для drag-and-drop
        self._drag_data = {"item": None, "y": 0}
    
        # История для Redo
        self.redo_stack = []
        
        # История изменений для отмены действий
        self.history = []
        self.future = []  # Для redo (если потребуется)
        self.manual_edit = False  # Флаг ручного редактирования
        
        
        # Привязка правой кнопки мыши для открытия редактора путей
        self.tree.bind("<Button-3>", self.create_path_editor_window)
        
        
        self.update_display()
        
        
        self.create_github_link()  # Создаем ссылку на GitHub
        
        # Убедимся, что ссылка поверх информации
        self.github_link.lift()  # Поднимаем на передний план
 

        # Используем загруженный шрифт
        style = ttk.Style(root)
        
        # Указываем только имя семейства шрифта (без объекта Font)
        style.configure('Symbol.TButton', 
                      font=(self.font_loader.symbol_font, 9),
                      padding=2)

        
        # Кнопки управления
        self.redo_btn = ttk.Button(
            btn_frame, 
            text="e", 
            width=2,
            style='Symbol.TButton',
            command=self.redo_action, 
            state='disabled'
            )
        self.redo_btn.pack(side=tk.RIGHT, padx=2)
        
        
        self.undo_btn = ttk.Button(
            btn_frame, 
            text="d", 
            width=2,
            style='Symbol.TButton',
            command=self.undo_action
            )
        self.undo_btn.pack(side=tk.RIGHT, padx=2)


        self.delete_btn = ttk.Button(
            btn_frame, 
            text="c", 
            width=2,
            style='Symbol.TButton',
            command=self.delete_tracks
            )
        self.delete_btn.pack(side=tk.RIGHT, padx=2)
        
        self.move_down_btn = ttk.Button(
            btn_frame, 
            text="b", 
            width=2,
            style='Symbol.TButton',
            command=self.move_down
            )
        self.move_down_btn.pack(side=tk.RIGHT, padx=2)


        self.move_up_btn = ttk.Button(
            btn_frame,
            text="a", 
            width=2, 
            style='Symbol.TButton',
            command=self.move_up
            )
        self.move_up_btn.pack(side=tk.RIGHT, padx=2)
        

    def show_tree_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = self.localization.tr("tree_tooltip")
        self.tree_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.tree_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.tree.winfo_x()  # Позиция поля ввода
        entry_width = self.tree.winfo_width()  # Ширина поля
        tooltip_width = self.tree_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + 20 + (entry_width - tooltip_width) // 2
        y = self.tree.winfo_y() + 395  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.tree_tooltip.place(x=x, y=y)

    def hide_tree_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'tree_tooltip'):
            self.tree_tooltip.place_forget()    
    
    def select_all_tracks(self, event=None):
        """Выделяет все треки в таблице"""
        items = self.tree.get_children()
        if items:
            self.tree.selection_set(items)
        return "break"  # Предотвращаем дальнейшую обработку события
        
    def on_treeview_button_release(self, event):
        """Обработчик отпускания кнопки мыши с гарантированным сохранением"""
        if hasattr(self, '_drag_data') and self._drag_data and self._drag_data.get("items"):
            # Проверяем, изменились ли позиции
            original_indices = set(self._drag_data["indices"])
            current_indices = set(self.tree.index(i) for i in self.tree.selection())
            
            if original_indices != current_indices:
                # Создаем временный список если его еще нет
                if self.temp_list is None:
                    self.temp_list = [track.copy() for track in self.display_tracks]
                
                # Помечаем все перемещённые треки
                for idx in current_indices:
                    if 0 <= idx < len(self.temp_list):  # Проверяем границы списка
                        self.temp_list[idx]['was_moved'] = False
                
                self.save_state()
                print("[DRAG] Состояние сохранено после перетаскивания")
        
        self._drag_data = None
        self.save_state()

    def on_treeview_mouse_move(self, event):
        """Обработчик перемещения мыши при перетаскивании"""
        if not self._drag_data or not self._drag_data["items"]:
            return
        
        y = event.y
        delta_y = y - self._drag_data["y"]
        if abs(delta_y) < 5:  # Минимальное перемещение для начала drag
            return
        
        # Определяем целевой элемент
        target_item = self.tree.identify_row(y)
        children = list(self.tree.get_children())
        
        if target_item:
            target_index = children.index(target_item)
        else:
            target_index = len(children)  # Если курсор ниже всех элементов
        
        # Получаем индексы перемещаемых элементов
        moving_indices = sorted(self._drag_data["indices"])
        
        # Если целевая позиция внутри выделения - игнорируем
        if target_index >= moving_indices[0] and target_index <= moving_indices[-1] + 1:
            return
        
        # Создаем временный список если его еще нет
        if self.temp_list is None:
            self.temp_list = [track.copy() for track in self.display_tracks]
        
        # Извлекаем перемещаемые треки и помечаем их как перемещённые
        moving_tracks = []
        for i in moving_indices:
            track = self.temp_list[i].copy()
            track['was_moved'] = True  # Помечаем трек как перемещённый
            moving_tracks.append(track)
        
        # Удаляем их из исходных позиций (в обратном порядке)
        for i in reversed(moving_indices):
            del self.temp_list[i]
        
        # Корректируем целевую позицию с учетом удаленных элементов
        if target_index > moving_indices[-1]:
            target_index -= len(moving_indices)
        
        # Вставляем треки в новую позицию
        for i, track in enumerate(moving_tracks):
            self.temp_list.insert(target_index + i, track)
        
        # Обновляем отображение
        self.display_tracks = self.temp_list.copy()
        
        # Вычисляем новые индексы выделения
        new_selection_indices = list(range(target_index, target_index + len(moving_tracks)))
        self.update_display(selection_indices=new_selection_indices)
        
        # Обновляем данные для drag
        self._drag_data["y"] = y
        self._drag_data["indices"] = new_selection_indices

    def on_treeview_button_press(self, event):
        """Обработчик нажатия кнопки мыши для начала перетаскивания"""
        item = self.tree.identify_row(event.y)
        if item:
            # Если Ctrl или Shift нажат, не начинаем перетаскивание
            if event.state & (0x0004 | 0x0001):  # 0x0004 - Ctrl, 0x0001 - Shift
                self._drag_data = None
                return
            
            # Если элемент не выделен - выделяем только его
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            
            # Сохраняем позиции всех выделенных элементов
            self._drag_data = {
                "items": self.tree.selection(),
                "y": event.y,
                "indices": [self.tree.index(i) for i in self.tree.selection()]
            }
        else:
            self._drag_data = None

    
    def move_up(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        positions = sorted([int(self.tree.index(item)) for item in selected])
        if positions[0] == 0:
            return
        
        if self.temp_list is None:
            self.temp_list = []
            for track in self.display_tracks:
                new_track = track.copy()
                new_track["was_modified"] = track.get("was_modified", False)
                new_track["was_restored"] = track.get("was_restored", False)
                self.temp_list.append(new_track)
        
        for index in positions:
            # Сохраняем флаги для обоих треков
            prev_restored = self.temp_list[index-1].get("was_restored", False)
            current_restored = self.temp_list[index].get("was_restored", False)
            
            # Обмениваем треки местами
            self.temp_list[index], self.temp_list[index-1] = self.temp_list[index-1], self.temp_list[index]
            
            # Помечаем перемещенные треки
            self.temp_list[index-1]['was_moved'] = True
            # Если трек был восстановлен, меняем тег на moved_restored
            if prev_restored:
                self.temp_list[index-1]['was_restored'] = False
                self.temp_list[index]['was_restored'] = True
        
        self.display_tracks = self.temp_list
        
        # Перед обновлением сохраняем новые индексы выбранных элементов (со смещением на -1)
        new_selection_indices = [i-1 for i in positions]
        self.update_display(selection_indices=new_selection_indices)
        
        self.show_message(self.localization.tr("moved_up"), "green")
        self.manual_edit = True
        self.update_undo_redo_buttons()
        self.save_state()

    def move_down(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        positions = sorted([int(self.tree.index(item)) for item in selected], reverse=True)
        max_index = len(self.tree.get_children()) - 1
        if positions[0] == max_index:
            return
        
        if self.temp_list is None:
            self.temp_list = []
            for track in self.display_tracks:
                new_track = track.copy()
                new_track["was_modified"] = track.get("was_modified", False)
                new_track["was_restored"] = track.get("was_restored", False)
                self.temp_list.append(new_track)
        
        for index in positions:
            # Сохраняем флаги для обоих треков
            next_restored = self.temp_list[index+1].get("was_restored", False)
            current_restored = self.temp_list[index].get("was_restored", False)
            
            # Обмениваем треки местами
            self.temp_list[index], self.temp_list[index+1] = self.temp_list[index+1], self.temp_list[index]
            
            # Помечаем перемещенные треки
            self.temp_list[index+1]['was_moved'] = True
            # Если трек был восстановлен, меняем тег на moved_restored
            if next_restored:
                self.temp_list[index+1]['was_restored'] = False
                self.temp_list[index]['was_restored'] = True
        
        self.display_tracks = self.temp_list
        
        # Перед обновлением сохраняем новые индексы выбранных элементов (со смещением на +1)
        new_selection_indices = [i+1 for i in positions]
        self.update_display(selection_indices=new_selection_indices)
        
        self.show_message(self.localization.tr("moved_down"), "green")
        self.manual_edit = True
        self.update_undo_redo_buttons()
        self.save_state()
        

    def delete_tracks(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        if self.temp_list is None:
            self.temp_list = []
            for track in self.display_tracks:
                new_track = track.copy()
                new_track["was_modified"] = track.get("was_modified", False)
                new_track["was_restored"] = track.get("was_restored", False)  # Сохраняем флаг восстановления
                self.temp_list.append(new_track)
        
        indices = sorted([self.tree.index(item) for item in selected], reverse=True)
        for index in indices:
            del self.temp_list[index]
        
        self.display_tracks = self.temp_list
        self.update_display()
        self.show_message(
            self.localization.tr("deleted_tracks").format(count=len(selected)), 
            "green"
        )
        self.manual_edit = True
        self.update_undo_redo_buttons()
        self.save_state()
        
    
          
    def update_display(self, selection_indices=None):
        """Обновляет отображение треков в таблице с правильной нумерацией"""
        self.tree.delete(*self.tree.get_children())  # Очищаем таблицу
        
        # Настраиваем теги для разных состояний треков
        self.tree.tag_configure('modified', background='#FFFACD')  # Светло-желтый - измененные пути
        self.tree.tag_configure('moved', background='#D5E8D4')    # Светло-зеленый - перемещенные треки
        self.tree.tag_configure('restored', background='#FFCCCB') # Светло-красный - восстановленные треки
        self.tree.tag_configure('modified_moved', background='#E6D5FF') # Комбинация modified + moved E6D5FF
        self.tree.tag_configure('modified_restored', background='#FFD5E6') # Комбинация modified + restored FFD5E6
        self.tree.tag_configure('moved_restored', background='#D5F0FF') # Комбинация moved + restored D5F0FF
        self.tree.tag_configure('all', background='#E0E0E0') # Все три состояния

        # Вставляем треки с правильной нумерацией (начиная с 1)
        for i, track in enumerate(self.display_tracks, 1):
            item = self.tree.insert('', 'end', values=(i, track['name']))
            
            # Определяем теги в зависимости от состояния трека
            tags = []
            is_modified = track.get('was_modified', False)
            is_moved = track.get('was_moved', False)
            is_restored = track.get('was_restored', False)
            
            # Комбинируем теги для всех возможных сочетаний
            if is_modified and is_moved and is_restored:
                tags.append('all')
            elif is_modified and is_moved:
                tags.append('modified_moved')
            elif is_modified and is_restored:
                tags.append('modified_restored')
            elif is_moved and is_restored:
                tags.append('moved_restored')
            elif is_modified:
                tags.append('modified')
            elif is_moved:
                tags.append('moved')
            elif is_restored:
                tags.append('restored')
            
            if tags:
                self.tree.item(item, tags=tuple(tags))
            print(f"[TRACK] {i}. {track['name']}    —   —   —   —   —   {tags}")
        print(f"[DEBUG] Таблица обновлена")
        # Восстанавливаем выделение если указаны индексы
        if selection_indices is not None:
            children = self.tree.get_children()
            for idx in selection_indices:
                if 0 <= idx < len(children):
                    self.tree.selection_add(children[idx])
        
        # Обновляем внутренние списки
        self.full_paths = [t["path"] for t in self.display_tracks]
        self.display_names = [t["name"] for t in self.display_tracks]
        
    
    def save_initial_state(self):
        """Явно сохраняет начальное состояние"""
        if not hasattr(self, 'display_tracks') or not self.display_tracks:
            return
            
        initial_state = {
            'tracks': [track.copy() for track in self.display_tracks],
            'selection': []
        }
        
        self.history = [initial_state]
        self.history_index = 0
        self.update_undo_redo_buttons()
        print("[HISTORY] Начальное состояние сохранено")

    def save_state(self, force_save=False):
        """Сохраняет текущее состояние с улучшенной логикой"""
        # Создаем глубокую копию текущего состояния
        current_state = {
            'tracks': [{
                'path': track['path'],
                'name': track['name'],
                'num': track['num'],
                'original_path': track.get('original_path', track['path']),
                'was_modified': track.get('was_modified', False),
                'was_moved': track.get('was_moved', False)  # Сохраняем состояние перемещения
            } for track in self.display_tracks],
            'selection': list(self.tree.selection())
        }
        
        # Проверяем, нужно ли сохранять (если не force_save и состояние не изменилось)
        if not force_save and self.history and self.compare_states(self.history[self.history_index], current_state):
            return
        
        # Если мы не в конце истории (после undo), удаляем будущие состояния
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        
        # Добавляем новое состояние
        self.history.append(current_state)
        self.history_index = len(self.history) - 1
        
        # Ограничиваем размер истории
        if len(self.history) > 50:
            self.history.pop(0)
            self.history_index -= 1
        
        self.update_undo_redo_buttons()
        print(f"[HISTORY] Состояние сохранено (всего: {len(self.history)}, позиция: {self.history_index})")
    
    def compare_states(self, state1, state2):
        """Сравнивает два состояния треков"""
        if len(state1['tracks']) != len(state2['tracks']):
            return False
        
        for t1, t2 in zip(state1['tracks'], state2['tracks']):
            if (t1['path'] != t2['path'] or 
                t1['name'] != t2['name'] or
                t1['original_path'] != t2['original_path'] or
                t1['was_modified'] != t2['was_modified']):
                return False
        return True


    def restore_state(self, state):
        """Восстанавливает состояние с полным обновлением интерфейса"""
        # Получаем текущие пути перед восстановлением
        current_names = {track['name'] for track in self.display_tracks} if self.display_tracks else set()
        
        # Обновляем основной список
        self.display_tracks = []
        for track in state['tracks']:
            new_track = track.copy()
            # Помечаем восстановленные треки (те, которых не было в current_paths)
            if track['name'] not in current_names:
                new_track['was_restored'] = True
                
            else:
                # Сохраняем существующий флаг restored если он есть
                existing_track = next((t for t in self.display_tracks if t['name'] == track['name']), None)
                if existing_track and existing_track.get('was_restored', False):
                    new_track['was_restored'] = True
            self.display_tracks.append(new_track)
        
        # Обновляем временный список если он существует
        if self.temp_list is not None:
            self.temp_list = self.display_tracks.copy()
        
        self.update_display()
        
        # Восстанавливаем выделение
        if state['selection']:
            try:
                self.tree.selection_set(state['selection'])
            except tk.TclError:
                pass  # Игнорируем если элементы больше не существуют
                
            
    def undo_action(self):
        """Отменяет последнее действие с улучшенной логикой"""
        if self.history_index <= 0:
            self.show_message(self.localization.tr("nothing_to_undo"), "red")
            return
        
        self.history_index -= 1
        self.restore_state(self.history[self.history_index])
        self.show_message(self.localization.tr("action_undone"), "green")
        self.update_undo_redo_buttons()
        print(f"[DEBUG] Действие отменено")
        print(f"[HISTORY] Состояние: (всего: {len(self.history)}, позиция: {self.history_index})")

    def redo_action(self):
        """Повторяет отмененное действие с улучшенной логикой"""
        if self.history_index >= len(self.history) - 1:
            self.show_message(self.localization.tr("nothing_to_redo"), "red")
            return
        
        self.history_index += 1
        self.restore_state(self.history[self.history_index])
        self.show_message(self.localization.tr("action_redone"), "green")
        self.update_undo_redo_buttons()
        print(f"[DEBUG] Действие повторено")
        print(f"[HISTORY] Состояние: (всего: {len(self.history)}, позиция: {self.history_index})")
    
    def update_undo_redo_buttons(self):
        """Обновляет состояние кнопок с учетом новой логики"""
        self.undo_btn['state'] = 'normal' if self.history_index > 0 else 'disabled'
        self.redo_btn['state'] = 'normal' if self.history_index < len(self.history) - 1 else 'disabled'



    def update_internal_lists(self):
        """Обновляет внутренние списки на основе текущего состояния Treeview"""
        self.display_tracks = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if len(values) >= 2:
                track = {
                    "path": values[1],
                    "name": os.path.basename(values[1]),
                    "num": values[0],
                    "was_modified": 'modified' in self.tree.item(item, 'tags')
                }
                self.display_tracks.append(track)
        
        # Обновляем временный список, если он существует
        if self.temp_list is not None:
            self.temp_list = self.display_tracks.copy()


    def get_treeview_state(self):
        """Возвращает текущее состояние Treeview в унифицированном формате"""
        return [self.tree.item(item)['values'] for item in self.tree.get_children()]
    
    
    def show_message(self, text, color):
        """Обновляет поле сообщений"""
        self.seed_info.config(text=text, fg=color)    
        
        
    def update_seed_format(self, event=None):
        """Обновляет выбранный формат сида"""
        self.seed_format = self.seed_format_combobox.get()



    def generate_seed(self, num_tracks, date):
        """Генерация предсказуемого основного сида на основе даты и n!"""
        import _pylong
        sys.set_int_max_str_digits(0)
        try: 
            # Вычисляем факториал
            fact = math.factorial(num_tracks)
            print(f"[DEBUG] Факториал {num_tracks}! = {fact} \n===================================================================")
            
            # Немного усложнено: дата + количество треков + случайное число из списка
            date_part = int(date.timestamp())
            random_number = random.getrandbits(256)
            random_nbr = random.getrandbits(128)
            random_nbrr = random.getrandbits(64)
            random_nbrrr = random.getrandbits(4)
            number = [1, random_nbr, random_nbrr, 1, random_nbrrr]
            random_divisor = random.choice(number)
            result = (random_number // random_divisor)

            predictable_num = (date_part * num_tracks + result + 1) % fact
            
            print(f"[DEBUG] ГЕНЕРАЦИЯ ОСНОВНОГО СИДА \n=================================================================== \n Количество треков = {num_tracks} \n Дата = {date_part} \n Случайное число = {random_number} \n Делитель = {random_divisor} \n Разность = {result} \n Результат = {predictable_num}")
            # Форматируем в соответствии с выбранным форматом
            if self.seed_format_combobox.get() in ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                            "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "数字のみ", "Kun tal", "Endast siffror", "Vain numerot", "Slegs Syfers", "Chỉ số"]:
                return str(predictable_num).zfill(len(str(fact)))
            else:
                # Для буквенно-цифрового формата используем хеш
                hash_obj = hashlib.sha256(str(predictable_num).encode())
                print(f"[DEBUG] Хеш = {hash_obj}")
                return hash_obj.hexdigest()[:len(str(fact))]
        
        except Exception as e:
            self.seed_info.config(text=f"{self.localization.tr('error')}: {str(e)}", fg="red")
            print(f"[DEBUG] Ошибка: {str(e)}")

    def apply_reverse_step(self, files, step):
        """Реверс блоков (идентично генератору)"""
        reversed_files = files.copy()
        for i in range(0, len(reversed_files), step):
            reversed_files[i:i+step] = reversed(reversed_files[i:i+step])
        return reversed_files


    def shuffle_tracks(self):
        """Перемешивание с фиксированным результатом для одинакового сида"""
        import _pylong
        sys.set_int_max_str_digits(0)
        print(f"[DEBUG] ПРОЦЕСС ПЕРЕМЕШИВАНИЯ \n===================================================================")
        try:
            user_seed = self.seed_entry.get()
            step_value = self.step_entry.get()
            now = datetime.datetime.now()
        
            # Определяем базовый список для работы
            base_list = self.temp_list if self.temp_list is not None else self.original_list.copy()
            
            # Сохраняем текущие состояния restored и modified перед любыми изменениями
            track_states = {
                track['original_path']: {
                    'was_restored': track.get('was_restored', False),
                    'was_modified': track.get('was_modified', False),
                    'was_moved': track.get('was_moved', False),
                    'path': track['path'],
                    'name': track['name']
                } 
                for track in self.display_tracks.copy()
            }            
                             
            # Гарантируем наличие original_path и сохраняем флаги
            for track in base_list:
                if "original_path" not in track:
                    track["original_path"] = track["path"]
                    
                if track["original_path"] in self.modified_paths:
                    track["path"] = self.modified_paths[track["original_path"]]    
                    track["was_modified"] = True
                    
            # Сортируем по именам (A-Z)
            self.sorted_list = sorted(base_list, 
                            key=lambda x: (not x['name'][0].isalpha(), x['name'].lower()))
            
            num_tracks = len(self.sorted_list)
            self.temp_list = None  # Сбрасываем временный список после сортировки
            
            # Генерация сидов
            if not user_seed or user_seed == "0":
                seed = self.generate_seed(num_tracks, now)
            else:
                seed = user_seed
            
            
            # Обрезаем нули
            seed_trimmed = seed.lstrip('0') or '0'
            
            
            print(f"[DEBUG] Сид = {seed}")
            
            print(f"[DEBUG] Использованный сид = {seed_trimmed}")
           
            # Перемешиваем sorted_list
            tracks = [track.copy() for track in self.sorted_list]  # Глубокое копирование
            self.shuffled_list = self.soft_shuffle(tracks, str(seed_trimmed))
            
                
            # Применяем реверс если нужно
            step = 0
            if step_value.strip():
                try:
                    step = int(step_value)
                    if 0 < step <= 20:
                        # Реверсируем блоки в shuffled_list
                        print(f"[DEBUG] Реверс = {step}")
                        for i in range(0, len(self.shuffled_list), step):
                            self.shuffled_list[i:i+step] = reversed(self.shuffled_list[i:i+step])
                except ValueError:
                    self.seed_info.config(text=self.localization.tr("error_reverse_step"), fg="red")
                    return
            
            
            # Восстанавливаем все состояния после перемешивания
            for track in self.shuffled_list:
                original_path = track["original_path"]
                
                # Восстанавливаем сохраненные состояния
                if original_path in track_states:
                    saved_state = track_states[original_path]
                    track["was_modified"] = saved_state['was_modified']
                    track["was_moved"] = saved_state['was_moved']
                    track["was_restored"] = saved_state['was_restored']
                    
                    # Для модифицированных треков сохраняем новый путь
                    if track["was_modified"] and original_path in self.modified_paths:
                        track["path"] = self.modified_paths[original_path]
                
                # Удаляем временный флаг перемещения (если был установлен при сортировке)
                if 'was_moved' in track and not track['was_moved']:
                    del track['was_moved']
                
                
                    
            # Обновляем отображение
            self.display_tracks = self.shuffled_list
            self.update_display()
            
            # Обновляем информацию о сиде
            self.current_seed = seed_trimmed
            self.current_reverse_step = step if step > 0 else None
                    
            print(f"[DEBUG] Перемешивание завершено")
            
            self.save_state()
            # Показываем сообщение
            if step > 0:
                info_text = self.localization.tr("editor_seed_info_step").format(seed=seed_trimmed, step=step)
            else:
                info_text = self.localization.tr("editor_seed_info_basic").format(seed=seed_trimmed)
            
            self.seed_info.config(text=info_text, fg="green")
            
            
        except Exception as e:
            self.seed_info.config(text=f"{self.localization.tr('error')}: {str(e)}", fg="red")
            print(f"[DEBUG] Ошибка: {str(e)}") 
            
            
    def shuffle_files(self, files, seed_value):
        """Перемешивание с небольшими изменениями"""
        random.seed(abs(self.stable_hash(str(seed_value))))
        files = files.copy()
        random.shuffle(files)        
        return files


    def soft_shuffle(self, files, seed_value, intensity=None):
        """Перемешивание с небольшими изменениями"""
        seed_hash = abs(self.stable_hash(str(seed_value)))
        random.seed(seed_hash)
        files = files.copy()
        
        # Генерация intensity из сида, если не задано
        if intensity is None:
            # Используем хеш сида как основу для 0.6-1.0
            hash_ratio = (seed_hash % 10_000_000_000) / 10_000_000_000  # 0.0-0.999...
            intensity = 0.6 + 0.3 * hash_ratio  # Растягиваем на диапазон 0.6-1.0
        else:
            # Ограничиваем ручной ввод с сохранением точности
            intensity = max(0.6, min(1.0, float(intensity)))
            
        # Количество перестановок = 30% от числа треков (можно регулировать)
        num_swaps = max(0, int(len(files) * intensity))
        print(f"[DEBUG] Генерация intensity из сида = {intensity}")
        print(f"[DEBUG] Количество перестановок = {num_swaps}")
        for _ in range(num_swaps):
            i, j = random.sample(range(len(files)), 2)
            files[i], files[j] = files[j], files[i]
            print(f"[DEBUG] Перемешано {i}<->{j}")
        return files



    def save_playlist(self):
        """Сохранение плейлиста с учетом текущего состояния"""
        try:
            # Определяем, какие треки использовать для сохранения
            if self.shuffled_list is not None:
                # Если было перемешивание - используем перемешанный список
                source_list = self.shuffled_list
            
            elif self.temp_list is not None:
                # Если было ручное редактирование - используем временный список
                source_list = self.temp_list
            
            else:
                # Если не было ни перемешивания, ни редактирования - используем оригинальный порядок
                source_list = self.original_list

            for track in source_list:
                if 'was_moved' in track:
                    del track['was_moved'] 
                    
            current_tracks = []
            
            for idx, track in enumerate(source_list, 1):

                
                current_tracks.append({
                    "path": track["path"],
                    "name": os.path.basename(track["path"]),
                    "num": idx,
                    "original_path": track.get("original_path", track["path"]),  # Сохраняем оригинальный путь
                    "was_modified": track.get("was_modified", False),
                    "was_moved": track.get("was_moved", False),  # Сохраняем состояние перемещения
                    "was_restored": track.get("was_restored", False)  # Сохраняем состояние восстановления
                })
            
            if not current_tracks:
                raise ValueError(self.localization.tr("error_no_tracks"))
                
            playlist_name = self.name_entry.get().strip()
            if not playlist_name:
                raise ValueError(self.localization.tr("error_no_playlist_name"))
            
            # Определяем путь для сохранения
            script_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
                      else os.path.dirname(os.path.abspath(__file__))
            # Получаем выбранный формат
            playlist_format = self.format_m3u8
            if not playlist_format:  # Защита на случай пустого значения
                playlist_format = "m3u8"    
                
            save_path = os.path.join(script_dir, f"{playlist_name}.{playlist_format}")
            
            # Записываем файл
            if playlist_format in ["m3u8", "m3u"]:  
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    f.write("#Made with VolfLife's Playlist Generator\n")
                    f.write(f"#GENERATED:{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"#PLAYLIST:{playlist_name}\n")
                    
                    # Добавляем информацию о сиде только если было перемешивание
                    if self.shuffled_list is not None and hasattr(self, 'current_seed'):
                        f.write(f"#SEED:{self.current_seed}\n")
                        if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                            f.write(f"#REVERSE_STEP:{self.current_reverse_step}\n")
                    
                    f.write(f"#TRACKS:{len(current_tracks)}\n\n")
                    
                    for track in current_tracks:
                        f.write(f"#EXTINF:-1,{track['name']}\n")
                        escaped_path = track['path'].replace('\\', '/')
                        f.write(f"{escaped_path}\n")
                print(f"[DEBUG] Плейлист сохранен: {playlist_name}.{playlist_format}")
                
            if playlist_format in ["txt"]:  
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write("#Made with VolfLife's Playlist Generator\n")
                    f.write(f"#GENERATED:{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"#TRACKLIST:{playlist_name}\n")
                    
                    # Добавляем информацию о сиде только если было перемешивание
                    if self.shuffled_list is not None and hasattr(self, 'current_seed'):
                        f.write(f"#SEED:{self.current_seed}\n")
                        if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                            f.write(f"#REVERSE_STEP:{self.current_reverse_step}\n")
                    
                    f.write(f"#TRACKS:{len(current_tracks)}\n\n")
                    
                    for track in current_tracks:
                        escaped_path = track['path'].replace('\\', '/')
                        f.write(f"{escaped_path}\n")
                print(f"[DEBUG] Треклист сохранен: {playlist_name}.{playlist_format}") 
                
            # Обновляем temp_list с сохранением original_path
            if self.temp_list is None:
                self.temp_list = []
                for track in current_tracks:
                    new_track = track.copy()
                    new_track["original_path"] = track.get("original_path", track["path"])
                    self.temp_list.append(new_track)
            
            # Обновляем отображение из current_tracks, чтобы синхронизироваться
            self.display_tracks = current_tracks.copy()
            self.update_display()
            
            # Формируем сообщение
            message = self.localization.tr("playlist_saved").format(name=f"{playlist_name}.{playlist_format}")
            if self.shuffled_list is not None and hasattr(self, 'current_seed'):
                message += f" \n {self.localization.tr('seed_info_value')}: {self.current_seed}"
                if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                    message += f" \n {self.localization.tr('reverse_info_value')}: {self.current_reverse_step}"
            
            self.seed_info.config(text=message, fg="green")
            
        except Exception as e:
            self.seed_info.config(text=f"{self.localization.tr('error_save')}: {str(e)}", fg="red")
    

    
    def create_path_editor_window(self, event=None):
        """Создает окно для изменения путей выделенных треков"""
        if event:  # Если вызвано через клик мыши
            item = self.tree.identify_row(event.y)
            if item:
                if item not in self.tree.selection():
                    self.tree.selection_set(item)
        
        selected_items = self.tree.selection()
        if not selected_items:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        # Создаем модальное окно
        self.path_editor = tk.Toplevel(self.root)
        self.path_editor.title(self.localization.tr("edit_paths_window_title"))
        self.path_editor.transient(self.root)
        self.path_editor.grab_set()
        self.path_editor.resizable(False, False)
        
        # Центрируем окно
        window_width = 500
        window_height = 400
        screen_width = self.path_editor.winfo_screenwidth()
        screen_height = self.path_editor.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.path_editor.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Фрейм для таблицы
        table_frame = ttk.Frame(self.path_editor, padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Таблица с выделенными треками (только № и название)
        self.path_editor_tree = ttk.Treeview(table_frame, columns=('num', 'name'), show='headings')
        self.path_editor_tree.heading('num', text=self.localization.tr("track_number"))
        self.path_editor_tree.heading('name', text=self.localization.tr("track_name"))
        self.path_editor_tree.column('num', width=50, anchor='center')
        self.path_editor_tree.column('name', width=400, anchor='w')
        
        # Заполняем таблицу выделенными треками
        for item in selected_items:
            values = self.tree.item(item)['values']
            if len(values) >= 2:
                self.path_editor_tree.insert('', 'end', values=(values[0], values[1]))
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.path_editor_tree.yview)
        self.path_editor_tree.configure(yscrollcommand=scrollbar.set)
        
        self.path_editor_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Фрейм для поля ввода пути
        path_frame = ttk.Frame(self.path_editor, padding="10")
        path_frame.pack(fill=tk.X)
        
        ttk.Label(path_frame, text=self.localization.tr("new_path_label")).pack(anchor='w')
        

         # Поле ввода пути
        self.new_path_entry = ttk.Entry(path_frame)
        self.new_path_entry.pack(fill=tk.X, pady=5)
        
        # Кнопка "Обзор"
        browse_btn = ttk.Button(
            path_frame, 
            text=self.localization.tr("browse_button"), 
            width=10,
            command=self.browse_folder
        )
        browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        
        # Подсказка
        self.example = ttk.Frame(self.path_editor, padding="10")
        
        ttk.Label(path_frame, 
                 text=self.localization.tr("path_example_hint"), 
                 font=('TkDefaultFont', 8)).pack(side=tk.LEFT)
        
        # Фрейм для кнопок
        button_frame = ttk.Frame(self.path_editor, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, 
                  text=self.localization.tr("apply_button"), 
                  command=self.apply_new_paths).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, 
                  text=self.localization.tr("cancel_button"), 
                  command=self.path_editor.destroy).pack(side=tk.LEFT)
        
        # Сохраняем выбранные элементы
        self.selected_for_edit = selected_items
        
        # Автозаполнение пути из первого выделенного трека
        if selected_items:
            first_item = selected_items[0]
            values = self.tree.item(first_item)['values']
            if len(values) >= 2:
                path = os.path.dirname(values[1])
                self.new_path_entry.insert(0, path)


    def browse_folder(self):
        """Открывает диалог выбора папки и вставляет путь в поле ввода"""
        # Импортируем здесь, чтобы не замедлять запуск приложения
        from tkinter import filedialog
        
        # Вызываем стандартный диалог выбора папки
        folder_path = filedialog.askdirectory(
            title=self.localization.tr("select_folder_dialog_title")
        )
        
        # Если пользователь выбрал папку (не нажал "Отмена")
        if folder_path:
            # Вставляем путь в поле ввода
            self.new_path_entry.delete(0, tk.END)
            self.new_path_entry.insert(0, folder_path)
    
    
    def apply_new_paths(self):
        try:
            new_path = self.new_path_entry.get().strip()
            if not new_path:
                raise ValueError(self.localization.tr("error_empty_path"))
            
            new_path = os.path.normpath(new_path)
            if not new_path.endswith(os.sep):
                new_path += os.sep
            
            # Создаем временный список если его еще нет
            if self.temp_list is None:
                self.temp_list = [track.copy() for track in self.display_tracks]
            
            selected_indices = [self.tree.index(item) for item in self.selected_for_edit]
            
            for idx in selected_indices:
                track = self.temp_list[idx]
                original_path = track.get("original_path", track["path"])
                filename = os.path.basename(original_path)
                new_full_path = os.path.normpath(new_path + filename)
                
                # Обновляем словарь изменённых путей
                self.modified_paths[original_path] = new_full_path
                
                # Обновляем трек
                track["path"] = new_full_path
                track["name"] = filename
                track["was_modified"] = True
                track["was_restored"] = False
                track["original_path"] = original_path  # Сохраняем оригинальный путь
                
            self.display_tracks = self.temp_list.copy()
            self.update_display()
            self.save_state()
            
            # Сбрасываем перемешанную версию
            self.shuffled_list = None
            
            self.show_message(self.localization.tr("paths_updated"), "green")
            if self.path_editor:
                self.path_editor.destroy()
                self.path_editor = None
                
        except Exception as e:
            self.show_message(f"{self.localization.tr('error')}: {str(e)}", "red")

        
        
    def update_track_lists(self):
        """Обновляет внутренние списки треков на основе текущего состояния Treeview"""
        self.full_paths = []
        self.display_names = []
        
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if len(values) >= 2:
                self.full_paths.append(values[1])
                self.display_names.append(values[1])  # Используем полный путь для имени
        
        # Сохраняем изменения в оригинальных путях
        self.original_paths = self.full_paths.copy()
        