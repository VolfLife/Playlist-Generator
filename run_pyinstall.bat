@echo off
pyinstaller --onefile --hidden-import=_pylong --hidden-import=fontTools --hidden-import=mutagen --windowed --add-data "version_info.py;." --add-data "action_symbols.ttf;." --add-data "Icon.ico;." --icon=Icon.ico --name "Playlist Generator" --version-file version_info.txt "PlaylistGenerator.py"
pause