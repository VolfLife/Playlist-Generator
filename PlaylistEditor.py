import os
import sys
import random
import datetime
import hashlib
import math
import string
import json
import locale
import time
import uuid
import urllib.parse
import xml.sax.saxutils as saxutils
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from Localization import Localization
from FontLoader import FontLoader            

class PlaylistEditor:
    def __init__(self, root, file_paths=None):
        self.root = root
        self.font_loader = FontLoader()		
        self.icon_path = self.font_loader.icon_ico
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
        self.deleted_tracks_history = []  # Инициализируем историю удалений
        self.deleted_tracks_map = {}      # Словарь для быстрого поиска по ключам
        self.del_id_counter = 0           # Счетчик для генерации уникальных ID        
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
        self.current_swaps = None
        self.seed_format = self.localization.tr("seed_formats")[0]  # По умолчанию
        self.selected_for_edit = []
        
        try:
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
        
        self.root.iconbitmap(self.icon_path)

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
                if saved_format in ["m3u8", "m3u", "pls", "txt", "xspf", "asx", "xspf+url", "json", "wpl", "xml"]:
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
        self.root.minsize(540, 738)

        
    def load_playlist(self):
        """Загружает несколько плейлистов и объединяет их"""
        import urllib
        supported_formats = {
                # Аудио
                '.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.wma', '.opus', '.aiff', '.aif', '.alac', '.dsf', '.dff', '.mka', '.ac3', '.dts',
                # Видео
                '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.3gp', '.vob', '.ogv'
            }
        for i, file_path in enumerate(self.file_paths, 1):
            temp_list = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    ext = os.path.splitext(file_path)[1].lower()
                    
                    if ext in ('.m3u', '.m3u8', '.txt'):
                        # Обработка M3U/M3U8/TXT форматов
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if line and not line.startswith('#'):
                                clean_path = line.strip('"\' \t')
                                if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                    continue
                                normalized_path = os.path.normpath(clean_path).replace('\\', '/').strip('"\' \t')
                                temp_list.append({
                                    "path": normalized_path,
                                    "name": os.path.basename(normalized_path),
                                    "num": line_num,
                                    "source": f"original_temp_list_{i}",
                                    "original_path": normalized_path,
                                    "was_modified": False,
                                    "track_id": None
                                })
                    
                    elif ext in ('.pls'):
                        # Обработка PLS формата
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line or line.startswith(';') or line.startswith('['):
                                continue
                                
                            if line.lower().startswith('file'):
                                # Извлекаем путь к файлу
                                _, file_path_pls = line.split('=', 1)
                                clean_path = file_path_pls.strip('"\' \t')
                                if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                    continue
                                normalized_path = os.path.normpath(clean_path).replace('\\', '/')
                                
                                temp_list.append({
                                    "path": normalized_path,
                                    "name": os.path.basename(normalized_path),
                                    "num": line_num,
                                    "source": f"original_temp_list_{i}",
                                    "original_path": normalized_path,
                                    "was_modified": False,
                                    "track_id": None
                                })
                    
                    elif ext in ('.asx'):
                        # Обработка ASX формата
                        try:
                            from xml.etree import ElementTree as ET
                            tree = ET.parse(file_path)
                            root = tree.getroot()
                            
                            for entry_num, entry in enumerate(root.findall('.//Entry'), 1):
                                ref = entry.find('Ref')
                                if ref is not None:
                                    href = ref.get('href', '').strip()
                                    if not href:
                                        continue
                                    
                                    # Декодирование URL-encoded путей (если нужно)
                                    clean_path = urllib.parse.unquote(href) if '%' in href else href
                                    clean_path = os.path.normpath(clean_path).replace('\\', '/').strip('"\' \t')
                                    
                                    if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                        continue
                                    
                                    # Получаем название трека из тега Title или из имени файла
                                    title = entry.findtext('Title', '').strip() or os.path.basename(clean_path)
                                    
                                    temp_list.append({
                                        "path": clean_path,
                                        "name": saxutils.unescape(title),  # Декодируем XML-entities
                                        "num": entry_num,
                                        "source": f"original_temp_list_{i}",
                                        "original_path": clean_path,
                                        "was_modified": False,
                                        "track_id": None
                                    })
                                    
                        except ET.ParseError as e:
                            print(f"[ERROR] Ошибка разбора ASX файла {file_path}: {str(e)}")
                        except Exception as e:
                            print(f"[ERROR] Ошибка обработки ASX файла {file_path}: {str(e)}")
                    
                    elif ext == '.xspf':
                        # Обработка XSPF формата
                        import xml.etree.ElementTree as ET
                        import re
                        
                        try:
                            # Сначала читаем файл как текст и экранируем проблемные символы
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Заменяем неэкранированные амперсанды (кроме XML-сущностей)
                            content = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;|\#\d+;)', '&amp;', content)
                            
                            # Парсим исправленный XML
                            root = ET.fromstring(content)
                            ns = {'ns': 'http://xspf.org/ns/0/'}
                            
                            for track_num, track in enumerate(root.findall('.//ns:track', ns), 1):
                                location_element = track.find('ns:location', ns)
                                
                                if location_element is None or not location_element.text:
                                    print(f"Warning: Empty <location> in track {track_num}")
                                    continue
                                
                                # Получаем и очищаем location
                                location = location_element.text.strip()
                                
                                # Сначала декодируем URL-кодирование
                                location = urllib.parse.unquote(location)
                                    
                                # Удаляем file:/// если присутствует (с учетом возможного file://)
                                if location.startswith(('file:///', 'file://')):
                                    location = re.sub(r'^file:///*', '', location)
                                  
                                location = urllib.parse.unquote(location)  # Декодируем URL-кодирование
                                
                                # Получаем название трека (если есть)
                                title = track.find('ns:title', ns)
                                display_name = os.path.basename(location)
                                
                                clean_path = location.strip('"\' \t')
                                
                                if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                    continue
                                
                                normalized_path = os.path.normpath(clean_path).replace('\\', '/')
                                temp_list.append({
                                    "path": normalized_path,
                                    "name": display_name,
                                    "num": track_num,
                                    "source": f"original_temp_list_{i}",
                                    "original_path": normalized_path,
                                    "was_modified": False,
                                    "track_id": None
                                })
                        except ET.ParseError as e:
                            print(f"[ERROR] Ошибка разбора XSPF файла {file_path}: {str(e)}")
                            continue
                    
                    
                    elif ext == '.wax':
                        # Обработка WAX формата (SMIL-based)
                        import xml.etree.ElementTree as ET
                        import re
                        import urllib.parse
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Экранируем специальные символы в XML
                            content = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;|\#\d+;)', '&amp;', content)
                            
                            # Парсим XML с учетом namespace
                            namespaces = {
                                'smil': 'http://www.w3.org/2001/SMIL20/Language'
                            }
                            root = ET.fromstring(content)
                            
                            track_num = 1
                            for media in root.findall('.//smil:media', namespaces):
                                if 'src' not in media.attrib or not media.attrib['src']:
                                    print(f"Warning: Empty src attribute in track {track_num}")
                                    continue
                                
                                # Обрабатываем путь
                                location = media.attrib['src'].strip()
                                
                                # Удаляем file:///
                                if location.startswith('file:///'):
                                    location = location[8:]  # Удаляем file:///
                                elif location.startswith('file://'):
                                    location = location[7:]  # Удаляем file://
                                
                                # Декодируем URL-кодирование
                                location = urllib.parse.unquote(location)
                                
                                # Получаем имя трека из параметров (если есть)
                                title = None
                                original_filename = None
                                for param in media.findall('smil:param', namespaces):
                                    if param.get('name') == 'title':
                                        title = param.get('value')
                                    elif param.get('name') == 'originalFilename':
                                        original_filename = param.get('value')
                                
                                # Определяем display_name
                                if title:
                                    display_name = title
                                elif original_filename:
                                    display_name = os.path.splitext(original_filename)[0]
                                else:
                                    display_name = os.path.basename(location)
                                
                                # Нормализуем путь
                                clean_path = os.path.normpath(location).replace('\\', '/')
                                
                                # Пропускаем неподдерживаемые форматы
                                if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                    continue
                                
                                # Добавляем трек в список
                                temp_list.append({
                                    "path": clean_path,
                                    "name": os.path.basename(location),
                                    "num": track_num,
                                    "source": f"original_temp_list_{i}",
                                    "original_path": clean_path,
                                    "was_modified": False,
                                    "track_id": None
                                })
                                
                                track_num += 1
                                
                        except ET.ParseError as e:
                            print(f"[ERROR] Ошибка разбора WAX файла {file_path}: {str(e)}")
                            continue
                        except Exception as e:
                            print(f"[ERROR] Ошибка обработки WAX файла {file_path}: {str(e)}")
                            continue                    
                    
                    
                    elif ext == '.wvx':
                        # Обработка WVX формата (SMIL-based)
                        import xml.etree.ElementTree as ET
                        import re
                        import urllib.parse
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Экранируем специальные символы в XML
                            content = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;|\#\d+;)', '&amp;', content)
                            
                            # Парсим XML
                            root = ET.fromstring(content)
                            
                            track_num = 1
                            for media in root.findall('.//media'):
                                if 'src' not in media.attrib or not media.attrib['src']:
                                    print(f"Warning: Empty src attribute in track {track_num}")
                                    continue
                                
                                # Обрабатываем путь
                                location = media.attrib['src'].strip()
                                
                                # Удаляем file:/// и декодируем URL
                                if location.startswith('file:///'):
                                    location = urllib.parse.unquote(location[8:])
                                elif location.startswith('file://'):
                                    location = urllib.parse.unquote(location[7:])
                                elif location.startswith(('http://', 'https://', 'mms://')):
                                    # Для онлайн-ресурсов оставляем как есть
                                    pass
                                else:
                                    location = urllib.parse.unquote(location)
                                
                                # Получаем метаданные
                                title = media.attrib.get('title')
                                artist = media.attrib.get('artist')
                                album = media.attrib.get('albumTitle')
                                
                                # Формируем отображаемое имя
                                if title and artist:
                                    display_name = f"{artist} - {title}"
                                elif title:
                                    display_name = title
                                else:
                                    display_name = os.path.basename(location)
                                
                                # Для локальных файлов нормализуем путь
                                if not location.startswith(('http://', 'https://', 'mms://')):
                                    clean_path = os.path.normpath(location).replace('\\', '/')
                                else:
                                    clean_path = location
                                
                                # Пропускаем неподдерживаемые форматы для локальных файлов
                                if not location.startswith(('http://', 'https://', 'mms://')):
                                    if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                        continue
                                
                                # Добавляем трек в список
                                temp_list.append({
                                    "path": clean_path,
                                    "name": os.path.basename(location),
                                    "num": track_num,
                                    "source": f"original_temp_list_{i}",
                                    "original_path": clean_path,
                                    "was_modified": False,
                                    "track_id": None,
                                    "metadata": {
                                        "artist": artist,
                                        "title": title,
                                        "album": album
                                    }
                                })
                                
                                track_num += 1
                                
                        except ET.ParseError as e:
                            print(f"[ERROR] Ошибка разбора WVX файла {file_path}: {str(e)}")
                            continue
                        except Exception as e:
                            print(f"[ERROR] Ошибка обработки WVX файла {file_path}: {str(e)}")
                            continue
                    
                    
                    elif ext == '.json':
                        # Обработка JSON формата
                        try:
                            playlist_data = json.load(f)
                            
                            # Проверяем структуру JSON
                            if not isinstance(playlist_data, dict):
                                raise ValueError("Invalid JSON playlist format: expected dictionary")
                            
                            # Получаем треки из разных возможных структур JSON
                            tracks = playlist_data.get('tracks') or playlist_data.get('items') or []
                            
                            for track in tracks:
                                # Поддержка разных форматов пути в JSON
                                file_path = track.get('path') or track.get('file') or track.get('location') or ''
                                
                                if not file_path:
                                    continue
                                
                                # Нормализация пути
                                clean_path = os.path.normpath(file_path.strip('"\' \t')).replace('\\', '/')
                                
                                # Проверка расширения файла
                                if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                    continue
                                
                                # Добавляем трек во временный список
                                temp_list.append({
                                    "path": clean_path,
                                    "name": os.path.basename(clean_path),
                                    "num": track.get('position') or track.get('track_number') or len(temp_list) + 1,
                                    "source": f"original_temp_list_{i}",
                                    "original_path": clean_path,
                                    "was_modified": False,
                                    "was_moved": False,
                                    "was_restored": False,
                                    "track_id": None,
                                    "original_name": track.get('title') or track.get('name') or os.path.basename(clean_path)
                                })
                        except json.JSONDecodeError as e:
                            print(f"[ERROR] Ошибка разбора JSON файла {filename}: {str(e)}")
                        except Exception as e:
                            print(f"[ERROR] Ошибка обработки JSON файла {filename}: {str(e)}")
                    
                    elif ext == '.wpl':
                        # Обработка WPL формата
                        try:
                            from xml.etree import ElementTree as ET
                            tree = ET.parse(file_path)
                            root = tree.getroot()
                            
                            # Находим все media-элементы в последовательности
                            for entry_num, media in enumerate(root.findall('.//media'), 1):
                                src = media.get('src', '').strip()
                                if not src:
                                    continue
                                
                                # Очистка пути (удаление лишних кавычек, пробелов)
                                clean_path = os.path.normpath(src).replace('\\', '/').strip('"\' \t')
                                
                                # Проверка поддерживаемого формата файла
                                if not any(clean_path.lower().endswith(ext) for ext in supported_formats):
                                    continue
                                
                                # Получаем название трека из атрибута title или имени файла
                                title = media.get('title', '').strip() or os.path.basename(clean_path)
                                
                                temp_list.append({
                                    "path": clean_path,
                                    "name": saxutils.unescape(title),  # Декодируем XML-entities
                                    "num": entry_num,
                                    "source": f"original_temp_list_{i}",
                                    "original_path": clean_path,
                                    "was_modified": False,
                                    "track_id": None
                                })
                                
                        except ET.ParseError as e:
                            print(f"[ERROR] Ошибка разбора WPL файла {file_path}: {str(e)}")
                        except Exception as e:
                            print(f"[ERROR] Ошибка обработки WPL файла {file_path}: {str(e)}")
        
        
                    elif ext == '.xml':
                        try:
                            from xml.etree import ElementTree as ET
                            import re
                            
                            # Читаем весь файл для обработки
                            content = f.read()
                            
                            # Экранируем невалидные XML-символы
                            content = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;|\#\d+;)', '&amp;', content)
                            
                            # Удаляем все meta-теги с rel="filename" до парсинга
                            content = re.sub(r'<meta\s+rel="filename"[^>]*>.*?</meta>', '', content, flags=re.IGNORECASE|re.DOTALL)
                            
                            try:
                                root = ET.fromstring(content)
                            except ET.ParseError:
                                # Пробуем добавить корневой тег для неполных XML
                                content = f'<root>{content}</root>'
                                root = ET.fromstring(content)
                            
                            # Словарь для хранения найденных треков
                            found_tracks = []
                            
                            # 1. Пытаемся обработать как iTunes Library
                            if root.find('.//dict/dict') is not None:
                                print("Detected iTunes Library format")
                                tracks = []
                                current_track = {}
                                
                                for elem in root.findall('.//dict/dict/dict'):
                                    key = None
                                    for child in elem:
                                        if child.tag == 'key':
                                            key = child.text
                                        elif key:
                                            current_track[key.lower()] = child.text if child.text else ''
                                            key = None
                                    
                                    if 'location' in current_track:
                                        location = current_track['location']
                                        location = re.sub(r'^file:///*', '', location)
                                        location = urllib.parse.unquote(location)
                                        location = os.path.normpath(location).replace('\\', '/').strip('"\' \t')
                                        
                                        name = current_track.get('name', os.path.basename(location))
                                        found_tracks.append((location, name))
                                    
                                    current_track = {}
                            
                            # 2. Пытаемся обработать как XSPF
                            elif root.find('.//track') is not None or root.find('.//Track') is not None:
                                print("Detected XSPF format")
                                for track in root.findall('.//track') + root.findall('.//Track'):
                                    location = None
                                    title = None
                                    
                                    # Получаем location
                                    loc_elem = track.find('location') or track.find('Location')
                                    if loc_elem is not None and loc_elem.text:
                                        location = loc_elem.text.strip()
                                        location = re.sub(r'^file:///*', '', location)
                                        location = urllib.parse.unquote(location)
                                        location = os.path.normpath(location).replace('\\', '/').strip('"\' \t')
                                    
                                    # Получаем title
                                    title_elem = track.find('title') or track.find('Title')
                                    if title_elem is not None and title_elem.text:
                                        title = title_elem.text.strip()
                                    
                                    if location:
                                        found_tracks.append((
                                            location,
                                            title if title else os.path.splitext(os.path.basename(location))[0]
                                        ))
                            
                            # 3. Общий поиск медиа-путей в XML
                            else:
                                print("Detected generic XML format")
                                def find_paths(element):
                                    paths = []
                                    # Проверяем атрибуты
                                    for attr, value in element.attrib.items():
                                        if any(value.lower().endswith(ext) for ext in supported_formats):
                                            clean_path = re.sub(r'^file:///*', '', value)
                                            clean_path = urllib.parse.unquote(clean_path)
                                            paths.append(clean_path)
                                    
                                    # Проверяем текст элемента
                                    if element.text and any(element.text.strip().lower().endswith(ext) for ext in supported_formats):
                                        clean_path = re.sub(r'^file:///*', '', element.text.strip())
                                        clean_path = urllib.parse.unquote(clean_path)
                                        paths.append(clean_path)
                                    
                                    # Рекурсивно проверяем дочерние элементы
                                    for child in element:
                                        paths.extend(find_paths(child))
                                    
                                    return paths
                                
                                paths = find_paths(root)
                                found_tracks = [(path, os.path.splitext(os.path.basename(path))[0]) for path in paths]
                            
                            # Добавляем найденные треки в temp_list
                            for track_num, (location, title) in enumerate(found_tracks, 1):
                                if any(location.lower().endswith(ext) for ext in supported_formats):
                                    normalized_path = os.path.normpath(location).replace('\\', '/').strip('"\' \t')
                                    temp_list.append({
                                        "path": normalized_path,
                                        "name": os.path.basename(location),
                                        "num": track_num,
                                        "source": f"original_temp_list_{i}",
                                        "original_path": normalized_path,
                                        "was_modified": False,
                                        "track_id": None
                                    })
                                    print(f"Added track: {title} | {normalized_path}")
                            
                            print(f"Total tracks added from XML: {len(temp_list)}")
                            
                        except Exception as e:
                            print(f"[ERROR] Ошибка загрузки XML плейлиста {file_path}: {str(e)}")
                            import traceback
                            traceback.print_exc()

        
                # Сохраняем отдельный список
                self.original_lists[f"original_temp_list_{i}"] = temp_list
                self.original_list.extend(temp_list)
                
                count = len(self.file_paths)
                self.seed_info.config(text=self.localization.tr("multiple_playlists_loaded").format(count=f"{count}"), fg="green")
                
            except Exception as e:
                print(f"[ERROR] Ошибка загрузки плейлиста {file_path}: {str(e)}")
                continue


        
        # Обновляем отображение
        self.display_tracks = self.original_list.copy()
        self.update_display()
        print(f"[DEBUG] Загружено плейлистов = {count}")
        self.save_initial_state()
        
        # Генерируем имя плейлиста
        if self.file_paths:
            base_name = os.path.basename(self.file_paths[0])
            for ext in ['.m3u8', '.m3u', '.txt', '.pls', '.xspf', '.asx', '.json', '.wax', '.wvx', '.wpl', '.xml']:
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
        
        self.base_list = None
        self.sorted_list = None
        self.shuffled_list = None
    

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


    def clear_search_entry(self, event=None):
        # Очищаем поле ввода и список папок, сохраняем настройки
        self.search_entry.delete(0, tk.END)
        
        # Сбрасываем флаг found у всех треков
        for track in self.display_tracks:
            track['found'] = False
        
        # Обновляем отображение
        self.update_display()
        self.hide_search_tooltip()
    
    
    def on_search_key_release(self, event):
        """Обработчик ввода текста в поле поиска"""
        search_term = self.search_entry.get().lower()
        if not search_term:
            for track in self.display_tracks:
                track['found'] = False
                track["modified"]: track.get("was_modified", False)
                track["name_modified"]: track.get("was_name_modified", False)
                track["moved"]: track.get("was_moved", False)
                track["restored"]: track.get("was_restored", False)
                track["track_id"]: track.get("track_id", None)
                track["added"]: track.get("added", False)
        else:
            # Обновляем флаг found у всех треков
            for track in self.display_tracks:
                track['found'] = search_term in track['name'].lower()
                track["modified"]: track.get("was_modified", False)
                track["name_modified"]: track.get("was_name_modified", False)
                track["moved"]: track.get("was_moved", False)
                track["restored"]: track.get("was_restored", False)
                track["track_id"]: track.get("track_id", None)
                track["added"]: track.get("added", False)
        # Обновляем отображение
        self.update_display()


    def add_tracks(self):
        """Добавляет поддерживаемые аудио и видео файлы из выбранного каталога"""
        from tkinter import filedialog
        
        # Открываем диалог выбора каталога
        folder_path = filedialog.askdirectory(title=self.localization.tr("select_folder_to_add_tracks"))
        if not folder_path:
            return  # Пользователь отменил выбор
            
        # Получаем список поддерживаемых форматов
        supported_formats = {
                # Аудио
                '.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac', '.wma', '.opus', '.aiff', '.aif', '.alac', '.dsf', '.dff', '.mka', '.ac3', '.dts',
                # Видео
                '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.3gp', '.vob', '.ogv'
            }
        
        try:
            # Сканируем каталог и находим поддерживаемые файлы
            new_tracks = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in supported_formats:
                        full_path = os.path.join(root, file)
                        normalized_path = os.path.normpath(full_path).replace('\\', '/')
                        
                        # Генерируем уникальный ID для трека
                        track_id = str(uuid.uuid4())
                    
                        new_track = {
                            "path": normalized_path,
                            "name": file,
                            "num": len(self.display_tracks) + len(new_tracks) + 1,
                            "track_id": track_id,
                            "source": "added_from_folder",
                            "original_path": normalized_path,
                            "was_modified": False,
                            "was_name_modified": False,
                            "was_moved": False,
                            "found": False
                        }
                        new_tracks.append(new_track)
            
            if not new_tracks:
                self.show_message(self.localization.tr("no_supported_files_found"), "red")
                return
                
            # Добавляем новые треки к текущему списку
            self.temp_list = [track.copy() for track in self.display_tracks]
            
            # Добавляем новые треки
            self.temp_list.extend(new_tracks)
            self.display_tracks = self.temp_list.copy()
            self.shuffled_list = None
            # Обновляем отображение
            self.update_display()
            self.save_state()
            count = len(new_tracks)
            # Показываем сообщение о успешном добавлении
            self.show_message(
                self.localization.tr("tracks_added_successfully").format(count=len(new_tracks)), 
                "green"
            )
            
        except Exception as e:
            self.show_message(f"{self.localization.tr('error_adding_tracks')}: {str(e)}", "red")
        
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
            self.root.title(self.localization.tr("window_title_editor"))
            # Обновляем текст
            self.playlist_name_label.config(text=self.localization.tr("playlist_name_label"))
            self.seed_label.config(text=self.localization.tr("seed_label"))
            self.swaps_label.config(text=self.localization.tr("intensity_label"))
            self.seed_format_label.config(text=self.localization.tr("seed_format_label"))
            self.reverse_label.config(text=self.localization.tr("reverse_step_label"))
            self.save_label.config(text=self.localization.tr("save_button"))
            self.shuffle_label.config(text=self.localization.tr("shuffle_button"))
            self.language_label.config(text=self.localization.tr("language_label"))        
            # Обновляем список форматов сида
            self.seed_format_combobox['values'] = self.localization.get_seed_format_options()

            # Генерируем имя плейлиста
            if self.file_paths:
                base_name = os.path.basename(self.file_paths[0])
                for ext in ['.m3u8', '.m3u', '.txt', '.pls', '.xspf', '.asx', '.json', '.wax', '.wvx', '.wpl', '.xml']:
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
            
            # Получаем текущее значение формата сида
            current_seed_format = self.seed_format_combobox.get()
            # Список форматов, при которых текущее значение не должно меняться
            numeric_formats = ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                            "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "数字のみ", "Kun tal", "Endast siffror", "Vain numerot", "Slegs Syfers", "Chỉ số", "Hanya angka", "Dhigití amháin", "Μόνο αριθμοί", "Само цифри", "Tik skaičiai", "Tikai cipari", "Numri biss", "Само бројки", "Iba číslice", "מספרים בלבד", "எண்கள் மட்டும்", "అంకెలు మాత్రమే", "Nombor sahaja", "ቁጥሮች ብቻ", "Nambari pekee", "Izinombolo kuphela"]
            # Проверяем, находится ли текущее значение в списке форматов
            if current_seed_format in numeric_formats:
                # Если текущее значение в списке, не меняем его
                self.seed_format_combobox['values'] = self.localization.get_seed_format_options()
                self.seed_format_combobox.current(0)
            else:
                # Если текущее значение не в списке, устанавливаем значение по умолчанию
                self.seed_format_combobox.current(1)  # Устанавливаем второе значение как значение по умолчанию
                
        
    
    def create_widgets(self, root):
        """Создает интерфейс редактора"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Используем загруженный шрифт
        style = ttk.Style(root)
        
        # Указываем только имя семейства шрифта (без объекта Font)
        style.configure('Symbol.TButton', 
                      font=(self.font_loader.symbol_font, 9),
                      padding=2)

        # Фрейм для поиска
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Поле поиска
        ttk.Label(search_frame, text="f", style='Symbol.TButton', width=3).pack(side=tk.LEFT, padx=(0, 5)) #self.localization.tr("search_label")
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", self.on_search_key_release)
        # Добавляем обработчик правой кнопки мыши для очистки
        self.search_entry.bind("<Button-3>", self.clear_search_entry)
        
        # Кнопка добавления треков
        add_tracks = ttk.Button(search_frame, text="g", style='Symbol.TButton', width=3, command=self.add_tracks)
        add_tracks.pack(side=tk.LEFT)
        
        # Добавляем подсказку при наведении курсора
        self.search_tooltip = tk.Label(self.root, text=self.localization.tr("tree_tooltip"), 
                                           bg="beige", relief="solid", borderwidth=1)
        self.search_tooltip.place_forget()
        self.search_entry.bind("<Enter>", self.show_search_tooltip)
        self.search_entry.bind("<Leave>", self.hide_search_tooltip)
        
        
        # Фрейм для таблицы с ползунком
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 5))
        table_frame.grid_propagate(False) 
        
        # Уменьшаем количество видимых строк в таблице на 1, чтобы компенсировать добавление поля поиска
        self.tree = ttk.Treeview(
            table_frame, 
            columns=('num', 'name'), 
            show='headings', 
            selectmode='extended',
            height=18  # Количество видимых строк (было 17)
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
        
        # Инициализируем таблицу
        self.update_display()        
        
        for i, name in enumerate(self.display_names, 1):
            self.tree.insert('', 'end', values=(i, name))
        
        # Фрейм для полей ввода
        manage_frame = ttk.Frame(main_frame)
        manage_frame.pack(fill=tk.X, pady=0)
        # Кнопки управления
        self.redo_btn = ttk.Button(
            manage_frame, 
            text="e", 
            width=17,
            style='Symbol.TButton',
            command=self.redo_action, 
            state='disabled'
            )
        self.redo_btn.pack(side=tk.RIGHT, padx=2)
        
        
        self.undo_btn = ttk.Button(
            manage_frame, 
            text="d", 
            width=17,
            style='Symbol.TButton',
            command=self.undo_action
            )
        self.undo_btn.pack(side=tk.RIGHT, padx=2)


        self.delete_btn = ttk.Button(
            manage_frame, 
            text="c", 
            width=19,
            style='Symbol.TButton',
            command=self.delete_tracks
            )
        self.delete_btn.pack(side=tk.RIGHT, padx=2)
        
        self.move_down_btn = ttk.Button(
            manage_frame, 
            text="b", 
            width=17,
            style='Symbol.TButton',
            command=self.move_down
            )
        self.move_down_btn.pack(side=tk.RIGHT, padx=2)


        self.move_up_btn = ttk.Button(
            manage_frame,
            text="a", 
            width=17, 
            style='Symbol.TButton',
            command=self.move_up
            )
        self.move_up_btn.pack(side=tk.RIGHT, padx=2)
        
        # Фрейм для полей ввода
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)

        # Настройка веса колонки для растягивания
        input_frame.columnconfigure(1, weight=1)  # Это важно для растягивания Entry полей

        # Поле имени плейлиста
        self.playlist_name_label = tk.Label(input_frame, text=self.localization.tr("playlist_name_label"))
        self.playlist_name_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.name_entry = ttk.Entry(input_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.name_entry.insert(0, self.playlist_name)

        self.name_entry.bind("<Button-3>", self.clear_playlist_entry)
        
        # Поле сида
        self.seed_label = tk.Label(input_frame, text=self.localization.tr("seed_label"))
        self.seed_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.seed_entry = ttk.Entry(input_frame)
        self.seed_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.seed_entry.bind("<Button-3>", self.clear_seed_entry)
        
        # Поле перестановок
        self.swaps_label = tk.Label(input_frame, text=self.localization.tr("intensity_label"))
        self.swaps_label.grid(
            row=2, column=0, sticky="w", padx=5, pady=3)
        self.intensity_entry = ttk.Entry(input_frame, width=10)  # Оставляем width=5 только для этого поля, если нужно
        self.intensity_entry.insert(0, "")
        self.intensity_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        self.intensity_entry.bind("<Button-3>", self.clear_intensity_entry)
        
        # Формат сида
        self.seed_format_label = tk.Label(input_frame, text=self.localization.tr("seed_format_label"))
        self.seed_format_label.grid(
            row=2, column=1, sticky="w", padx=85, pady=3)
              
        # Поле шага реверса
        self.reverse_label = tk.Label(input_frame, text=self.localization.tr("reverse_step_label"))
        self.reverse_label.grid(
            row=3, column=0, sticky="w", padx=5, pady=3)
        self.step_entry = ttk.Entry(input_frame, width=10)  # Оставляем width=5 только для этого поля, если нужно
        self.step_entry.insert(0, "")
        self.step_entry.grid(row=3, column=1, padx=5, pady=3, sticky="w")
        
        self.step_entry.bind("<Button-3>", self.clear_step_entry)
        
        # Ползунок формата сида
        self.seed_format_combobox = ttk.Combobox(
            input_frame, 
            values=self.localization.tr("seed_formats"), 
            state="readonly",
            width=18
        )
        self.seed_format_combobox.current(0)
        self.seed_format_combobox.grid(row=3, column=1, padx=85, pady=3, sticky="w")
        self.seed_format_combobox.bind("<<ComboboxSelected>>", self.update_seed_format)
        
        # Фрейм для кнопок
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 5))
        
        # Combobox формата
        self.format_combobox = ttk.Combobox(
            btn_frame,
            values=["m3u8", "m3u", "pls", "wpl", "asx", "xspf", "xspf+url", "json", "xml", "txt"],
            state="readonly",
            width=8
        )
        self.format_combobox.pack(side=tk.RIGHT, padx=12)
        self.format_combobox.set(self.format_m3u8)
        self.format_combobox.bind("<<ComboboxSelected>>", self.change_format)

        self.save_label = ttk.Button(btn_frame, text=self.localization.tr("save_button"), command=self.save_playlist)
        self.save_label.pack(side=tk.RIGHT, padx=5)
        self.shuffle_label = ttk.Button(btn_frame, text=self.localization.tr("shuffle_button"), command=self.shuffle_tracks)
        self.shuffle_label.pack(side=tk.RIGHT, padx=5)

        self.language_label = tk.Label(btn_frame, text=self.localization.tr("language_label"))
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
            btn_frame, 
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
        
        
        
        # Поле для сообщений
        message_frame = ttk.Frame(main_frame)
        message_frame.pack(fill=tk.X, pady=7)
        
        # Фиксируем высоту фрейма сообщений
        message_frame.pack_propagate(False)  # Отключаем автоматическое изменение размера
        message_frame.config(height=65)  # Устанавливаем фиксированную высоту
        
        self.seed_info = tk.Label(
            message_frame,
            text="",
            fg="green",
            justify="center"  # Выравнивание по центру при переносе строк
        )
        self.seed_info.pack(fill=tk.X, expand=False)
        
                
                
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

        
        
        
        # Добавляем подсказку при наведении курсора для сида
        self.seed_tooltip = tk.Label(self.root, text="", 
                                           bg="beige", relief="solid", borderwidth=1)
        self.seed_tooltip.place_forget()
        self.seed_entry.bind("<Enter>", self.show_seed_tooltip)
        self.seed_entry.bind("<Leave>", self.hide_seed_tooltip)
  
        # Добавляем подсказку при наведении курсора для перестановок
        self.swaps_tooltip = tk.Label(self.root, text="", 
                                           bg="beige", relief="solid", borderwidth=1)
        self.swaps_tooltip.place_forget()
        self.intensity_entry.bind("<Enter>", self.show_swaps_tooltip)
        self.intensity_entry.bind("<Leave>", self.hide_swaps_tooltip)
  
        # Добавляем подсказку при наведении курсора для реверса
        self.reverse_tooltip = tk.Label(self.root, text="", 
                                           bg="beige", relief="solid", borderwidth=1)
        self.reverse_tooltip.place_forget()
        self.step_entry.bind("<Enter>", self.show_reverse_tooltip)
        self.step_entry.bind("<Leave>", self.hide_reverse_tooltip)


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
        y = self.tree.winfo_y() + 424  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.tree_tooltip.place(x=x, y=y)

    def hide_tree_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'tree_tooltip'):
            self.tree_tooltip.place_forget()    
    
    def show_search_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = self.localization.tr("folder_entry_tooltip")
        self.search_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.search_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.tree.winfo_x()  # Позиция поля ввода
        entry_width = self.tree.winfo_width()  # Ширина поля
        tooltip_width = self.search_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + 20 + (entry_width - tooltip_width) // 2
        y = self.tree.winfo_y() + 31  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.search_tooltip.place(x=x, y=y)

    def hide_search_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'search_tooltip'):
            self.search_tooltip.place_forget()    

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
        y = self.seed_entry.winfo_y() + 479  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.seed_tooltip.place(x=x, y=y)

    def hide_seed_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'seed_tooltip'):
            self.seed_tooltip.place_forget()

    def show_swaps_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = " 0=off, 1=auto, 2-∞ "
        self.swaps_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.swaps_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.intensity_entry.winfo_x()  # Позиция поля ввода
        entry_width = self.intensity_entry.winfo_width()  # Ширина поля
        tooltip_width = self.swaps_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + 10 + (entry_width - tooltip_width) // 2
        y = self.intensity_entry.winfo_y() + 479  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.swaps_tooltip.place(x=x, y=y)

    def hide_swaps_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'swaps_tooltip'):
            self.swaps_tooltip.place_forget()
    
    def show_reverse_tooltip(self, event=None):
        # Получаем текущий текст подсказки
        tooltip_text = " 0=off, 1=auto, 2-∞ "
        self.reverse_tooltip.config(text=tooltip_text)
        
        # Принудительно обновляем геометрию для актуальных размеров
        self.reverse_tooltip.update_idletasks()
        
        # Рассчитываем позицию
        entry_x = self.step_entry.winfo_x()  # Позиция поля ввода
        entry_width = self.step_entry.winfo_width()  # Ширина поля
        tooltip_width = self.reverse_tooltip.winfo_reqwidth()  # Ширина подсказки
        
        # Центрируем подсказку относительно поля ввода
        x = entry_x + 10 + (entry_width - tooltip_width) // 2
        y = self.step_entry.winfo_y() + 479  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.reverse_tooltip.place(x=x, y=y)

    def hide_reverse_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'reverse_tooltip'):
            self.reverse_tooltip.place_forget()

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
        x = entry_x + 10 + (entry_width - tooltip_width) // 2
        y = self.language_dropdown.winfo_y() + 561  # Фиксированный отступ по Y
        
        # Устанавливаем позицию
        self.translation_tooltip.place(x=x, y=y)

    def hide_translation_tooltip(self, event=None):
        # Скрываем подсказку
        if hasattr(self, 'translation_tooltip'):
            self.translation_tooltip.place_forget()

    def clear_playlist_entry(self, event=None):
        self.name_entry.delete(0, tk.END)

    def clear_seed_entry(self, event=None):
        self.seed_entry.delete(0, tk.END)
    
    def clear_step_entry(self, event=None):
        self.step_entry.delete(0, tk.END)
    
    def clear_intensity_entry(self, event=None):
        self.intensity_entry.delete(0, tk.END)
    
    def select_all_tracks(self, event=None):
        """Выделяет все треки в таблице"""
        items = self.tree.get_children()
        if items:
            self.tree.selection_set(items)
        return "break"  # Предотвращаем дальнейшую обработку события


    def on_treeview_mouse_move(self, event):
        """Обработчик перемещения с разделением логики для одного и нескольких треков"""
        if not hasattr(self, '_drag_data') or not self._drag_data or not self._drag_data["items"]:
            return
        
        # ИСПРАВЛЕНИЕ: замена условия is_sorted
        # Старое условие (проблемное): 
        # is_sorted = any(track.get('found', False) for track in self.display_tracks)
        
        # Новое условие: проверяем только наличие активного поиска
        search_term = self.search_entry.get().strip()
        is_sorted = bool(search_term)  # True только если есть поисковый запрос
    
        y = event.y
        delta_y = y - self._drag_data["y"]
        if abs(delta_y) < 1:  # Минимальное перемещение
            return
        
        target_item = self.tree.identify_row(y)
        if not target_item:
            return
        
        visible_items = list(self.tree.get_children())
        
        # Для отсортированных списков: только один трек с обменом
        if is_sorted:
            # Если выделено больше одного трека - отменяем перемещение
            if len(self._drag_data["items"]) > 1:
                # Сбрасываем данные перетаскивания
                self._drag_data = {}
                return
            
            # Логика для перемещения одного трека в отсортированном списке
            y = event.y
            delta_y = y - self._drag_data["y"]
            if abs(delta_y) < 1:  # Минимальное перемещение
                return
            
            target_item = self.tree.identify_row(y)
            if not target_item:
                return
            
            visible_items = list(self.tree.get_children())
            try:
                target_index = visible_items.index(target_item)
                moving_indices = sorted([visible_items.index(item) for item in self._drag_data["items"]])
            except ValueError:
                return
            
            # Определяем направление перемещения
            is_moving_down = target_index > moving_indices[-1]
            is_moving_up = target_index < moving_indices[0]
            
            if not (is_moving_down or is_moving_up):
                return
            
            # Находим границы группы
            first_idx = moving_indices[0]
            last_idx = moving_indices[-1]
            
            # Определяем соседа для обмена
            if is_moving_down:
                neighbor_idx = last_idx + 1
            else:  # is_moving_up
                neighbor_idx = first_idx - 1
            
            # Проверяем границы
            if neighbor_idx < 0 or neighbor_idx >= len(visible_items):
                return
            
            # Получаем реальные индексы из display_tracks
            try:
                # Для выделенного элемента
                item = self._drag_data["items"][0]
                values = self.tree.item(item, 'values')
                if values and len(values) > 1:  # Проверяем, что есть имя
                    moving_real_index = int(values[0]) - 1
                    # Сохраняем имя перемещаемого трека
                    moving_name = values[1]
                
                # Для соседнего элемента
                neighbor_item = visible_items[neighbor_idx]
                neighbor_values = self.tree.item(neighbor_item, 'values')
                if not neighbor_values:
                    return
                neighbor_real_idx = int(neighbor_values[0]) - 1
            except:
                return
            
            # Создаем новую версию display_tracks
            new_display = [track.copy() for track in self.display_tracks]
            
            if is_moving_down:
                # Меняем местами с соседом снизу
                new_display[moving_real_index], new_display[neighbor_real_idx] = \
                    new_display[neighbor_real_idx], new_display[moving_real_index]
                
                # Обновляем номера
                new_display[moving_real_index]['num'] = moving_real_index + 1
                new_display[neighbor_real_idx]['num'] = neighbor_real_idx + 1
                
                # Помечаем как перемещенные
                #new_display[moving_real_index]['was_moved'] = True
                new_display[neighbor_real_idx]['was_moved'] = True
                
            else:  # is_moving_up
                # Меняем местами с соседом сверху
                new_display[moving_real_index], new_display[neighbor_real_idx] = \
                    new_display[neighbor_real_idx], new_display[moving_real_index]
                
                # Обновляем номера
                new_display[moving_real_index]['num'] = moving_real_index + 1
                new_display[neighbor_real_idx]['num'] = neighbor_real_idx + 1
                
                # Помечаем как перемещенные
                #new_display[moving_real_index]['was_moved'] = True
                new_display[neighbor_real_idx]['was_moved'] = True
            
            # Применяем изменения
            self.display_tracks = new_display
            self.temp_list = self.display_tracks
            self.shuffled_list = None
            self._drag_data["y"] = y
            
            # Обновляем отображение
            self.update_display()
            
            # Восстанавливаем выделение по имени трека
            self._restore_selection_by_identifiers(self._drag_data["identifiers"])
        
        else:
            # Для неотсортированных списков
            try:
                target_index = visible_items.index(target_item)
                moving_indices = sorted([visible_items.index(item) for item in self._drag_data["items"]])
            except ValueError:
                return
            
            # Разделяем логику для одного и нескольких треков
            if len(self._drag_data["items"]) == 1:
                # Логика для одного трека (старая реализация)
                # Определяем направление перемещения
                is_moving_down = target_index > moving_indices[-1]
                is_moving_up = target_index < moving_indices[0]
                
                if not (is_moving_down or is_moving_up):
                    return
                
                # Находим соседа для обмена
                if is_moving_down:
                    neighbor_idx = moving_indices[-1] + 1
                else:  # is_moving_up
                    neighbor_idx = moving_indices[0] - 1
                
                # Проверяем границы
                if neighbor_idx < 0 or neighbor_idx >= len(visible_items):
                    return
                
                # Получаем реальные индексы
                try:
                    # Для выделенного элемента
                    item = self._drag_data["items"][0]
                    values = self.tree.item(item, 'values')
                    if values and len(values) > 1:  # Проверяем, что есть имя
                        moving_real_index = int(values[0]) - 1
                        moving_name = values[1]  # Сохраняем имя
                    
                    # Для соседнего элемента
                    neighbor_item = visible_items[neighbor_idx]
                    neighbor_values = self.tree.item(neighbor_item, 'values')
                    if not neighbor_values:
                        return
                    neighbor_real_idx = int(neighbor_values[0]) - 1
                except:
                    return
                
                # Создаем новую версию display_tracks
                new_display = [track.copy() for track in self.display_tracks]
                
                # Меняем местами с соседом
                new_display[moving_real_index], new_display[neighbor_real_idx] = \
                    new_display[neighbor_real_idx].copy(), new_display[moving_real_index].copy()
                
                # Обновляем номера
                new_display[moving_real_index]['num'] = moving_real_index + 1
                new_display[neighbor_real_idx]['num'] = neighbor_real_idx + 1
                
                # Помечаем как перемещенные
                #new_display[moving_real_index]['was_moved'] = True
                new_display[neighbor_real_idx]['was_moved'] = True
                
                # Применяем изменения
                self.display_tracks = new_display
                self.temp_list = self.display_tracks
                self.shuffled_list = None
                self._drag_data["y"] = y
                
                # Обновляем отображение
                self.update_display()
                
                # Восстанавливаем выделение по имени
                self._restore_selection_by_identifiers(self._drag_data["identifiers"])

            else:
                # Логика для нескольких треков (блочное перемещение)
                # Если это первое движение - инициализируем данные
                if 'block_init' not in self._drag_data:
                    # Сохраняем исходные данные
                    self._drag_data['original_display'] = [track.copy() for track in self.display_tracks]
                    self._drag_data['block_items'] = []
                    self._drag_data['names'] = []
                    
                    # Собираем данные о выделенных треках
                    for item in self._drag_data["items"]:
                        values = self.tree.item(item, 'values')
                        if values and len(values) > 1:  # Проверяем, что есть имя
                            real_index = int(values[0]) - 1
                            if 0 <= real_index < len(self.display_tracks):
                                # Сохраняем трек и его данные
                                track = self.display_tracks[real_index]
                                track['was_moved'] = True
                                
                                track_data = {
                                    'track': track,
                                    'real_index': real_index,
                                    'name': values[1],
                                    'was_moved': True
                                }
                                self._drag_data['block_items'].append(track_data)
                                self._drag_data['names'].append(values[1])
                    
                    if not self._drag_data['block_items']:
                        return
                    
                    # Помечаем, что инициализация выполнена
                    self._drag_data['block_init'] = True
                
                # Вычисляем высоту блока (если еще не вычисляли)
                if 'block_height' not in self._drag_data:
                    block_height = 0
                    for item in self._drag_data["items"]:
                        bbox = self.tree.bbox(item)
                        if bbox:
                            block_height += bbox[3]
                        else:
                            block_height += 20
                    self._drag_data['block_height'] = block_height
                
                # Получаем высоту блока
                block_height = self._drag_data['block_height']
                
                # Рассчитываем смещение для позиционирования курсора в середине блока
                center_offset = block_height / 3
                
                # Для движения вниз используем положительное смещение, для движения вверх - отрицательное
                delta_y = y - self._drag_data.get('last_y', y)
                direction_factor = 1 if delta_y > 0 else -1
                
                # Рассчитываем виртуальную позицию курсора с учетом смещения
                virtual_y = y + (center_offset * direction_factor)
                
                # Обновляем последнюю позицию Y
                self._drag_data['last_y'] = y
                
                # Находим элемент, соответствующий виртуальной позиции
                insert_item = self.tree.identify_row(virtual_y)
                if not insert_item:
                    return
                
                # Определяем позицию вставки
                try:
                    insert_values = self.tree.item(insert_item, 'values')
                    if not insert_values:
                        return
                    insert_real_index = int(insert_values[0]) - 1
                except:
                    return

                # Создаем новый список треков
                new_display = [track for track in self.display_tracks]

                # Удаляем выделенные треки из их текущих позиций
                block_tracks = []
                for item_data in self._drag_data['block_items']:
                    if item_data['real_index'] < len(new_display):
                        block_tracks.append(item_data['track'])
                        new_display[item_data['real_index']] = None

                # Удаляем None значения
                new_display = [track for track in new_display if track is not None]

                # Вставляем блок в новую позицию
                insert_index = 0
                if insert_real_index > 0:  # Для всех позиций кроме первой
                    for i, track in enumerate(new_display):
                        if track.get('display_num', track['num']) > insert_real_index + 1:
                            break
                        insert_index = i + 1

                # Если позиция вставки не изменилась - пропускаем обновление
                if 'last_insert_index' in self._drag_data and self._drag_data['last_insert_index'] == insert_index:
                    return

                # Сохраняем текущую позицию для следующей проверки
                self._drag_data['last_insert_index'] = insert_index

                new_display = new_display[:insert_index] + block_tracks + new_display[insert_index:]

                # Обновляем отображаемые индексы
                for idx, track in enumerate(new_display):
                    track['display_num'] = idx + 1    
                    
                # Применяем изменения
                self.display_tracks = new_display
                self.temp_list = self.display_tracks
                self.shuffled_list = None
                self.update_display()
                
                # Обновляем реальные индексы в block_items
                for i, item_data in enumerate(self._drag_data['block_items']):
                    item_data['real_index'] = insert_index + i
                
                # Восстанавливаем выделение по именам
                self._restore_selection_by_identifiers(self._drag_data['identifiers'])
            
            
    def on_treeview_button_press(self, event):
        """Обработчик нажатия кнопки мыши"""
        import uuid  # Добавляем импорт модуля UUID
        
        item = self.tree.identify_row(event.y)
        if item:
            if event.state & (0x0004 | 0x0001):  # Ctrl или Shift
                self._drag_data = None
                return
            
            selected_items = self.tree.selection()
            if item not in selected_items:
                selected_items = [item]
                self.tree.selection_set(item)
            
            # Собираем данные о выделенных треках
            real_indices = []
            display_indices = []
            identifiers = []  # Используем уникальные идентификаторы
            visible_items = list(self.tree.get_children())
            
            for item in selected_items:
                try:
                    values = self.tree.item(item, 'values')
                    if values and len(values) > 0:
                        real_index = int(values[0]) - 1
                        real_indices.append(real_index)
                        display_indices.append(visible_items.index(item))
                        
                        # Генерируем уникальный временный идентификатор для каждого трека
                        if 0 <= real_index < len(self.display_tracks):
                            track = self.display_tracks[real_index]
                            if 'drag_id' not in track:
                                track['drag_id'] = uuid.uuid4().hex  # Генерируем уникальный UUID
                            identifiers.append(track['drag_id'])
                except:
                    continue
            
            if real_indices:
                self._drag_data = {
                    "items": selected_items,
                    "y": event.y,
                    "real_indices": real_indices,
                    "display_indices": display_indices,
                    "identifiers": identifiers  # Сохраняем уникальные идентификаторы
                }
                
        else:
            self._drag_data = None

    def _restore_selection_by_identifiers(self, identifiers):
        """Восстанавливает выделение по уникальным идентификаторам"""
        if not identifiers:
            return
        
        new_selection = []
        visible_items = list(self.tree.get_children())
        
        for item in visible_items:
            values = self.tree.item(item, 'values')
            if values and len(values) > 0:
                real_index = int(values[0]) - 1
                if 0 <= real_index < len(self.display_tracks):
                    track = self.display_tracks[real_index]
                    if 'drag_id' in track and track['drag_id'] in identifiers:
                        new_selection.append(item)
        
        if new_selection:
            self.tree.selection_set(new_selection)
            # Обновляем данные drag
            self._drag_data["items"] = new_selection

    def on_treeview_button_release(self, event):
        """Обработчик отпускания кнопки мыши"""
        if hasattr(self, '_drag_data') and self._drag_data:
            # Очищаем временные идентификаторы
            if 'identifiers' in self._drag_data:
                for identifier in self._drag_data['identifiers']:
                    for track in self.display_tracks:
                        if 'drag_id' in track and track['drag_id'] == identifier:
                            del track['drag_id']
            
            # Сбрасываем флаги и временные данные
            if 'block_init' in self._drag_data:
                del self._drag_data['block_init']
            if 'block_height' in self._drag_data:
                del self._drag_data['block_height']
            # Удаляем временные данные о позиции
            if 'last_insert_index' in self._drag_data:
                del self._drag_data['last_insert_index']
            # Сохраняем состояние после перемещения
            self.save_state()
            
            # Сбрасываем данные перетаскивания
            self._drag_data = {}
        
        
    def move_up(self):
        """Перемещает выделенные треки вверх с учетом фильтрации"""
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        # Получаем все видимые элементы
        visible_items = list(self.tree.get_children())
        if not visible_items:
            return
        
        # Создаем временный список если его еще нет
        if self.temp_list is None:
            self.temp_list = [track.copy() for track in self.display_tracks]
        
        # Собираем данные о выделенных треках
        selected_data = []
        for item in selected:
            values = self.tree.item(item, 'values')
            if values and len(values) >= 2:
                display_num = int(values[0])  # Отображаемый номер
                real_index = display_num - 1   # Реальный индекс
                if 0 <= real_index < len(self.temp_list):
                    selected_data.append({
                        'item': item,
                        'display_num': display_num,
                        'real_index': real_index,
                        'name': values[1],
                        'visible_index': visible_items.index(item)  # Позиция в отображении
                    })
        
        if not selected_data:
            return
        
        # Сортируем по позиции в отображении
        selected_data.sort(key=lambda x: x['visible_index'])
        
        # Проверяем, можно ли переместить вверх
        if selected_data[0]['visible_index'] == 0:
            return
        
        # Для каждого выделенного трека находим предыдущий видимый трек
        for data in selected_data:
            current_visible_idx = data['visible_index']
            prev_item = visible_items[current_visible_idx - 1]
            
            # Получаем данные предыдущего трека
            prev_values = self.tree.item(prev_item, 'values')
            if not prev_values or len(prev_values) < 2:
                continue
                
            prev_real_index = int(prev_values[0]) - 1
            current_real_index = data['real_index']
            
            # Меняем местами в temp_list
            self.temp_list[current_real_index], self.temp_list[prev_real_index] = \
                self.temp_list[prev_real_index], self.temp_list[current_real_index]
            
            # Обновляем отображаемые номера
            self.temp_list[current_real_index]['num'] = prev_real_index + 1
            self.temp_list[prev_real_index]['num'] = current_real_index + 1
            
            # Помечаем как перемещенные
            self.temp_list[prev_real_index]['was_moved'] = True
        
        # Обновляем основной список
        self.display_tracks = self.temp_list.copy()
        self.shuffled_list = None
        # Обновляем отображение
        self.update_display()
        
        # Восстанавливаем выделение по именам треков
        new_selection = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) >= 2:
                for data in selected_data:
                    if values[1] == data['name']:
                        new_selection.append(item)
                        break
        
        if new_selection:
            self.tree.selection_set(new_selection)
        
        self.show_message(self.localization.tr("moved_up"), "green")
        self.manual_edit = True
        self.update_undo_redo_buttons()
        self.save_state()

    def move_down(self):
        """Перемещает выделенные треки вниз с учетом фильтрации"""
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        # Получаем все видимые элементы
        visible_items = list(self.tree.get_children())
        if not visible_items:
            return
        
        # Создаем временный список если его еще нет
        if self.temp_list is None:
            self.temp_list = [track.copy() for track in self.display_tracks]
        
        # Собираем данные о выделенных треках
        selected_data = []
        for item in selected:
            values = self.tree.item(item, 'values')
            if values and len(values) >= 2:
                display_num = int(values[0])  # Отображаемый номер
                real_index = display_num - 1   # Реальный индекс
                if 0 <= real_index < len(self.temp_list):
                    selected_data.append({
                        'item': item,
                        'display_num': display_num,
                        'real_index': real_index,
                        'name': values[1],
                        'visible_index': visible_items.index(item)  # Позиция в отображении
                    })
        
        if not selected_data:
            return
        
        # Сортируем по позиции в отображении (в обратном порядке)
        selected_data.sort(key=lambda x: x['visible_index'], reverse=True)
        
        # Проверяем, можно ли переместить вниз
        if selected_data[0]['visible_index'] == len(visible_items) - 1:
            return
        
        # Для каждого выделенного трека находим следующий видимый трек
        for data in selected_data:
            current_visible_idx = data['visible_index']
            next_item = visible_items[current_visible_idx + 1]
            
            # Получаем данные следующего трека
            next_values = self.tree.item(next_item, 'values')
            if not next_values or len(next_values) < 2:
                continue
                
            next_real_index = int(next_values[0]) - 1
            current_real_index = data['real_index']
            
            # Меняем местами в temp_list
            self.temp_list[current_real_index], self.temp_list[next_real_index] = \
                self.temp_list[next_real_index], self.temp_list[current_real_index]
            
            # Обновляем отображаемые номера
            self.temp_list[current_real_index]['num'] = next_real_index + 1
            self.temp_list[next_real_index]['num'] = current_real_index + 1
            
            # Помечаем как перемещенные
            self.temp_list[next_real_index]['was_moved'] = True
        
        # Обновляем основной список
        self.display_tracks = self.temp_list.copy()
        self.shuffled_list = None
        # Обновляем отображение
        self.update_display()
        
        # Восстанавливаем выделение по именам треков
        new_selection = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) >= 2:
                for data in selected_data:
                    if values[1] == data['name']:
                        new_selection.append(item)
                        break
        
        if new_selection:
            self.tree.selection_set(new_selection)
        
        self.show_message(self.localization.tr("moved_down"), "green")
        self.manual_edit = True
        self.update_undo_redo_buttons()
        self.save_state()

    
    def delete_tracks(self):
        selected = self.tree.selection()
        if not selected:
            self.show_message(self.localization.tr("error_no_selection"), "red")
            return
        
        # Создаем временный список если его еще нет
        if self.temp_list is None:
            self.temp_list = [track.copy() for track in self.display_tracks]
        
        # Получаем реальные индексы в исходном списке
        indices_to_delete = []
        
        for item in selected:
            item_values = self.tree.item(item, 'values')
            if item_values and len(item_values) > 0:
                # Номер трека из первого столбца таблицы (нумерация с 1)
                track_num = int(item_values[0]) - 1
                if 0 <= track_num < len(self.temp_list):
                    indices_to_delete.append(track_num)
                    
                    # Получаем трек
                    track = self.temp_list[track_num]
                    
                    # Добавляем в историю удалений и получаем del_id
                    del_id = self.add_to_deletion_history(track)
                    
                    # Сохраняем del_id в треке
                    track['del_id'] = del_id
        
        # Удаляем в обратном порядке, чтобы индексы не сдвигались
        for index in sorted(indices_to_delete, reverse=True):
            if 0 <= index < len(self.temp_list):
                del self.temp_list[index]
        
        # Обновляем основной список
        self.display_tracks = self.temp_list.copy()
        
        # Сохраняем состояние перед обновлением отображения
        self.save_state()
        
        # Обновляем отображение (без сохранения выделения)
        self.update_display()
        
        # Показываем сообщение
        deleted_count = len(indices_to_delete)
        self.show_message(
            self.localization.tr("deleted_tracks").format(count=deleted_count), 
            "green"
        )
        
        # Обновляем флаги и кнопки
        self.manual_edit = True
        self.update_undo_redo_buttons()
        
        # Сбрасываем перемешанную версию
        self.shuffled_list = None
    
    
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
        self.tree.tag_configure('modified_name', background='#FFDDCC') # Коралловый - измененное имя
        self.tree.tag_configure('modified_name_moved', background='#f8d3e9') # Комбинация - modified_name + moved
        self.tree.tag_configure('modified_name_path', background='#c6f5f0') # Бирюзовый
        self.tree.tag_configure('modified_name_path_moved', background='#CCDAFF')
        self.tree.tag_configure('found', background='white')  # для найденных элементов
        self.tree.tag_configure('added', background='#F0F0F0') # Все три состояния E0E0E0

        # Получаем поисковый запрос
        search_term = self.search_entry.get().lower()
        print(f"[DEBUG] ТАБЛИЦА ===================================================================\n[TRACK] :")
        # Вставляем треки с оригинальной нумерацией
        for i, track in enumerate(self.display_tracks, 1):  # i - оригинальный номер
            # Пропускаем треки, которые не соответствуют поисковому запросу (если он есть)
            if search_term and not track.get('found', False):
                continue
               
            # Используем оригинальный номер (i) вместо visible_index
            item = self.tree.insert('', 'end', values=(i, track['name'], track['path'].replace('\\', '/')))
            
            # Определяем теги в зависимости от состояния трека
            tags = []
            is_modified = track.get('was_modified', False)
            is_moved = track.get('was_moved', False)
            is_restored = track.get('was_restored', False)
            is_name_modified = track.get('was_name_modified', False)
            is_found = track.get('found', False)
            has_id = track.get('track_id', None)
            # Комбинируем теги для всех возможных сочетаний
            if is_moved and is_name_modified and is_modified:
                tags.append('modified_name_path_moved')
            elif is_moved and is_name_modified:
                tags.append('modified_name_moved') 
            elif is_modified and is_name_modified:
                tags.append('modified_name_path')
            elif is_name_modified:
                tags.append('modified_name')
            elif is_modified and is_moved:
                tags.append('modified_moved')
            elif is_modified and is_restored:
                tags.append('modified_restored') 
            elif is_moved and is_restored:
                tags.append('moved_restored')
            elif is_modified:
                tags.append('modified')   
            elif is_restored:
                tags.append('restored')    
            elif is_moved:
                tags.append('moved')
            elif has_id is not None:
                tags.append('added') 
            elif is_found:
                tags.append('found')
          
                
            if tags:
                self.tree.item(item, tags=tuple(tags))
            print(f"[TRACK] {i}. {track['name']}    —   —   —   —   —   {tags}")
            print(f"[TRACK] :                                                                     ID: {track.get('track_id')}")
            print(f"[TRACK] :")
        # Восстанавливаем выделение если указаны индексы
        if selection_indices is not None:
            children = self.tree.get_children()
            for idx in selection_indices:
                if 0 <= idx < len(children):
                    self.tree.selection_add(children[idx])
        
        # Обновляем внутренние списки (без изменений)
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
                'track_id': track['track_id'],
                'original_path': track.get('original_path', track['path']),
                'original_name': track.get('original_name', track['name']),
                'was_modified': track.get('was_modified', False),
                'was_name_modified': track.get('was_name_modified', False),
                'was_moved': track.get('was_moved', False),
                'was_restored': track.get('was_restored', False),
                'found': track.get('found', False),
                'del_id': track.get('del_id'),  # Сохраняем del_id если есть
            } for track in self.display_tracks],
            'selection': [int(self.tree.index(item)) for item in self.tree.selection()],
            'deleted_tracks_history': self.deleted_tracks_history.copy(),  # Сохраняем историю
            'del_id_counter': self.del_id_counter  # Сохраняем счетчик
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
                t1.get('original_name', t1['name']) != t2.get('original_name', t2['name']) or
                t1['was_modified'] != t2['was_modified'] or
                t1.get('was_name_modified', False) != t2.get('was_name_modified', False)):
                return False
        return True


    def restore_state(self, current_state):
        """Восстанавливает состояние с полным обновлением интерфейса"""
        # Получаем текущие пути перед восстановлением
        current_paths = {(track['path'], track['name'], track['track_id'], track['num']): track 
                        for track in self.display_tracks} if self.display_tracks else {}
        
        # Обновляем основной список
        self.display_tracks = []
        
        # Получаем текущий поисковый запрос
        search_term = self.search_entry.get().lower()
        
        for track in current_state['tracks']:
            new_track = track.copy()
            
            # Создаем ключ для идентификации трека
            key = (track['path'], track['name'], track['track_id'], track['num'])
            
            # Проверяем, существует ли трек в текущем состоянии
            existing_track = current_paths.get(key)
            
            if existing_track:
                # Сохраняем флаги из текущего состояния
                new_track['found'] = existing_track.get('found', False)
                new_track['was_restored'] = existing_track.get('was_restored', False)
            else:
                # Для новых треков устанавливаем found в зависимости от текущего фильтра
                new_track['found'] = not search_term or search_term in new_track['name'].lower()
                
                # Проверяем, был ли этот трек удален
                deletion_info = self.get_deletion_info(new_track)
                if deletion_info:
                    # Применяем тег 'restored'
                    new_track['was_restored'] = True
                    
                    # Сохраняем del_id для последующего использования
                    new_track['del_id'] = deletion_info['del_id']
            
            self.display_tracks.append(new_track)
        
        # Обновляем временные списки
        self.temp_list = self.display_tracks.copy()
        self.shuffled_list = None
        
        # Обновляем отображение с сохранением фильтра
        current_search = self.search_entry.get()
        self.update_display()
        if current_search:
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, current_search)
            self.on_search_key_release(None)
                   

    def add_to_deletion_history(self, track):
        """Добавляет трек в историю удалений и обновляет карту"""
        # Генерируем уникальный del_id
        self.del_id_counter += 1
        del_id = f"del_{self.del_id_counter}_{int(time.time() * 1000)}"
        
        # Создаем ключ для идентификации трека
        key = (track['path'], track['name'], track.get('track_id', ''), track['num'])
        
        # Сохраняем информацию об удалении
        deletion_info = {
            'key': key,
            'del_id': del_id,
            'timestamp': time.time()
        }
        
        # Добавляем в историю
        self.deleted_tracks_history.append(deletion_info)
        
        # Обновляем карту для быстрого поиска
        self.deleted_tracks_map[key] = deletion_info
        
        return del_id


    def get_deletion_info(self, track):
        """Возвращает информацию об удалении для трека, если она есть"""
        key = (track['path'], track['name'], track.get('track_id', ''), track['num'])
        return self.deleted_tracks_map.get(key)
        

    def undo_action(self):
        """Отменяет последнее действие с поддержкой фильтрации"""
        if self.history_index <= 0:
            self.show_message(self.localization.tr("nothing_to_undo"), "red")
            return
        
        # Сохраняем текущий поисковый запрос
        current_search = self.search_entry.get()
        
        self.history_index -= 1
        state = self.history[self.history_index]
        
        # Восстанавливаем состояние
        self.restore_state(state)
        
        # Восстанавливаем поисковый запрос если он был
        if current_search:
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, current_search)
            self.on_search_key_release(None)
        
        self.show_message(self.localization.tr("action_undone"), "green")
        self.update_undo_redo_buttons()

    def redo_action(self):
        """Повторяет отмененное действие с поддержкой фильтрации"""
        if self.history_index >= len(self.history) - 1:
            self.show_message(self.localization.tr("nothing_to_redo"), "red")
            return
        
        # Сохраняем текущий поисковый запрос
        current_search = self.search_entry.get()
        
        self.history_index += 1
        state = self.history[self.history_index]
        
        # Восстанавливаем состояние
        self.restore_state(state)
        
        # Восстанавливаем поисковый запрос если он был
        if current_search:
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, current_search)
            self.on_search_key_release(None)
        
        self.show_message(self.localization.tr("action_redone"), "green")
        self.update_undo_redo_buttons()

    def update_undo_redo_buttons(self):
        """Обновляет состояние кнопок с учетом новой логики"""
        self.undo_btn['state'] = 'normal' if self.history_index > 0 else 'disabled'
        self.redo_btn['state'] = 'normal' if self.history_index < len(self.history) - 1 else 'disabled'
     
    
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

            # Выбираем подходящий делитель
            random_divisor = random.choice(number)
            if random_divisor == 0 or (random_divisor > random_number and random_divisor != 1):
                random_divisor = max([x for x in number if x <= random_number])
            
            result = (random_number // random_divisor)
            
            predictable_num = (date_part * num_tracks + result + 1) % fact
            
            print(f"[DEBUG] ГЕНЕРАЦИЯ ОСНОВНОГО СИДА \n=================================================================== \n Количество треков = {num_tracks} \n Дата = {date_part} \n Случайное число = {random_number} \n Делитель = {random_divisor} \n Разность = {result} \n Результат = {predictable_num}")
            # Форматируем в соответствии с выбранным форматом
            if self.seed_format_combobox.get() in ["Только цифры", "Digits only", "Solo dígitos", "Nur Zahlen", "Solo numeri", "Tylko cyfry", 
                            "Толькі лічбы", "Тільки цифри", "Тек сандар", "Само бројеви", "Chiffres uniquement", "Sólo números", "Apenas números", "Sadece rakamlar", "Apenas dígitos", "Alleen cijfers", "仅数字", "숫자만", "Samo številke", "Vetëm numra", "Samo brojevi", "Csak számok", "Doar cifre", "Pouze čísla", "Alleen cijfers", "Chiffres seulement", "Nur Zahlen", "Numbers only", "Aðeins tölur", "Ainult numbrid", "Bare tall", "Solo números", "केवल संख्याएँ", "数字のみ", "Kun tal", "Endast siffror", "Vain numerot", "Slegs Syfers", "Chỉ số", "Hanya angka", "Dhigití amháin", "Μόνο αριθμοί", "Само цифри", "Tik skaičiai", "Tikai cipari", "Numri biss", "Само бројки", "Iba číslice", "מספרים בלבד", "எண்கள் மட்டும்", "అంకెలు మాత్రమే", "Nombor sahaja", "ቁጥሮች ብቻ", "Nambari pekee", "Izinombolo kuphela"]:
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


    def shuffle_tracks(self, num_swaps=None):
        """Перемешивание с фиксированным результатом для одинакового сида"""
        import _pylong
        import uuid
        sys.set_int_max_str_digits(0)
        print(f"[DEBUG] ПРОЦЕСС ПЕРЕМЕШИВАНИЯ \n===================================================================")
        try:
            user_seed = self.seed_entry.get()
            step_value = self.step_entry.get()
            now = datetime.datetime.now()
        
            # Определяем базовый список для работы
            if self.shuffled_list is not None:
                # Если было перемешивание - используем перемешанный список
                base_list = self.shuffled_list
            
            elif self.temp_list is not None:
                # Если было ручное редактирование - используем временный список
                base_list = self.temp_list
            
            else:
                # Если не было ни перемешивания, ни редактирования - используем оригинальный порядок
                base_list = self.original_list.copy()

            # 1. Присваиваем временные ID и сохраняем полные копии оригинальных треков
            original_tracks = {}
            for track in base_list:
                temp_id = str(uuid.uuid4())
                track["temp_id"] = temp_id
                # Сохраняем ПОЛНУЮ КОПИЮ оригинального трека
                original_tracks[temp_id] = track.copy()
            
            # 2. Гарантируем наличие original_path и применяем модификации
            for track in base_list:
                if "original_path" not in track:
                    track["original_path"] = track["path"]
                
                # Применяем изменения только к текущему треку
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
            self.shuffled_list, num_swaps = self.soft_shuffle(tracks, str(seed_trimmed))
            
            print("[DEBUG] : Новый список ============================")
            for i, track in enumerate(self.shuffled_list, 1):
                print(f"{i}. {track['name']}\n                                                                     TempID: {track['temp_id']}       |       ID: {track.get('track_id')}")
            print("===================================================================")            
            
            # Применяем реверс если нужно
            step = 0
            if step_value.strip():
                try:
                    step = int(step_value)
                    if 0 < step:
                        if step == 1:
                            step = random.randint(2, 20)
                        
                        # Реверсируем блоки в shuffled_list
                        print(f"[DEBUG] Реверс = {step}")
                        for i in range(0, len(self.shuffled_list), step):
                            self.shuffled_list[i:i+step] = reversed(self.shuffled_list[i:i+step])
                except ValueError:
                    self.seed_info.config(text=self.localization.tr("error_reverse_step"), fg="red")
                    return
            
            if step_value.strip(): 
                print(f"[DEBUG] : Новый список c реверсом {step} ============================")
                for i, track in enumerate(self.shuffled_list, 1):
                    print(f"{i}. {track['name']}\n                                                                     TempID: {track['temp_id']}       |       ID: {track.get('track_id')}")
                print("===================================================================")            
            
            
            # 3. Восстанавливаем состояния после перемешивания
            for track in self.shuffled_list:
                temp_id = track.get('temp_id')
                if temp_id and temp_id in original_tracks:
                    original_track = original_tracks[temp_id]
                    
                    # Восстанавливаем ВСЕ атрибуты из оригинального трека
                    for key in ['track_id', 'was_restored', 'was_modified', 
                               'was_name_modified', 'was_moved', 'found',
                               'original_path', 'original_name']:
                        if key in original_track:
                            track[key] = original_track[key]
                    
                    # Особые случаи:
                    # - Путь восстанавливаем только если не был изменен
                    if not track.get('was_modified', False):
                        track['path'] = original_track['path']
                    
                    # - Имя восстанавливаем только если не было изменено
                    if not track.get('was_name_modified', False):
                        track['name'] = original_track['name']
                    
                    # - Для модифицированных треков сохраняем текущий путь
                    if track.get('was_modified', False) and track['original_path'] in self.modified_paths:
                        track['path'] = self.modified_paths[track['original_path']]
                
                # Удаляем временные данные
                track.pop('temp_id', None)
                if 'was_moved' in track and not track['was_moved']:
                    del track['was_moved']

                
            # Обновляем отображение
            self.display_tracks = self.shuffled_list
            self.update_display()
            
            # Обновляем информацию о сиде
            self.current_seed = seed_trimmed
            self.current_swaps = num_swaps if num_swaps > 0 else None
            self.current_reverse_step = step if step > 0 else None
                    
            print(f"[SUCCES] Перемешивание завершено")
            
            self.save_state()
            # Показываем сообщение
            if step > 0:
                if self.current_swaps:
                    info_text = self.localization.tr("editor_seed_info_intensity_step").format(seed=seed_trimmed, step=step, num_swaps=self.current_swaps)
                else:
                    info_text = self.localization.tr("editor_seed_info_step").format(seed=seed_trimmed, step=step)
            else:
                if self.current_swaps:
                    info_text = self.localization.tr("editor_seed_info_intensity").format(seed=seed_trimmed, num_swaps=self.current_swaps)
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
        
        print(f"[DEBUG] : Текущий список ============================")
        for i, track in enumerate(files, 1):
            print(f"{i}. {track['name']} \n                                                                     TempID: {track['temp_id']}       |       ID: {track.get('track_id')}")
        print("===================================================================")
        
        random.shuffle(files)
        
        print(f"[DEBUG] : Перемешанный список ============================")
        for i, track in enumerate(files, 1):
            print(f"{i}. {track['name']} \n                                                                     TempID: {track['temp_id']}      |       ID: {track.get('track_id')}")
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



    def save_playlist(self):
        import datetime
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
                if 'was_added' in track:
                    del track['was_added']
                    
            # Создаем копию текущего состояния перед сохранением
            current_state = {
                'tracks': [track.copy() for track in source_list],
                'selection': list(self.tree.selection())
            }

            # Создаем список треков для сохранения
            saved_tracks = []
            
            for idx, track in enumerate(source_list, 1):
                # Сохраняем текущее состояние трека
                new_track = track.copy()
                new_track['num'] = idx
                
                # Если имя было изменено, используем новое имя в пути
                if track.get('was_name_modified', False):
                    dir_path = os.path.dirname(track['path'])
                    new_path = os.path.join(dir_path, track['name'])
                else:
                    new_path = track['path']
                
                saved_tracks.append({
                    "path": new_path,
                    "name": track['name'],
                    "num": idx,
                    'track_id': track.get('track_id', None),
                    "original_path": track.get("original_path", track['path']),
                    "original_name": track.get("original_name", track['name']),
                    "was_modified": track.get("was_modified", False),
                    "was_name_modified": track.get("was_name_modified", False),
                    "was_moved": track.get("was_moved", False),
                    "was_restored": track.get("was_restored", False),
                    'found': track.get('found', False),
                })
            
            if not saved_tracks:
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
                        if self.current_swaps:
                            f.write(f"#NUM_SWAPS:{self.current_swaps}\n")    
                        if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                            f.write(f"#REVERSE_STEP:{self.current_reverse_step}\n")
                    
                    f.write(f"#TRACKS:{len(saved_tracks)}\n\n")
                    
                    for track in saved_tracks:                        
                        # Нормализуем путь
                        clean_path = os.path.normpath(track['path'])
                        
                        # Получаем имя файла
                        file_name = os.path.basename(clean_path)
                        name_without_ext = os.path.splitext(file_name)[0]
                        
                        f.write(f"#EXTINF:-1,{saxutils.escape(name_without_ext)}\n")
                        f.write(f"{clean_path.replace('\\', '/')}\n")
                print(f"[DEBUG] Плейлист сохранен: {playlist_name}.{playlist_format}")
                
                
            if playlist_format in ["txt"]:  
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write("#Made with VolfLife's Playlist Generator\n")
                    f.write(f"#GENERATED:{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"#TRACKLIST:{playlist_name}\n")
                    
                    # Добавляем информацию о сиде только если было перемешивание
                    if self.shuffled_list is not None and hasattr(self, 'current_seed'):
                        f.write(f"#SEED:{self.current_seed}\n")
                        if self.current_swaps:
                            f.write(f"#NUM_SWAPS:{self.current_swaps}\n")    
                        if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                            f.write(f"#REVERSE_STEP:{self.current_reverse_step}\n")
                    
                    f.write(f"#TRACKS:{len(saved_tracks)}\n\n")
                    
                    for track in saved_tracks:
                        escaped_path = track['path'].replace('\\', '/')
                        f.write(f"{escaped_path}\n")
                print(f"[DEBUG] Треклист сохранен: {playlist_name}.{playlist_format}") 
            
            
            if playlist_format in ["pls"]:
                with open(save_path, 'w', encoding='utf-8') as f:
                    # Заголовок плейлиста
                    f.write("[playlist]\n")
                    f.write(f";Made with VolfLife's Playlist Generator\n")
                    f.write(f";GENERATED:{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f";PLAYLIST:{playlist_name}\n")
                    
                    # Добавляем информацию о сиде только если было перемешивание
                    if self.shuffled_list is not None and hasattr(self, 'current_seed'):
                        f.write(f"#SEED:{self.current_seed}\n")
                        if self.current_swaps:
                            f.write(f"#NUM_SWAPS:{self.current_swaps}\n")     
                        if hasattr(self, 'current_reverse_step') and self.current_reverse_step:
                            f.write(f"#REVERSE_STEP:{self.current_reverse_step}\n")
                    
                    f.write(f"NumberOfEntries={len(saved_tracks)}\n")
                    f.write("Version=2\n\n")  # Версия формата PLS

                    # Запись треков
                    for i, track in enumerate(saved_tracks, 1):
                        # Нормализуем путь
                        clean_path = os.path.normpath(track['path'])
                        # Получаем имя файла
                        file_name = os.path.basename(clean_path)
                        name_without_ext = os.path.splitext(file_name)[0]
                        
                        f.write(f"File{i}={clean_path.replace('\\', '/')}\n")
                        f.write(f"Title{i}={saxutils.escape(name_without_ext)}\n")
                        f.write(f"Length{i}=-1\n")  # -1 = длительность определит плеер
                        
                        if i < len(saved_tracks):  # Добавляем пустую строку между треками (кроме последнего)
                            f.write("\n")
                print(f"[DEBUG] Плейлист сохранен: {playlist_name}.{playlist_format}")
              

            if playlist_format in ["asx"]:
                with open(save_path, 'w', encoding='utf-8') as f:
                    # Заголовок ASX
                    f.write('<ASX Version="3.0">\n')
                    f.write(f'<!-- Generated by VolfLife\'s Playlist Generator on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n')
                    f.write(f'<Title>{saxutils.escape(playlist_name)}</Title>\n')
                    f.write(f'<Abstract>SEED:{self.current_seed}</Abstract>\n')
                    
                    if self.current_swaps is not None and self.current_swaps > 0:
                        f.write(f'<Abstract>NUM_SWAPS:{self.current_swaps}</Abstract>\n')    
                    if self.current_reverse_step is not None and self.current_reverse_step > 0:
                        f.write(f'<Abstract>REVERSE_STEP:{self.current_reverse_step}</Abstract>\n')
                    
                    f.write(f'<Abstract>TRACKS:{len(saved_tracks)}</Abstract>\n\n')
                    
                    # Запись треков
                    for track in saved_tracks:
                        clean_path = os.path.normpath(track['path'])
                        file_name = os.path.basename(clean_path)
                        name_without_ext = os.path.splitext(file_name)[0]
                        
                        f.write('<Entry>\n')
                        f.write(f'  <Title>{saxutils.escape(name_without_ext)}</Title>\n')
                        f.write(f'  <Ref href="{saxutils.escape(clean_path.replace("\\", "/"))}" />\n')
                        f.write('</Entry>\n\n')
                    
                    f.write('</ASX>')
                
                print(f"[DEBUG] Плейлист сохранен: {playlist_name}.{playlist_format}")
              
                
            if playlist_format in ["xspf"]:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    f.write('<playlist version="1" xmlns="http://xspf.org/ns/0/">\n')
                    f.write(f'  <title>{playlist_name}</title>\n')
                    f.write('  <creator>VolfLife\'s Playlist Generator</creator>\n')
                    f.write(f'  <date>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</date>\n')
                    
                    # Метаданные
                    if hasattr(self, 'current_seed'):
                        f.write('  <annotation>\n')
                        f.write(f'    SEED:{self.current_seed}\n')
                        if self.current_swaps:
                            f.write(f'    NUM_SWAPS:{self.current_swaps}\n')
                        if hasattr(self, 'current_reverse_step'):
                            f.write(f'    REVERSE_STEP:{self.current_swaps}\n')
                        f.write('  </annotation>\n')
                    
                    f.write('  <trackList>\n')
                    
                    for track in saved_tracks:                     
                        # Нормализуем путь
                        clean_path = os.path.normpath(track['path'])
                        # Получаем имя файла
                        file_name = os.path.basename(clean_path)
                        name_without_ext = os.path.splitext(file_name)[0]
                        
                        # Формируем file:// URL с правильным кодированием
                        file_url = "file:///" + clean_path.replace('\\', '/')
                    
                        f.write('    <track>\n')
                        f.write(f'      <location>{file_url}</location>\n')
                        f.write(f'      <title>{saxutils.escape(name_without_ext)}</title>\n')
                        f.write(f'      <meta rel="filename">{saxutils.escape(file_name)}</meta>\n')  # Добавляем оригинальное имя файла
                        f.write('    </track>\n')
                    
                    f.write('  </trackList>\n')
                    f.write('</playlist>\n')
                print(f"[DEBUG] Плейлист сохранен: {playlist_name}.{playlist_format}")

            
            if playlist_format in ["xspf+url"]:
                # Определяем путь для сохранения
                script_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
                          else os.path.dirname(os.path.abspath(__file__))
                playlist_format = "xspf"      
                save_path = os.path.join(script_dir, f"{playlist_name}.{playlist_format}")
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    f.write('<playlist version="1" xmlns="http://xspf.org/ns/0/">\n')
                    f.write(f'  <title>{playlist_name}</title>\n')
                    f.write('  <creator>VolfLife\'s Playlist Generator</creator>\n')
                    f.write(f'  <date>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</date>\n')
                    
                    # Метаданные
                    if hasattr(self, 'current_seed'):
                        f.write('  <annotation>\n')
                        f.write(f'    SEED:{self.current_seed}\n')
                        if self.current_swaps:
                            f.write(f'    NUM_SWAPS:{self.current_swaps}\n')    
                        if hasattr(self, 'current_reverse_step'):
                            f.write(f'    REVERSE_STEP:{self.current_reverse_step}\n')
                        f.write('  </annotation>\n')
                    
                    f.write('  <trackList>\n')
                    
                    for track in saved_tracks:                     
                        # Нормализуем путь
                        clean_path = os.path.normpath(track['path'])
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
                print(f"[DEBUG] Плейлист сохранен: {playlist_name}.{playlist_format}")

            
            if playlist_format in ["json"]:          
                from datetime import datetime
                playlist_data = {
                    "meta": {
                        "name": playlist_name,
                        "generator": "VolfLife's Playlist Generator",
                        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "seed": self.current_seed,
                        "num_swaps": self.current_swaps if self.current_swaps and self.current_swaps > 0 else None,
                        "reverse_step": self.current_reverse_step if self.current_reverse_step and self.current_reverse_step > 0 else None,
                        "num_tracks": len(saved_tracks)
                    },
                    "tracks": []
                }

                for track in saved_tracks:
                    file_path = os.path.normpath(track['path'])
                    playlist_data["tracks"].append({
                        "path": file_path.replace('\\', '/'),
                        "filename": os.path.basename(file_path),
                        "title": os.path.splitext(os.path.basename(track['path']))[0]
                    })

                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(playlist_data, f, indent=4, ensure_ascii=False)
                print(f"[DEBUG] Плейлист сохранен: {playlist_name}.{playlist_format}")
                
            
            if playlist_format in ["wpl"]:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write('<?wpl version="1.0"?>\n')
                    f.write('<smil>\n')
                    f.write('  <head>\n')
                    f.write('    <meta name="Generator" content="VolfLife\'s Playlist Generator"/>\n')
                    f.write(f'    <meta name="ItemCount" content="{len(saved_tracks)}"/>\n')
                    f.write(f'    <title>{playlist_name}</title>\n')
                    
                    # Метаданные в виде комментариев (альтернатива для WPL)
                    f.write('    <!--\n')
                    f.write(f'      GENERATED:{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n')
                    f.write(f'      SEED:{self.current_seed}\n')
                    if self.current_swaps:
                        f.write(f'      NUM_SWAPS:{self.current_swaps}\n')
                    if self.current_reverse_step:
                        f.write(f'      REVERSE_STEP:{self.current_reverse_step}\n')
                    f.write('    -->\n')
                    
                    f.write('  </head>\n')
                    f.write('  <body>\n')
                    f.write('    <seq>\n')
                    
                    for track in saved_tracks:
                        # Нормализуем путь и экранируем спецсимволы XML
                        clean_path = os.path.normpath(track['path'])
                        escaped_path = saxutils.escape(clean_path.replace('\\', '/'))
                        
                        # Записываем путь к файлу
                        f.write(f'      <media src="{escaped_path}"/>\n')
                    
                    f.write('    </seq>\n')
                    f.write('  </body>\n')
                    f.write('</smil>\n')
                
                print(f"[DEBUG] Плейлист создан и сохранен: {playlist_name}.{playlist_format}")

            
            if playlist_format == 'xml':
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    f.write('<playlist version="1" xmlns="http://xspf.org/ns/0/">\n')
                    f.write('  <title>{}</title>\n'.format(saxutils.escape(playlist_name)))
                    f.write('  <creator>VolfLife\'s Playlist Generator</creator>\n')
                    f.write('  <date>{}</date>\n'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    
                    # Метаданные
                    f.write('  <annotation>\n')
                    f.write('    GENERATED:{}\n'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    if self.current_seed:
                        f.write('    SEED:{}\n'.format(self.current_seed))
                    if self.current_swaps:
                        f.write('    NUM_SWAPS:{}\n'.format(self.current_swaps))
                    if self.current_reverse_step:
                        f.write('    REVERSE_STEP:{}\n'.format(self.current_reverse_step))
                    f.write('    TRACKS:{}\n'.format(len(saved_tracks)))
                    f.write('  </annotation>\n')
                    
                    f.write('  <trackList>\n')
                    
                    for i, track in enumerate(saved_tracks, 1):
                        # Нормализуем путь
                        clean_path = os.path.normpath(track['path'])
                        file_name = os.path.basename(clean_path)
                        name_without_ext = os.path.splitext(file_name)[0]
                        
                        f.write('    <track>\n')
                        f.write('      <location>{}</location>\n'.format(
                            urllib.parse.quote(saxutils.escape(clean_path.replace('\\', '/')))))
                        f.write('      <title>{}</title>\n'.format(
                            saxutils.escape(name_without_ext)))
                        f.write('      <meta rel="trackNumber">{}</meta>\n'.format(i))
                        f.write('    </track>\n')
                    
                    f.write('  </trackList>\n')
                    f.write('</playlist>\n')
                
                print(f"[DEBUG] Плейлист создан и сохранен: {playlist_name}.{playlist_format}")
            
            
            # Обновляем temp_list с сохранением original_path
            if self.temp_list is None:
                self.temp_list = []
                for track in saved_tracks:
                    new_track = track.copy()
                    new_track["original_path"] = track.get("original_path", track["path"])
                    self.temp_list.append(new_track)
            
            # Обновляем отображение из saved_tracks, чтобы синхронизироваться
            self.display_tracks = saved_tracks.copy()
            self.update_display()
            
            # Формируем сообщение          
            if self.current_reverse_step:
                if self.current_swaps:
                    info_text = self.localization.tr("seed_info_intensity_step").format(
                        seed=self.current_seed, step=self.current_reverse_step, num_swaps=self.current_swaps
                    )
                else:
                    info_text = self.localization.tr("seed_info_step").format(
                        seed=self.current_seed, step=self.current_reverse_step
                    )
            else:
                if self.current_swaps:
                    info_text = self.localization.tr("seed_info_intensity").format(
                        seed=self.current_seed, num_swaps=self.current_swaps
                    )
                else:
                    info_text = self.localization.tr("seed_info_basic").format(
                        seed=self.current_seed
                    )
            
            self.seed_info.config(text=self.localization.tr("playlist_saved").format(name=f"{playlist_name}.{playlist_format}", info=info_text), fg="green")
            
        except Exception as e:
            self.seed_info.config(text=f"{self.localization.tr('error_save')}: {str(e)}", fg="red")
    

    
    def create_path_editor_window(self, event=None):
        """Создает окно для изменения путей и имен выделенных треков"""
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
        self.path_editor.title(self.localization.tr("edit_track_window_title"))
        self.path_editor.transient(self.root)
        self.path_editor.grab_set()
        self.path_editor.resizable(False, False)
        
        # Устанавливаем иконку из FontLoader
        if hasattr(self, 'font_loader') and hasattr(self.font_loader, 'icon_ico'):
            try:
                icon_path = os.path.abspath(self.font_loader.temp_icon_path)
                self.path_editor.iconbitmap(icon_path)
                print("[DEBUG] Иконка для редактора треков успешно установлена")
            except Exception as e:
                print(f"[DEBUG] Ошибка установки иконки для редактора треков: {e}")
                if hasattr(self.font_loader, 'temp_icon_path'):
                    print(f"[DEBUG] Путь к временной иконке: {self.font_loader.temp_icon_path}")
                    print(f"[DEBUG] Файл существует: {os.path.exists(self.font_loader.temp_icon_path)}")
        
        # Центрируем окно
        window_width = 500
        window_height = 400
        screen_width = self.path_editor.winfo_screenwidth()
        screen_height = self.path_editor.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.path_editor.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Создаем Notebook (вкладки)
        notebook = ttk.Notebook(self.path_editor)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка для изменения пути
        path_frame = ttk.Frame(notebook)
        notebook.add(path_frame, text=self.localization.tr("edit_path_tab"))
        self.create_path_editor_tab(path_frame, selected_items)
        
        # Вкладка для изменения имени (доступна только для 1 трека)
        name_frame = ttk.Frame(notebook)
        notebook.add(name_frame, text=self.localization.tr("edit_name_tab"), 
                    state='normal' if len(selected_items) == 1 else 'disabled')
        
        if len(selected_items) == 1:
                self.create_name_editor_tab(name_frame, selected_items)        
        # Сохраняем выбранные элементы
        self.selected_for_edit = selected_items

    def create_path_editor_tab(self, parent, selected_items):
        """Создает содержимое вкладки для изменения пути"""
        # Фрейм для таблицы
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Таблица с выделенными треками
        tree = ttk.Treeview(table_frame, columns=('num', 'name'), show='headings')
        tree.heading('num', text=self.localization.tr("track_number"))
        tree.heading('name', text=self.localization.tr("track_name"))
        tree.column('num', width=50, anchor='center')
        tree.column('name', width=400, anchor='w')
        
        # Заполняем таблицу выделенными треками
        for item in selected_items:
            values = self.tree.item(item)['values']
            if len(values) >= 2:
                tree.insert('', 'end', values=(values[0], values[1]))
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Фрейм для поля ввода пути
        path_frame = ttk.Frame(parent, padding="10")
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
        ttk.Label(path_frame, 
                 text=self.localization.tr("path_example_hint"), 
                 font=('TkDefaultFont', 8)).pack(side=tk.LEFT)
        
        # Фрейм для кнопок
        button_frame = ttk.Frame(parent, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, 
                  text=self.localization.tr("apply_button"), 
                  command=self.apply_new_paths).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, 
                  text=self.localization.tr("cancel_button"), 
                  command=self.path_editor.destroy).pack(side=tk.LEFT)
        
        # Автозаполнение пути из первого выделенного трека
        if selected_items:
            first_item = selected_items[0]
            values = self.tree.item(first_item)['values']
            if len(values) >= 2:
                full_path = values[2]  # Теперь здесь полный путь
                dir_path = os.path.dirname(full_path)
                self.new_path_entry.delete(0, tk.END)
                self.new_path_entry.insert(0, dir_path)
                print(f"[DEBUG] Данные трека = {self.tree.item(first_item)}")

    def create_name_editor_tab(self, parent, selected_items):
        """Создает содержимое вкладки для изменения имени"""
        # Фрейм для таблицы
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Таблица с выделенными треками
        tree = ttk.Treeview(table_frame, columns=('num', 'name'), show='headings')
        tree.heading('num', text=self.localization.tr("track_number"))
        tree.heading('name', text=self.localization.tr("track_name"))
        tree.column('num', width=50, anchor='center')
        tree.column('name', width=400, anchor='w')
        
        # Заполняем таблицу выделенными треками
        for item in selected_items:
            values = self.tree.item(item)['values']
            if len(values) >= 2:
                tree.insert('', 'end', values=(values[0], values[1]))
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Фрейм для поля ввода имени
        name_frame = ttk.Frame(parent, padding="10")
        name_frame.pack(fill=tk.X)
        
        ttk.Label(name_frame, text=self.localization.tr("new_name_label")).pack(anchor='w')
        
        # Поле ввода имени
        self.new_name_entry = ttk.Entry(name_frame)
        self.new_name_entry.pack(fill=tk.X, pady=5)
        
        # Подсказка
        ttk.Label(name_frame, 
                 text=self.localization.tr("name_example_hint"), 
                 font=('TkDefaultFont', 8)).pack(side=tk.LEFT)
        
        # Фрейм для кнопок
        button_frame = ttk.Frame(parent, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, 
                  text=self.localization.tr("apply_button"), 
                  command=self.apply_new_names).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, 
                  text=self.localization.tr("cancel_button"), 
                  command=self.path_editor.destroy).pack(side=tk.LEFT)
        
        # Автозаполнение имени из первого выделенного трека
        if selected_items:
            first_item = selected_items[0]
            values = self.tree.item(first_item)['values']
            if len(values) >= 2:
                name = os.path.basename(values[1])
                self.new_name_entry.insert(0, name)
        

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
            
            # Получаем ID выделенных элементов в Treeview
            selected_items = self.tree.selection()
            
            for item in selected_items:
                # Получаем реальный индекс через теги или данные
                item_values = self.tree.item(item, 'values')
                if not item_values or len(item_values) < 2:
                    continue
                    
                # Находим трек по номеру (первое значение в строке)
                track_num = int(item_values[0]) - 1  # -1 потому что нумерация с 1
                
                if 0 <= track_num < len(self.temp_list):
                    track = self.temp_list[track_num]
                    original_path = track.get("original_path", track["path"])
                    filename = track["name"]
                    new_full_path = os.path.normpath(new_path + filename)
                    
                    # Обновляем словарь изменённых путей
                    self.modified_paths[original_path] = new_full_path
                    
                    # Обновляем трек
                    track["path"] = new_full_path
                    track["was_modified"] = True
                    track["was_restored"] = False
                    track["original_path"] = original_path
                    
                    if track.get('was_name_modified', False):
                        track["was_name_modified"] = True
                        
            self.display_tracks = self.temp_list.copy()
            self.update_display()
            self.save_state()
            
            self.shuffled_list = None
            self.show_message(self.localization.tr("paths_updated"), "green")
            if self.path_editor:
                self.path_editor.destroy()
                self.path_editor = None
                
        except Exception as e:
            self.show_message(f"{self.localization.tr('error')}: {str(e)}", "red")

    def apply_new_names(self):
        """Применяет новые имена к выделенным трекам"""
        try:
            new_name = self.new_name_entry.get().strip()
            if not new_name:
                raise ValueError(self.localization.tr("error_empty_name"))
            
            if self.temp_list is None:
                self.temp_list = [track.copy() for track in self.display_tracks]
            
            selected_items = self.tree.selection()
            
            for item in selected_items:
                item_values = self.tree.item(item, 'values')
                if not item_values or len(item_values) < 2:
                    continue
                    
                track_num = int(item_values[0]) - 1
                
                if 0 <= track_num < len(self.temp_list):
                    track = self.temp_list[track_num]
                    if 'original_name' not in track:
                        track['original_name'] = track['name']
                    
                    track['name'] = new_name
                    track['was_name_modified'] = True
                    
                    if track.get('was_modified', False):
                        track['was_modified'] = True
                    
            self.display_tracks = self.temp_list.copy()
            self.update_display()
            self.save_state()
            
            self.shuffled_list = None
            self.show_message(self.localization.tr("names_updated"), "green")
            if self.path_editor:
                self.path_editor.destroy()
                self.path_editor = None
                
        except Exception as e:
            self.show_message(f"{self.localization.tr('error')}: {str(e)}", "red")
        
        