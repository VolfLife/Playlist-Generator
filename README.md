# Playlist Generator

An intuitive and simple tool for generating and editing randomly shuffled playlists.

To download the program, go to the [Releases](https://github.com/VolfLife/Playlist-Generator/releases/latest) page.

## Key Features

* Clean, minimalist interface

* Multi-language support

* Dual-functionality: Generator & Editor

* Supported playlist formats:

	* For generating:	 `.m3u8, .m3u, .pls, .wpl, .asx, .xspf, .json, .xml, .txt`

	* For editing: 		`.m3u8, .m3u, .pls, .wpl, .asx, .xspf, .json, .xml, .txt` + `.wax, .wvx,`

* Supported audio and video formats:

	* Audio:	`.mp3, .flac, .ogg, .wav, .m4a, .aac, .wma, .opus, .aiff, .aif, .alac, .dsf, .dff, .mka, .ac3, .dts`

	* Video: 	`.mp4, .mkv, .avi, .mov, .wmv, .flv, .webm, .m4v, .mpg, .mpeg, .ts, .m2ts, .3gp, .vob, .ogv`

* Seed-based shuffling for reproducible results

* Custom extra swaps & segmented block reversal algorithms for complex shuffling

* Сounter of the total duration of tracks from the selected folder(s)

* Preserves playlist metadata:

```
#EXTM3U
#Made by VolfLife's Playlist Generator
#GENERATED:2025-03-29 01:24:00
#PLAYLIST:my_playlist
#DURATION:52:33.09
#SEED:7034926188901
#SHADOW_SEED:1104258672009899
#NUM_SWAPS:21
#REVERSE_STEP:19
#TRACKS:25
...
```

>*Note: Translations are machine-generated and may contain errors*

## Usage

The program operates in two modes: Generator or Editor.


### Generator Mode
___

![Generator Interface](https://github.com/VolfLife/Playlist-Generator/blob/main/screenshots/generator_img.png)

Creates a playlist from scratch. Simply launch the executable to enter generator mode.


#### How to use:

1. Select music folder(s)

2. Enter name playlist

3. Enter a custom seed or leave blank for random generation

4. Configure optional settings:
	
 	* **Extra swaps**: Enable for secondary shuffling
	
 	* **Reversal Step**: Set block size for reverse shuffling

 	* **Shadow Seed**: Alternative seed for wider permutation coverage

	* **Format**: Select output format (`.m3u`/`.pls`/etc.)

5. Click *`Generate playlist`* button. The playlist will be saved in the program’s directory

### Editor Mode
___

![Editor Interface](https://github.com/VolfLife/Playlist-Generator/blob/main/screenshots/editor_img.png)

Edits and saves data from existing playlists without requiring local track files. Launch by drag-and-dropping playlist file(s) onto the program shortcut.


#### Features:

* All generator mixing options

* Quick track search/filter by name

* Manual track management:

	* Reorder with drag-and-drop or ▲/▼ buttons

  	* Edit track paths and names

	* Import from folders/playlists with drag-and-drop

	* Delete tracks
	
	* Undo/redo actions

## Compilation

1. Install [Python 3.11+](https://www.python.org/downloads/windows/) and pip

2. Run the following commands in your terminal/command prompt:

	2.1. Install required packages
	```
	pip install pyinstaller fonttools mutagen tkinterdnd2
	```

 	2.2. Compile the application
	```
	pyinstaller --onefile --hidden-import=_pylong --hidden-import=fontTools --hidden-import=mutagen --windowed --add-data "version_info.py;." --add-data "action_symbols.ttf;." --add-data "Icon.ico;." --icon=Icon.ico --name "Playlist Generator" --version-file version_info.txt "PlaylistGenerator.py"
	```

 3. The compiled `.exe` file will be generated in the *`dist`* folder
