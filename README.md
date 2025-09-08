# tmus

A terminal-based music player for organized music directories, using VLC for playback.

<img width="1212" height="587" alt="image" src="https://github.com/user-attachments/assets/3c86f7a6-e268-415e-849f-1ba009cc9d8c" />


## Features
- Browse artists and songs from your music directory
- Play, pause, and repeat songs
- Caches your music library for fast startup

## Installation

```
pip install tmus
```

## Usage

Make sure your music directory is structured in this way:
Artists > Albums > Songs
OR 
a flat directory containing songs

```
tmus <path-to-music-directory>
```

## Requirements
- Python 3.8+
- VLC media player installed
### Windows 
- https://images.videolan.org/vlc/
### Linux
- sudo apt install vlc libvlc-dev

## Platform Notes
- On Windows, `windows-curses` is required (installed automatically)

## License
MIT
