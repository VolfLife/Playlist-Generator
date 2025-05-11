
# Playlist Generator

Интуитивно понятный и простой генератор для создания плейлиста с случайным списком треков

## Возможности

* Записывает пути только аудио–файлов: 
	```
	.mp3, .flac, .ogg, .wav, .m4a, .aac
	```
* Перемешивает список треков, используя случайно сгенерированный/пользовательский cид

* Использование теневого сида и реверса для более сложного перемешивания

* Ввод данных для повторного воспроизведения плейлиста

* Записывает метаданные в плейлист: 
	```
	#EXTM3U
	#Created by VolfLife's Playlist Generator
	#GENERATED:2025-03-29 01:24:00
	#PLAYLIST:my_playlist
	#SEED:89451...
	#SHADOW_SEED:11042...
	#REVERSE_STEP:19
	#TRACKS:25
	...
	```
* Создает `.m3u8`–плейлист
	>*очевидно*
	
## Сборка

1. Установить [Python](https://www.python.org/downloads/windows/), pip
2. В терминале:

	```
	pip install pyinstaller
	```
	```
	pyinstaller --onefile --windowed --icon=PlaylistGeneratorIcon.ico --name "Playlist Generator" "PlaylistGenerator.py"
	```
