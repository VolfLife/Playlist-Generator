import os
import sys
import tempfile
import ctypes
import shutil
import threading
from tkinter import font
from ctypes import wintypes

class FontLoader:
    def __init__(self):
        self._font_path = None
        self._font_name = None
        self._font_installed = False
        self.icon_ico = self._load_icon()
        self._load_font_data()  # Загружаем данные шрифта
        
    def get_font_name(self):
        """Возвращает имя загруженного шрифта"""
        if not self._font_installed:
            self._install_font_sync()  # Устанавливаем синхронно, если не установлен
        return self._font_name if self._font_name else "Arial"

    def _load_font_data(self):
        """Основная загрузка данных шрифта"""
        try:
            # 1. Находим файл шрифта
            self._font_path = self._locate_font_file()
            if not self._font_path:
                print("[ERROR] Font file not found")
                messagebox.showerror("Ошибка", "Файл шрифта action_symbols.ttf не найден")
                return

            # 2. Читаем имя шрифта из файла
            self._font_name = self._extract_font_name(self._font_path)
            if not self._font_name:
                print("[ERROR] Could not extract font name")
                self._font_name = "Arial"
                
            print(f"[INFO] Font name: {self._font_name}")

            # 3. Пытаемся установить шрифт асинхронно
            self._install_font_async()
            
        except Exception as e:
            print(f"[ERROR] Font loading failed: {e}")
            messagebox.showerror("Ошибка", f"Ошибка загрузки шрифта: {str(e)}")

    def _install_font_sync(self):
        """Синхронная установка шрифта (используется как fallback)"""
        try:
            if not self._font_path or self._font_installed:
                return

            FR_PRIVATE = 0x10
            if ctypes.windll.gdi32.AddFontResourceExW(
                ctypes.create_unicode_buffer(self._font_path),
                FR_PRIVATE,
                0
            ):
                # Обновляем кэш шрифтов
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
                self._font_installed = True
                print("[INFO] Font installed synchronously")
        except Exception as e:
            print(f"[ERROR] Sync font install failed: {e}")

    def _locate_font_file(self):
        """Поиск файла шрифта с проверкой в нескольких местах"""
        search_locations = [
            os.path.join(os.path.dirname(__file__), "action_symbols.ttf"),
            os.path.join(os.getcwd(), "action_symbols.ttf"),
            os.path.join(tempfile.gettempdir(), "action_symbols.ttf"),
            getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)),  # Для pyinstaller
        ]

        for location in search_locations:
            full_path = os.path.join(location, "action_symbols.ttf") if os.path.isdir(location) else location
            if os.path.exists(full_path):
                try:
                    # Проверяем что это валидный TTF файл
                    with open(full_path, 'rb') as f:
                        if f.read(4) == b'\x00\x01\x00\x00':  # TTF signature
                            return full_path
                except:
                    continue
        return None

    def _extract_font_name(self, font_path):
        """Извлекаем имя шрифта из файла"""
        try:
            from fontTools.ttLib import TTFont
            with TTFont(font_path) as f:
                for record in f['name'].names:
                    if record.nameID == 1 and record.platformID == 3:  # Font Family Name
                        return record.toStr()
                return os.path.splitext(os.path.basename(font_path))[0]
        except Exception as e:
            print(f"[ERROR] Font name extraction failed: {e}")
            return None

    def _install_font_async(self):
        """Асинхронная установка шрифта через WinAPI"""
        try:
            if not self._font_path or self._font_installed:
                return

            def install_thread():
                try:
                    FR_PRIVATE = 0x10
                    if ctypes.windll.gdi32.AddFontResourceExW(
                        ctypes.create_unicode_buffer(self._font_path),
                        FR_PRIVATE,
                        0
                    ):
                        # Обновляем кэш шрифтов
                        ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
                        self._font_installed = True
                        print("[INFO] Font installed asynchronously")
                except Exception as e:
                    print(f"[ERROR] Async font install failed: {e}")

            thread = threading.Thread(target=install_thread, daemon=True)
            thread.start()

        except Exception as e:
            print(f"[ERROR] Async font install setup failed: {e}")


    def __del__(self):
        """Очистка ресурсов"""
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

