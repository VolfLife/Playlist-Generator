# Playlist Generator

An intuitive and simple tool for generating and editing randomly shuffled playlists.

## Key Features

* Clean, minimalist interface

* Multi-language support

* Dual-functionality: Generator & Editor

* Supported audio and video formats:

	* Audio:	`.mp3`, `.flac`, `.ogg`, `.wav`, `.m4a`, `.aac`, `.wma`, `.opus`, `.aiff`, `.aif`, `.alac`, `.dsf`, `.dff`, `.mka`, `.ac3`, `.dts`

	* Video: 	`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.ts`, `.m2ts`, `.3gp`, `.vob`, `.ogv`

* Seed-based shuffling for reproducible results

* Advanced mixing options:

	* Shadow seed for complex shuffling

	* Reversal step algorithm

* Preserves playlist metadata:

```
#EXTM3U
#Made by VolfLife's Playlist Generator
#GENERATED:2025-03-29 01:24:00
#PLAYLIST:my_playlist
#SEED:7034926188901
#SHADOW_SEED:1104258672009899
#REVERSE_STEP:19
#TRACKS:25
...
```

>*Note: Translations may contain errors*

## Usage

The program operates in two modes: GENERATOR or EDITOR.


### Generator Mode
___

![Generator Interface](https://github.com/VolfLife/Playlist-Generator/blob/main/screenshots/generator_img.png)

Creates `.m3u8`/`.m3u`/`.pls`/`.asx`/`.xspf`/`.txt` playlist from scratch. Simply launch the executable to enter generator mode.

#### How to use

1. Select music folder(s)

2. Enter a name playlist

3. Enter a custom seed or leave blank for random generation

4. Set reversal step size (optional)

5. Enable shadow seed for advanced shuffle (optional)

6. Choose file format (optional)

7. Click "Generate playlist" button. The playlist will be saved in the program’s directory

### Editor Mode
___

![Editor Interface](https://github.com/VolfLife/Playlist-Generator/blob/main/screenshots/editor_img.png)

Edits and saves data from existing playlists without requiring local track files. Launch by drag-and-dropping `.m3u8`/`.m3u`/`.pls`/`.asx`/`.xspf`/`.txt` file(s) onto the program shortcut.

#### Features:

* All generator mixing options (excluding shadow seed)

* Manual track management:

	* Reorder with drag-and-drop or ▲/▼ buttons

  	* Delete tracks

	* Edit track paths and names
	
	* Undo/redo actions

## Compilation

1. Install [Python](https://www.python.org/downloads/windows/) + pip

2. Run in terminal:

	2.1.
	```
	pip install pyinstaller
	```

  	2.2.
   	```
	pip install fonttools
	```

 	2.3.
	```
	pyinstaller --onefile --hidden-import=_pylong --hidden-import=fontTools --windowed --add-data "version_info.py;." --add-data "action_symbols.ttf;." --add-data "Icon.ico;." --icon=Icon.ico --name "Playlist Generator" --version-file version_info.txt "PlaylistGenerator.py"
	```

 3. The compiled `.exe` file will be ready in the *`dist`* folder
