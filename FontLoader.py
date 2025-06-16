import os
import sys
import tempfile
import ctypes
import shutil  # Для копирования файлов
from tkinter import font, ttk
from ctypes import wintypes

class FontLoader:
    def __init__(self):
        self.temp_font_path = None
        self.temp_icon_path = None  # Добавляем атрибут для пути к временной иконке
        self.symbol_font = self._load_font()
        self.icon_ico = self._load_icon()  # Загружаем иконку
        
    def _load_font(self):
        """Основной метод загрузки шрифта"""
        try:
            # 1. Найти файл шрифта
            font_path = self._find_font_file()
            if not font_path:
                return "Arial"
                
            # 2. Временно установить шрифт в систему
            if not self._install_font(font_path):
                return "Arial"
                
            # 3. Получить настоящее имя шрифта
            font_name = self._get_font_name(font_path)
            return font_name if font_name else "Arial"
            
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки шрифта: {e}")
            return "Arial"

    def _find_font_file(self):
        """Поиск файла шрифта в разных местах"""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "action_symbols.ttf"),
        ]
        
        for path in filter(None, possible_paths):
            if os.path.exists(path):
                return path
                
        # Если файл не найден, попробуем создать временный
        try:
            import pkgutil
            font_data = pkgutil.get_data(__name__, "action_symbols.ttf")
            if font_data:
                self.temp_font_path = os.path.join(tempfile.gettempdir(), "action_symbols_temp.ttf")
                with open(self.temp_font_path, "wb") as f:
                    f.write(font_data)
                return self.temp_font_path
        except:
            pass
            
        return None

    def _install_font(self, font_path):
        """Временная установка шрифта в систему"""
        try:
            FR_PRIVATE = 0x10
            if ctypes.windll.gdi32.AddFontResourceExW(ctypes.create_unicode_buffer(font_path), FR_PRIVATE, 0):
                # Обновляем кэш шрифтов
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
                print(f"[DEBUG] Установлен шрифт: {font_path}")
                return True
        except Exception as e:
            print(f"[DEBUG] Ошибка установки шрифта: {e}")
        return False

    def _get_font_name(self, font_path):
        """Получение имени шрифта из файла"""
        try:
            from fontTools.ttLib import TTFont
            with TTFont(font_path) as f:
                for record in f['name'].names:
                    if record.nameID == 1 and record.platformID == 3:
                        return record.toStr()
                return os.path.splitext(os.path.basename(font_path))[0]
        except:
            return None

    def __del__(self):
        """Автоматическое удаление временного шрифта при завершении"""
        if self.temp_font_path and os.path.exists(self.temp_font_path):
            try:
                os.remove(self.temp_font_path)
            except:
                pass
              
              
    def _load_icon(self):
        """Загрузка иконки во временную папку и установка."""
        try:
            # 1. Найти файл иконки
            icon_path = self._find_icon_file()
            if not icon_path:
                print("[DEBUG] Файл иконки не найден.")
                return
            # 2. Скопировать иконку во временную папку
            temp_icon_path = self._copy_icon_to_temp(icon_path)
            if not temp_icon_path:
                return
            self.temp_icon_path = temp_icon_path  # Сохраняем путь к временной иконке
            return temp_icon_path
            print(f"[DEBUG] Установлена иконка: {self.temp_icon_path}")
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки иконки: {e}")
            
    
    def _find_icon_file(self):
        """Поиск файла иконки."""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "Icon.ico"),
        ]
        for path in filter(None, possible_paths):
            if os.path.exists(path):
                return path
        
        # Если файл не найден, попробуем создать временный
        try:
            import pkgutil
            icon_data = pkgutil.get_data(__name__, "Icon.ico")
            if icon_data:
                self.temp_icon_path = os.path.join(tempfile.gettempdir(), "Icon_temp.ico")
                with open(self.temp_icon_path, "wb") as f:
                    f.write(icon_data)
                return self.temp_icon_path
        except:
            pass
      
        return None        
    
    def _copy_icon_to_temp(self, icon_path):
        """Копирование иконки во временную папку."""
        try:
            temp_dir = tempfile.gettempdir()
            temp_icon_path = os.path.join(temp_dir, "Icon.ico")  # Имя файла должно совпадать с тем, что ожидает iconbitmap
            shutil.copy2(icon_path, temp_icon_path)
            return temp_icon_path
        except Exception as e:
            print(f"[DEBUG] Ошибка копирования иконки: {e}")
            return None
    