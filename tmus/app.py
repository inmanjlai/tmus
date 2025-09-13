#!/usr/bin/env python3
import curses
import sys
import os
import vlc
# Update this import to use the new optimized functions
from tmus.library_cache import update_library_cache
from tmus.music_scanner import flatten_album

PADDING = 2

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

def search_library(library, query):
    """Search for artists and songs matching the query"""
    if not query:
        return library, list(library.keys())

    query_lower = query.lower()
    filtered_library = {}
    filtered_artists = []

    # Search artists and their songs
    for artist, albums in library.items():
        artist_matches = query_lower in artist.lower()

        # Get all songs for this artist
        all_songs = flatten_album(albums)
        song_matches = any(query_lower in os.path.basename(song).lower() for song in all_songs)

        # Include artist if name matches or any song matches
        if artist_matches or song_matches:
            filtered_library[artist] = albums
            filtered_artists.append(artist)

    return filtered_library, filtered_artists

def draw_search_input(stdscr, query, search_active, height, width):
    """Draw the search input field at the bottom"""
    if search_active:
        search_text = f"Search: {query}"
        search_y = height - 1
        # Clear the search line
        stdscr.addstr(search_y, PADDING, " " * (width - 2 * PADDING))
        # Draw search input with cursor
        stdscr.addstr(search_y, PADDING, search_text)
        stdscr.addstr(search_y, PADDING + len(search_text), "_", curses.A_BLINK)

        # Instructions
        instructions = "[Enter] search [Esc] cancel"
        stdscr.addstr(search_y, width - len(instructions) - PADDING, instructions, curses.A_DIM)

