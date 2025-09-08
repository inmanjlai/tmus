# tmus

A terminal-based music player for organized music directories, using VLC for playback.

<img width="1214" height="605" alt="image" src="https://github.com/user-attachments/assets/35511852-ad50-4b15-ba13-344cd9179958" />


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

```
tmus <path-to-music-directory>
```

## Requirements
- Python 3.8+
- VLC media player installed

## Platform Notes
- On Windows, `windows-curses` is required (installed automatically)

## License
MIT
