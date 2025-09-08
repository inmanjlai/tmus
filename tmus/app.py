#!/usr/bin/env python3
import curses
import sys
import os
import vlc
# Update this import to use the new optimized functions
from tmus.library_cache import update_library_cache
from tmus.music_scanner import flatten_album

PADDING = 4

def show_loading_screen(stdscr, progress, total):
    """Display a centered loading screen with progress"""
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    
    # Center the loading text
    loading_text = f"Importing library {progress}/{total} songs"
    y = height // 2
    x = (width - len(loading_text)) // 2
    
    stdscr.addstr(y, x, loading_text, curses.A_BOLD)
    
    # Add a simple progress bar
    if total > 0:
        bar_width = min(50, width - 4)  # Max 50 chars wide, or fit to screen
        filled = int((progress / total) * bar_width)
        bar_x = (width - bar_width) // 2
        
        stdscr.addstr(y + 2, bar_x, "[ " + "█" * filled + "░" * (bar_width - filled) + " ]")
        
        # Show percentage
        percent = f"{int((progress / total) * 100)}%"
        percent_x = (width - len(percent)) // 2
        stdscr.addstr(y + 4, percent_x, percent)
    
    stdscr.refresh()

# refactor artists and songs to use draw list
def draw_list(win, items, offset, selected, max_rows):
    visible = items[offset:offset + max_rows]
    for i, item in enumerate(visible):
        if i + offset == selected:
            win.addstr(i + 1, 2, item, curses.A_STANDOUT)
        else:
            win.addstr(i + 1, 2, item)