def main_ui(stdscr, path):
    flat_dir = False
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
        flat_dir = True
        return scan_func(path, progress_callback, total_files, flatten=False)
    
    # Load library with progress updates - this will now use proper caching
    library = update_library_cache(path, scan_with_flatten, progress_callback)

    # Clear screen to remove any print statements from cache loading
    stdscr.clear()
    stdscr.refresh()

    selected_artist = 0
    artist_offset = 0
    selected_song = 0
    song_offset = 0
    curr_song = None
    curr_artist = None
    playing = False
    repeat = False

    # Search state
    search_active = False
    search_query = ""
    filtered_library = library
    filtered_artists = list(library.keys())

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

    # Initial window setup with proper padding
    height, width = stdscr.getmaxyx()
    content_height = height - 10  # Reserve space for header, footer, now playing, search
    content_width = width - 2 * PADDING
    artist_win_width = content_width // 2 - 1
    songs_win_width = content_width - artist_win_width - 1

    max_rows = content_height - 2  # Account for window borders
    artist_win = curses.newwin(content_height, artist_win_width, 3, PADDING)
    songs_win = curses.newwin(content_height, songs_win_width, 3, PADDING + artist_win_width + 1)

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
            content_height = height - 10
            content_width = width - 2 * PADDING
            artist_win_width = content_width // 2 - 1
            songs_win_width = content_width - artist_win_width - 1
            max_rows = content_height - 2
            artist_win = curses.newwin(content_height, artist_win_width, 3, PADDING)
            songs_win = curses.newwin(content_height, songs_win_width, 3, PADDING + artist_win_width + 1)
            stdscr.clear()

        # Clear and redraw header every loop for dynamic update
        if width > 2 * PADDING:  # Safety check
            stdscr.addstr(1, PADDING, " " * (width - 2 * PADDING))  # Clear entire header line
        stdscr.addstr(1, PADDING, "TMUS - Terminal Music Player", curses.A_BOLD)

        # Show search indicator in header if active
        if search_active:
            search_indicator = "[SEARCH MODE]"
            stdscr.addstr(1, width - len(search_indicator) - PADDING, search_indicator, curses.A_BOLD | curses.color_pair(1) if curses.has_colors() else curses.A_REVERSE)
        elif search_query:
            search_status = f"[Filtered: {search_query}]"
            stdscr.addstr(1, width - len(search_status) - PADDING, search_status, curses.A_DIM)

        # Clear and redraw footer with search instruction
        stdscr.addstr(height - 2, 0, " " * (width - 1))  # Clear entire footer line (width-1 to avoid bounds error)
        if search_active:
            pass
        elif search_query:
            footer = "[q] quit  [p] pause  [+/-] vol  [< / >] seek  [Enter] play  [/] search  [c] clear"
            stdscr.addstr(height - 2, int(width/2 - len(footer)/2), footer, curses.A_BOLD)
        else:
            footer = "[q] quit  [p] pause  [+ / -] vol  [< / >] seek  [Enter] play  [/] search"
            stdscr.addstr(height - 2, int(width/2 - len(footer)/2), footer, curses.A_BOLD)
        
        # Only clear and redraw the content windows
        artist_win.clear()
        songs_win.clear()
        artist_win.box()
        songs_win.box()

        # ---------- HEADER SECTION ----------
        repeat_text = " [r] repeat: ON " if repeat else " [r] repeat: OFF "
        repeat_color = curses.A_BOLD | (curses.color_pair(1) if repeat and curses.has_colors() else 0)
        stdscr.addstr(2, width - len(repeat_text) - PADDING, repeat_text, repeat_color)

        # ---------- ARTISTS SECTION ----------
        current_artists = filtered_artists if search_query else artists
        visible_artists = current_artists[artist_offset:artist_offset + max_rows]

        for i in range(len(visible_artists)):
            if i >= max_rows:
                break
            if selected_artist == i:
                artist_win.addstr(i + 1, 2, visible_artists[i], curses.A_STANDOUT)
            else:
                artist_win.addstr(i + 1, 2, visible_artists[i])

        # ---------- SONGS SECTION ----------
        if visible_artists and selected_artist < len(visible_artists):
            current_library = filtered_library if search_query else library
            current_artists_albums = current_library[visible_artists[selected_artist]]
            all_songs_by_artist = flatten_album(current_artists_albums)

            visible_songs = all_songs_by_artist[song_offset : song_offset + max_rows]
            for i, song in enumerate(visible_songs):
                song_split = os.path.basename(song)
                if i == selected_song:
                    songs_win.addstr(i + 1, 2, song_split, curses.A_STANDOUT)
                else:
                    songs_win.addstr(i + 1, 2, song_split)
        else:
            all_songs_by_artist = []
            visible_songs = []

        # Draw search input if active
        draw_search_input(stdscr, search_query, search_active, height - 1, width)
        
        # ---------- NOW PLAYING SECTION ----------
        if curr_song and curr_artist:
            # Clear now playing area
            now_playing_y = height - 6
            progress_y = height - 4

            # Clear the now playing locations
            stdscr.addstr(now_playing_y, PADDING, " " * (width - 2 * PADDING))
            stdscr.addstr(progress_y, PADDING, " " * (width - 2 * PADDING))

            # Choose the correct position based on search state (keep same position for both modes)
            now_playing_y = height - 6
            progress_y = height - 4

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

            # Volume bar: 20 segments, right-aligned
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
            vol_x = width - len(vol_str) - PADDING
            # Truncate now_playing if it would overlap the volume bar
            max_now_playing_len = vol_x - PADDING - 1
            now_playing_disp = now_playing[:max_now_playing_len]
            stdscr.addstr(now_playing_y, PADDING, now_playing_disp, curses.A_BOLD)
            stdscr.addstr(now_playing_y, vol_x, vol_str, curses.A_BOLD)

            # Progress bar with padding
            bar_width = max(1, width - 2 * PADDING)
            progress = int((pos/duration) * bar_width)
            stdscr.addstr(progress_y, PADDING, "█" * progress)
            stdscr.addstr(progress_y, PADDING + progress, "░" * (bar_width - progress))
            time_info = f" {int(pos//60)}:{int(pos%60):02d} / {int(duration//60)}:{int(duration%60):02d} "
            stdscr.addstr(progress_y, int(width/2 - len(time_info)/2), time_info, curses.A_BOLD)

        stdscr.refresh()
        artist_win.refresh()
        songs_win.refresh()
        key = stdscr.getch()

        # ---------- SEARCH INPUT HANDLING ----------
        if search_active:
            if key == 27:  # Escape key
                search_active = False
                search_query = ""
                filtered_library = library
                filtered_artists = list(library.keys())
                selected_artist = 0
                artist_offset = 0
                selected_song = 0
                song_offset = 0
                # Clear the entire screen to prevent double now playing display
                stdscr.clear()
            elif key == curses.KEY_ENTER or key == 10 or key == 13:
                search_active = False  # Exit search mode immediately when Enter is pressed
                if search_query.strip():
                    filtered_library, filtered_artists = search_library(library, search_query.strip())
                    selected_artist = 0
                    artist_offset = 0
                    selected_song = 0
                    song_offset = 0
            elif key == curses.KEY_BACKSPACE or key == 8 or key == 127:
                if search_query:
                    search_query = search_query[:-1]
            elif 32 <= key <= 126:  # Printable ASCII characters
                search_query += chr(key)
            continue  # Skip normal navigation when in search mode

        # ---------- NORMAL MODE KEYS ----------
        if key == ord("/"):
            search_active = True
            continue

        # Clear search filter with 'c' key
        if key == ord("c") and search_query:
            search_query = ""
            filtered_library = library
            filtered_artists = list(library.keys())
            selected_artist = 0
            artist_offset = 0
            selected_song = 0
            song_offset = 0

        # ---------- NAVIGATION ----------
        if key == curses.KEY_UP:
            song_offset = 0
            selected_song = 0
            current_artists = filtered_artists if search_query else artists
            if selected_artist > 0:
                selected_artist -= 1
            elif selected_artist + artist_offset > 0:
                artist_offset -= 1
        elif key == curses.KEY_DOWN:
            song_offset = 0
            selected_song = 0
            current_artists = filtered_artists if search_query else artists
            if selected_artist < min(max_rows - 1, len(current_artists) - 1):
                selected_artist += 1
            elif selected_artist + artist_offset < len(current_artists) - 1:
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
            if visible_songs and selected_song < len(visible_songs):
                curr_song = visible_songs[selected_song]
                curr_artist = visible_artists[selected_artist] if visible_artists and selected_artist < len(visible_artists) else "Unknown Artist"
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
        elif key == ord(","):  # Seek backward 5 seconds
            if curr_song and player:
                current_time = player.get_time()  # in milliseconds
                new_time = max(0, current_time - 5000)  # 5 seconds = 5000ms
                player.set_time(new_time)
        elif key == ord("."):  # Seek forward 5 seconds
            if curr_song and player:
                current_time = player.get_time()  # in milliseconds
                duration = player.get_length()  # in milliseconds
                new_time = min(duration, current_time + 5000)  # 5 seconds = 5000ms
                player.set_time(new_time)
        elif key == ord("<"):  # Seek backward 10 seconds
            if curr_song and player:
                current_time = player.get_time()
                new_time = max(0, current_time - 10000)  # 10 seconds = 10000ms
                player.set_time(new_time)
        elif key == ord(">"):  # Seek forward 10 seconds
            if curr_song and player:
                current_time = player.get_time()
                duration = player.get_length()
                new_time = min(duration, current_time + 10000)  # 10 seconds = 10000ms
                player.set_time(new_time)
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