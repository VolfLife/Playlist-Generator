# Playlist Generator

An intuitive and simple tool for generating and editing randomly shuffled playlists.

## Key Features

* Clean, minimalist interface

* Multi-language support

	>*Note: Translations may contain minor errors*

* Dual-functionality: Generator & Editor

* Supported audio formats:

	`mp3, .flac, .ogg, .wav, .m4a, .aac`

* Seed-based shuffling for reproducible results

* Advanced mixing options:

	* Shadow seed for complex shuffling

	* Reversal step algorithm

* Preserves playlist metadata:

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


## Usage

The program operates in two modes: GENERATOR or EDITOR.


### Generator Mode
___

![Generator Interface](https://github.com/VolfLife/fractureiser-samples/blob/main/screenshots/generator_img.png)

Creates `.m3u8` playlists from scratch. Simply launch the executable to enter generator mode.

1. Select your music folder/folders

2. Name your playlist

3. Enter a custom seed or leave blank for random generation

4. Set reversal step size (optional)

5. Enable shadow seed for advanced shuffling (optional)

6. Click "Generate playlist" - the playlist will be saved in the program directory

### Editor Mode
___

![Editor Interface](https://github.com/VolfLife/fractureiser-samples/blob/main/screenshots/editor_img.png)

Modify existing playlists - works even with missing local files. Launch by drag-and-dropping `.m3u8`/`.m3u`/`.txt` file(s) onto the program shortcut.

#### Features:

* All generator mixing options (excluding shadow seed)

* Manual track management:

	* Reorder with drag-and-drop or ▲/▼ buttons

  	* Delete tracks

	* Undo/redo actions
	
	* Edit track paths


## Compilation

1. Install [Python](https://www.python.org/downloads/windows/) with pip

2. Run in terminal:

```
pip install pyinstaller
```

```
pyinstaller --onefile --windowed --icon=Icon.ico --name "Playlist Generator" "PlaylistGenerator.py"
```