def main_ui(stdscr, path):
    # INITIALIZATION
    curses.curs_set(0)
    
    # Show initial loading screen
    show_loading_screen(stdscr, 0, 0)
    
    # Create a progress callback
    def progress_callback(current, total):
        show_loading_screen(stdscr, current, total)
    
    # UPDATED: Import the optimized scan function
    try:
        from tmus.music_scanner import scan_music_optimized
        scan_func = scan_music_optimized
    except ImportError:
        from tmus.music_scanner import scan_music_parallel
        # Fallback to original if optimized version not available
        scan_func = scan_music_parallel
    
    # You can add flatten=True here if you want flattened libraries
    # or add it as a command line argument
    def scan_with_flatten(path, progress_callback=None, total_files=None):
        return scan_func(path, progress_callback, total_files, flatten=False)
    
    # Load library with progress updates - this will now use proper caching
    library = update_library_cache(path, scan_with_flatten, progress_callback)
    
    selected_artist = 0
    artist_offset = 0
    selected_song = 0
    song_offset = 0
    curr_song = None
    curr_artist = None
    playing = False
    repeat = False

    if not library:
        stdscr.clear()
        stdscr.addstr(0, 0, "No mp3 files found in the specified path.")
        stdscr.getch()
        return
    
    artists = list(library.keys())

    instance = vlc.Instance()
    player = instance.media_player_new()
    volume = 50
    player.audio_set_volume(volume)

    # Initial window setup
    height, width = stdscr.getmaxyx()
    max_rows = height - 10
    artist_win_height = height - 8
    artist_win = curses.newwin(artist_win_height, int(width/2), 2, 0)
    songs_win = curses.newwin(artist_win_height, int(width/2), 2, int(width/2))

    while True:
        stdscr.timeout(200)  # wait max 200ms for key, then return -1 if no input

        # Handle resize
        new_height, new_width = stdscr.getmaxyx()
        if (new_height, new_width) != (height, width):
            selected_artist = 0
            artist_offset = 0
            selected_song = 0
            song_offset = 0
            height, width = new_height, new_width
            max_rows = height - 10
            artist_win_height = height - 8
            artist_win = curses.newwin(artist_win_height, int(width/2), 2, 0)
            songs_win = curses.newwin(artist_win_height, int(width/2), 2, int(width/2))
            stdscr.clear()

        # Redraw header and footer every loop for dynamic update
        stdscr.addstr(1, 1, "TMUS - Terminal Music Player", curses.A_BOLD)
        footer = "[q] quit     [p] pause    [+/-] volume     [Enter] play"
        stdscr.addstr(height - 1, int(width/2 - len(footer)/2), footer, curses.A_BOLD)
        
        # Only clear and redraw the content windows
        artist_win.clear()
        songs_win.clear()
        artist_win.box()
        songs_win.box()

        # ---------- HEADER SECTION ----------
        if repeat:
            stdscr.addstr(1, width - len(" [r] repeat: ON ") - 1, " [r] repeat: ON ", curses.A_BOLD | curses.color_pair(1))
        else:
            stdscr.addstr(1, width - len(" [r] repeat: OFF ") - 1, " [r] repeat: OFF ", curses.A_BOLD)

        # ---------- ARTISTS SECTION ----------
        # Test an artist with more songs than space permits
        visible_artists = artists[artist_offset:artist_offset + max_rows]
        for i in range(len(visible_artists)):
            if i >= max_rows: break
            if selected_artist == i: artist_win.addstr(i + 1, 2, visible_artists[i], curses.A_STANDOUT)
            else: artist_win.addstr(i + 1, 2, visible_artists[i])

        # ---------- SONGS SECTION ----------
        current_artists_albums = library[visible_artists[selected_artist]]
        all_songs_by_artist = flatten_album(current_artists_albums)

        visible_songs = all_songs_by_artist[song_offset : song_offset + max_rows]
        for i, song in enumerate(visible_songs):
            song_split = os.path.basename(song)
            if i == selected_song + song_offset:
                songs_win.addstr(i + 1, 2, song_split, curses.A_STANDOUT)
            else:
                songs_win.addstr(i + 1, 2, song_split)
        
        # ---------- NOW PLAYING SECTION ----------
        if curr_song and curr_artist:
            stdscr.addstr(height - 5, 1, " " * (width - 2))
            stdscr.addstr(height - 3, 1, " " * (width - 2))

            pos = player.get_time() / 1000
            duration = player.get_length() / 1000

            if duration <= 0:
                duration = 1

            # Repeat logic: if repeat is on and song finished, restart
            if repeat and player.get_state() == vlc.State.Ended:
                player.stop()
                media = instance.media_new(curr_song)
                player.set_media(media)
                player.play()

            now_playing = f"now playing: {os.path.basename(curr_song)}"

            # Volume bar: 10 segments, right-aligned
            vol_blocks = int((volume / 100) * 20)
            vol_bar = "-" * vol_blocks + " " * (20 - vol_blocks)
            vol_percent = f"{volume}%"
            # Center the percentage in the bar
            percent_pos = 10 - len(vol_percent)//2
            vol_bar_with_percent = (
                vol_bar[:percent_pos] +
                vol_percent +
                vol_bar[percent_pos + len(vol_percent):]
            )
            vol_str = f" volume [{vol_bar_with_percent}] "
            # Calculate where to start the volume bar (right-aligned)
            vol_x = width - len(vol_str)
            # Truncate now_playing if it would overlap the volume bar
            max_now_playing_len = vol_x - 2
            now_playing_disp = now_playing[:max_now_playing_len]
            stdscr.addstr(height - 5, 1, now_playing_disp, curses.A_BOLD)
            stdscr.addstr(height - 5, vol_x, vol_str, curses.A_BOLD)
            bar_width = max(1, width - 2)

            progress = int((pos/duration) * bar_width)
            stdscr.addstr(height - 3, 1, "█" * progress)
            stdscr.addstr(height - 3, 1 + progress, "░" * (bar_width - progress))
            time_info = f" {int(pos//60)}:{int(pos%60):02d} / {int(duration//60)}:{int(duration%60):02d} "
            stdscr.addstr(height - 3, int(width/2 - len(time_info)/2), time_info, curses.A_BOLD)

        stdscr.refresh()
        artist_win.refresh()
        songs_win.refresh()
        key = stdscr.getch()

        # ---------- NAVIGATION ----------
        if key == curses.KEY_UP:
            song_offset = 0
            selected_song = 0
            if selected_artist > 0:
                selected_artist -= 1
            elif selected_artist + artist_offset > 0:
                artist_offset -= 1
        elif key == curses.KEY_DOWN:
            song_offset = 0
            selected_song = 0
            if selected_artist < min(max_rows - 1, len(artists) -  1):
                selected_artist += 1
            elif selected_artist + artist_offset < len(artists) - 1:
                artist_offset += 1
        elif key == curses.KEY_LEFT:
            if selected_song > 0:
                selected_song -= 1
            elif selected_song + song_offset > 0:
                song_offset -= 1
        elif key == curses.KEY_RIGHT:
            if selected_song < min(max_rows - 1, len(all_songs_by_artist) - 1):
                selected_song += 1
            elif selected_song + song_offset < len(all_songs_by_artist) - 1:
                song_offset += 1
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            curr_song = visible_songs[selected_song]
            curr_artist = visible_artists[selected_artist]
            media = instance.media_new(curr_song)
            player.set_media(media)
            player.play()
            playing = True
        elif key == ord("="):
            volume = min(100, volume + 5)
            player.audio_set_volume(volume)
        elif key == ord("-"):
            volume = max(0, volume - 5)
            player.audio_set_volume(volume)
        elif key == ord("p"):
            if playing:
                player.pause()
            else:
                player.pause()
        elif key == ord("r"):
            repeat = not repeat
        elif key == ord("q"):
            break
        elif key == -1:
            # no key pressed, just continue
            pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python app.py <music_directory>")
        sys.exit(1)
    curses.wrapper(main_ui, sys.argv[1])

if __name__ == "__main__":
    main()