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
    def __init__(self, root, file_paths=None):
        self.root = root
        self.localization = Localization()
        self.visited_github = False
        self.github_link = None
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
            self.create_widgets()
            self.load_playlist()
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
                self.visited_github = settings.get('visited_github', False)
                if saved_lang and self.localization.is_language_supported(saved_lang):
                    self.localization.set_language(saved_lang)
                    print(f"[DEBUG] Загружен язык: {saved_lang}")
                else:
                    sys_lang = self.localization.detect_system_language()
                    self.localization.set_language(sys_lang)
                    # Для редактора не сохраняем, т.к. это может быть нежелательно
                
        except (FileNotFoundError, json.JSONDecodeError):
            sys_lang = self.localization.detect_system_language()
            self.localization.set_language(sys_lang)
            self.visited_github = False

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
        
        for i, file_path in enumerate(self.file_paths, 1):
            temp_list = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if file_path.lower().endswith('.txt'):
                                line = line.replace('"', '')
                            temp_list.append({
                                "path": line,
                                "name": os.path.basename(line),
                                "num": line_num,
                                "source": f"original_temp_list_{i}"  # Добавляем источник
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



    def create_widgets(self):
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
        message_frame = ttk.Frame(main_frame)
        message_frame.pack(fill=tk.X, pady=(10, 30))
        
        self.seed_info = tk.Label(
            message_frame,
            text="",
            fg="red",
            anchor="center"  # Центрирование текста
        )
        self.seed_info.pack(fill=tk.X, expand=True)
        
        
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
        
        
        # Обработчики drag-and-drop в Treeview
        self.tree.bind("<ButtonPress-1>", self.on_treeview_button_press)
        self.tree.bind("<B1-Motion>", self.on_treeview_mouse_move)
        self.tree.bind("<ButtonRelease-1>", self.on_treeview_button_release)
        
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
    
    
    
    def on_treeview_button_press(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            # Allow Ctrl for multi-selection: do not override selection if Ctrl is held
            if not (event.state & 0x0004) and item not in self.tree.selection():
                # If Ctrl not pressed and item not selected - select only this item
                self.tree.selection_set(item)
            # else keep current selection (allows Ctrl and Shift)
            self._drag_data["items"] = self.tree.selection()
            self._drag_data["y"] = event.y
        else:
            self._drag_data["items"] = None


    def on_treeview_mouse_move(self, event):
        if not self._drag_data["items"]:
            return
        y = event.y
        delta_y = y - self._drag_data["y"]
        if abs(delta_y) < 5:
            return
        children = list(self.tree.get_children())
        target_item = self.tree.identify_row(y)
        
        # Обрабатывать случай, когда курсор находится под всеми элементами — вставить в конец
        if target_item:
            try:
                target_index = children.index(target_item)
            except ValueError:
                return
        else:
            target_index = len(children)
        items = list(self._drag_data["items"])
        selected_indices = sorted(children.index(item) for item in items)
        
        # Если target_index находится внутри выбранных индексов, игнорировать перемещение
        if selected_indices and (target_index >= selected_indices[0] and target_index <= selected_indices[-1]):
            return
        if self.temp_list is None:
            self.temp_list = [track.copy() for track in self.display_tracks]
        moving_tracks = [self.temp_list[i] for i in selected_indices]
        
        
        # Удалить выбранное из temp_list в обратном порядке
        for i in reversed(selected_indices):
            del self.temp_list[i]
            
        # Отрегулируйте позицию вставки с учетом удаленных элементов перед целевым индексом
        adjustment = sum(1 for i in selected_indices if i < target_index)
        insert_index = target_index - adjustment
        
        # Зафиксировать insert_index в допустимом диапазоне
        if insert_index < 0:
            insert_index = 0
        elif insert_index > len(self.temp_list):
            insert_index = len(self.temp_list)
        for offset, track in enumerate(moving_tracks):
            self.temp_list.insert(insert_index + offset, track)
        self.display_tracks = self.temp_list.copy()
        new_selection_indices = list(range(insert_index, insert_index + len(moving_tracks)))
        self.update_display(selection_indices=new_selection_indices)
        children = self.tree.get_children()
        self._drag_data["items"] = [children[i] for i in new_selection_indices]
        self._drag_data["y"] = y


    def on_treeview_button_release(self, event):
        if self._drag_data["items"]:
            self.save_state()
        self._drag_data["items"] = None
        self._drag_data["y"] = 0
        
    
    
    def move_up(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        positions = sorted([int(self.tree.index(item)) for item in selected])
        if positions[0] == 0:
            return
        
        self.save_state()
        
        if self.temp_list is None:
            self.temp_list = [track.copy() for track in self.display_tracks]
        
        for index in positions:
            self.temp_list[index], self.temp_list[index-1] = self.temp_list[index-1], self.temp_list[index]
        
        self.display_tracks = self.temp_list
        
        # Перед обновлением сохранем новые индексы выбранных элементов (со смещением на -1)
        new_selection_indices = [i-1 for i in positions]
        self.update_display(selection_indices=new_selection_indices)
        
        self.show_message(self.localization.tr("moved_up"), "green")
        self.manual_edit = True
        self.update_undo_redo_buttons()



    def move_down(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        positions = sorted([int(self.tree.index(item)) for item in selected], reverse=True)
        max_index = len(self.tree.get_children()) - 1
        if positions[0] == max_index:
            return
        
        self.save_state()
        
        if self.temp_list is None:
            self.temp_list = [track.copy() for track in self.display_tracks]
        
        for index in positions:
            self.temp_list[index], self.temp_list[index+1] = self.temp_list[index+1], self.temp_list[index]
        
        self.display_tracks = self.temp_list
        
        # Перед обновлением сохранем новые индексы выбранных элементов (со смещением на +1)
        new_selection_indices = [i+1 for i in positions]
        self.update_display(selection_indices=new_selection_indices)
        
        self.show_message(self.localization.tr("moved_down"), "green")
        self.manual_edit = True
        self.update_undo_redo_buttons()

        

    def delete_tracks(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        self.save_state()
        
        if self.temp_list is None:
            self.temp_list = [track.copy() for track in self.display_tracks]
        
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
    
    
    def update_display(self, selection_indices=None):
        """Обновляет отображение треков в таблице с правильной нумерацией"""
        self.tree.delete(*self.tree.get_children())  # Очищаем таблицу
        
        # Вставляем треки с правильной нумерацией (начиная с 1)
        for i, track in enumerate(self.display_tracks, 1):
            print(f"Трек {i}: {track['name']} (ожидаемый номер: {i}, текущий номер: {track.get('num', 'N/A')})")
            self.tree.insert('', 'end', values=(i, track["name"]))
        
        # Обновляем внутренние списки
        self.full_paths = [t["path"] for t in self.display_tracks]
        self.display_names = [t["name"] for t in self.display_tracks]
        
        # Восстанавливаем выделение, если указаны индексы
        if selection_indices is not None:
            all_items = self.tree.get_children()
            for idx in selection_indices:
                if 0 <= idx < len(all_items):
                    self.tree.selection_add(all_items[idx])    
    
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



    def generate_seed(self, num_tracks, date):
        """Генерация предсказуемого основного сида на основе даты и n!"""
        sys.set_int_max_str_digits(0)
        # Вычисляем факториал
        fact = math.factorial(num_tracks)
        print(f"[DEBUG] Факториал {num_tracks}! = {fact}")
        
        # Немного усложнено: дата + количество треков + случайное число из списка
        date_part = int(date.timestamp())
        numbers = [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576]
        random_number = random.choice(numbers)
        predictable_num = (date_part * num_tracks * random_number) % fact
        
        print(f"[DEBUG] ГЕНЕРАЦИЯ ОСНОВНОГО СИДА \n=================================================================== \n Дата = {date_part} \n Число = {random_number} \n Количество треков = {num_tracks} \n Результат = {predictable_num}")
        # Форматируем в соответствии с выбранным форматом
        if self.seed_format_combobox.get() in ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                        "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만"]:
            return str(predictable_num).zfill(len(str(fact)))
        else:
            # Для буквенно-цифрового формата используем хеш
            hash_obj = hashlib.sha256(str(predictable_num).encode())
            return hash_obj.hexdigest()[:len(str(fact))]


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
            
            
            print(f"[DEBUG] Основной сид = {seed}")
            
            print(f"[DEBUG] Использованный основной сид = {seed_trimmed}")
           
            # Настраиваем генератор случайных чисел
            random.seed(abs(self.stable_hash(seed_trimmed)))
                        
            # Перемешиваем sorted_list
            self.shuffled_list = self.sorted_list.copy()
            random.shuffle(self.shuffled_list)
            
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
            
            # Обновляем отображение
            self.display_tracks = self.shuffled_list
            self.update_display()
            
            # Обновляем информацию о сиде
            self.current_seed = seed_trimmed
            self.current_reverse_step = step if step > 0 else None
                      
            
            # Показываем сообщение
            if step > 0:
                info_text = self.localization.tr("seed_info_step").format(seed=seed_trimmed, step=step)
            else:
                info_text = self.localization.tr("seed_info_basic").format(seed=seed_trimmed)
            
            self.seed_info.config(text=info_text, fg="green")
            
        except Exception as e:
            self.seed_info.config(text=f"{self.localization.tr('error')}: {str(e)}", fg="red")
                
        

    def save_playlist(self):
        """Сохранение плейлиста с учетом текущего состояния"""
        try:
            # Берём актуальные треки из внутреннего списка отображения, а не из Treeview напрямую,
            # чтобы сохранить корректные пути.
            current_tracks = []
            # Если есть temp_list (временный список после ручного редактирования), берем его,
            # иначе берем display_tracks
            source_list = self.temp_list if self.temp_list is not None else self.display_tracks
            
            for idx, track in enumerate(source_list, 1):
                # Перенумеруем треки
                current_tracks.append({
                    "path": track["path"],
                    "name": os.path.basename(track["path"]),
                    "num": idx
                })
            
            if not current_tracks:
                raise ValueError(self.localization.tr("error_no_tracks"))
                
            playlist_name = self.name_entry.get().strip()
            if not playlist_name:
                raise ValueError(self.localization.tr("error_no_playlist_name"))
            
            # Определяем путь для сохранения
            script_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
                      else os.path.dirname(os.path.abspath(__file__))
            save_path = os.path.join(script_dir, f"{playlist_name}.m3u8")
            
            # Записываем файл
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
                    f.write(f"{track['path']}\n")
            
            # Обновляем внутренние списки
            if self.temp_list is None:
                self.temp_list = current_tracks.copy()
            
            # Обновляем отображение из current_tracks, чтобы синхронизироваться
            self.display_tracks = current_tracks.copy()
            self.update_display()
            
            # Формируем сообщение
            message = self.localization.tr("playlist_saved").format(name=f"{playlist_name}.m3u8")
            if self.shuffled_list is not None and hasattr(self, 'current_seed'):
                message += f" | {self.localization.tr('seed_info_value')}: {self.current_seed}"
                if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                    message += f" | {self.localization.tr('reverse_info_value')}: {self.current_reverse_step}"
            
            self.seed_info.config(text=message, fg="green")
            
        except Exception as e:
            self.seed_info.config(text=f"{self.localization.tr('error_save')}: {str(e)}", fg="red")
    
    def update_track_lists(self):
        self.full_paths = []
        self.display_names = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if len(values) >= 2:
                self.full_paths.append(values[1])
                self.display_names.append(values[1])
        self.original_paths = self.full_paths.copy()
    
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
        """Применяет новый путь к выбранным трекам и сохраняет в temp_list"""
        try:
            new_path = self.new_path_entry.get().strip()
            if not new_path:
                raise ValueError(self.localization.tr("error_empty_path"))
            
            # Нормализуем путь
            new_path = os.path.normpath(new_path)
            if not new_path.endswith(os.sep):
                new_path += os.sep
            
            # Сохраняем текущее состояние для undo
            self.save_state()
            
            # Создаем/обновляем temp_list
            if self.temp_list is None:
                # Берем копию текущих треков с корректными путями
                self.temp_list = [track.copy() for track in self.display_tracks]
            
            # Получаем индексы выбранных элементов в Treeview
            selected_items = self.selected_for_edit  # селекты заранее сохранены
            selected_indices = [self.tree.index(item) for item in selected_items]
            
            # Обновляем пути выбранных треков по индексам
            for idx in selected_indices:
                old_track = self.temp_list[idx]
                filename = os.path.basename(old_track["path"])
                new_full_path = os.path.normpath(new_path + filename)
                self.temp_list[idx]["path"] = new_full_path
                self.temp_list[idx]["name"] = filename
            
            # Обновляем отображение из temp_list
            self.display_tracks = self.temp_list.copy()
            self.update_display()
            
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
        