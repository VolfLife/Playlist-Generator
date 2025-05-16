@echo off
pyinstaller --onefile --hidden-import=_pylong --windowed --add-data "version_info.py;." --icon=Icon.ico --name "Playlist Generator" --version-file version_info.txt "PlaylistGenerator.py"
pause