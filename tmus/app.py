#!/usr/bin/env python3
import curses
import sys
import os
import vlc
import random
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

def create_shuffle_playlist(library):
    """Create a shuffled playlist of all songs"""
    all_songs = []
    for artist, albums in library.items():
        songs = flatten_album(albums)
        for song in songs:
            all_songs.append((song, artist))

    random.shuffle(all_songs)
    return all_songs

def get_artist_for_song(song, library):
    """Find which artist a song belongs to"""
    for artist, albums in library.items():
        songs = flatten_album(albums)
        if song in songs:
            return artist
    return "Unknown Artist"

def create_all_songs_list(library):
    """Create a single list of all songs with their artists"""
    all_songs = []
    for artist, albums in library.items():
        songs = flatten_album(albums)
        for song in songs:
            all_songs.append((song, artist))
    return all_songs

def play_next_song(player, instance, shuffle, shuffle_playlist, current_playlist_index, library, curr_song):
    """Play the next song in shuffle or normal mode"""
    if shuffle and shuffle_playlist:
        # Move to next song in shuffle playlist
        new_index = (current_playlist_index + 1) % len(shuffle_playlist)
        next_song, next_artist = shuffle_playlist[new_index]

        media = instance.media_new(next_song)
        player.set_media(media)
        player.play()

        return next_song, next_artist, new_index

    # Normal mode - could be enhanced to play next song in current artist/album
    return curr_song, get_artist_for_song(curr_song, library) if curr_song else "Unknown Artist", current_playlist_index

def play_previous_song(player, instance, shuffle, shuffle_playlist, current_playlist_index, library, curr_song):
    """Play the previous song in shuffle or normal mode"""
    if shuffle and shuffle_playlist:
        # Move to previous song in shuffle playlist
        new_index = (current_playlist_index - 1) % len(shuffle_playlist)
        prev_song, prev_artist = shuffle_playlist[new_index]

        media = instance.media_new(prev_song)
        player.set_media(media)
        player.play()

        return prev_song, prev_artist, new_index

    # Normal mode - could be enhanced to play previous song in current artist/album
    return curr_song, get_artist_for_song(curr_song, library) if curr_song else "Unknown Artist", current_playlist_index

def draw_search_input(stdscr, query, search_active, height, width):
    """Draw the search input field at the bottom"""
    if search_active:
        search_text = f"Search: {query}"
        search_y = height - 1
        # Clear the search line safely
        max_clear_width = max(0, width - 2 * PADDING)
        if max_clear_width > 0:
            stdscr.addstr(search_y, PADDING, " " * max_clear_width)

        # Truncate search text if too long
        max_search_width = width - 2 * PADDING - 10  # Leave space for cursor and instructions
        if len(search_text) > max_search_width:
            search_text = search_text[:max_search_width-3] + "..."

        # Draw search input with cursor
        if len(search_text) + PADDING < width - 1:
            stdscr.addstr(search_y, PADDING, search_text)
            cursor_x = PADDING + len(search_text)
            if cursor_x < width - 1:
                stdscr.addstr(search_y, cursor_x, "_", curses.A_BLINK)

        # Instructions
        instructions = "[Enter] search [Esc] cancel"
        instr_x = width - len(instructions) - PADDING
        if instr_x > PADDING + len(search_text) + 2 and len(instructions) + PADDING < width:
            stdscr.addstr(search_y, instr_x, instructions, curses.A_DIM)

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
    shuffle = False
    shuffle_playlist = []
    current_playlist_index = 0
    ui_style = 1  # 1 = two-pane view, 2 = single list view
    all_songs_list = []  # For single list view
    selected_all_song = 0
    all_song_offset = 0

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
    all_songs_list = create_all_songs_list(library)

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
            footer = "[q] quit  [p] pause  [+/-] vol  [< / >] seek  [Enter] play  [/] search  [c] clear  [s] shuffle  [n] next  [b] prev  [1/2] view"
            # Truncate footer if too long for the screen
            if len(footer) > width - 2 * PADDING:
                footer = footer[:width - 2 * PADDING - 3] + "..."
            footer_x = max(PADDING, int(width/2 - len(footer)/2))
            stdscr.addstr(height - 2, footer_x, footer, curses.A_BOLD)
        else:
            footer = "[q] quit  [p] pause  [+ / -] vol  [< / >] seek  [Enter] play  [/] search  [s] shuffle  [n] next  [b] prev  [1/2] view"
            # Truncate footer if too long for the screen
            if len(footer) > width - 2 * PADDING:
                footer = footer[:width - 2 * PADDING - 3] + "..."
            footer_x = max(PADDING, int(width/2 - len(footer)/2))
            stdscr.addstr(height - 2, footer_x, footer, curses.A_BOLD)
        
        # ---------- HEADER SECTION ----------
        repeat_text = " [r] repeat: ON " if repeat else " [r] repeat: OFF "
        repeat_color = curses.A_BOLD | (curses.color_pair(1) if repeat and curses.has_colors() else 0)
        stdscr.addstr(2, width - len(repeat_text) - PADDING, repeat_text, repeat_color)

        shuffle_text = " [s] shuffle: ON " if shuffle else " [s] shuffle: OFF "
        shuffle_color = curses.A_BOLD | (curses.color_pair(1) if shuffle and curses.has_colors() else 0)

        ui_style_text = f" [1/2] View: {ui_style} "
        ui_style_color = curses.A_BOLD

        stdscr.addstr(2, width - len(repeat_text) - len(shuffle_text) - len(ui_style_text) - PADDING, ui_style_text, ui_style_color)
        stdscr.addstr(2, width - len(repeat_text) - len(shuffle_text) - PADDING, shuffle_text, shuffle_color)

        if ui_style == 1:
            # Two-pane view
            artist_win.clear()
            songs_win.clear()
            artist_win.box()
            songs_win.box()

            # ---------- ARTISTS SECTION ----------
            current_artists = filtered_artists if search_query else artists
            visible_artists = current_artists[artist_offset:artist_offset + max_rows]

            # Clear all lines first to prevent artifacts when list shrinks
            for i in range(max_rows):
                artist_win.addstr(i + 1, 2, " " * (artist_win_width - 4))

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

                # Clear all lines first to prevent artifacts when list shrinks
                for i in range(max_rows):
                    songs_win.addstr(i + 1, 2, " " * (songs_win_width - 4))

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

        else:
            # Single list view - use full width
            artist_win.clear()
            songs_win.clear()

            # Create single window for all songs
            full_win = curses.newwin(content_height, content_width, 3, PADDING)
            full_win.clear()
            full_win.box()

            # Use filtered list or all songs
            current_all_songs = []
            if search_query:
                # Create filtered all songs list
                for artist, albums in filtered_library.items():
                    songs = flatten_album(albums)
                    for song in songs:
                        current_all_songs.append((song, artist))
            else:
                current_all_songs = all_songs_list

            visible_all_songs = current_all_songs[all_song_offset:all_song_offset + max_rows]

            # Clear all lines first to prevent artifacts when list shrinks
            for i in range(max_rows):
                full_win.addstr(i + 1, 2, " " * (content_width - 4))

            for i, (song, artist) in enumerate(visible_all_songs):
                if i >= max_rows:
                    break
                song_display = f"{os.path.basename(song)} - {artist}"
                # Truncate if too long
                max_song_width = content_width - 4
                if len(song_display) > max_song_width:
                    song_display = song_display[:max_song_width-3] + "..."

                if i == selected_all_song:
                    full_win.addstr(i + 1, 2, song_display, curses.A_STANDOUT)
                else:
                    full_win.addstr(i + 1, 2, song_display)

            full_win.refresh()

            # Set visible_songs for compatibility with existing logic
            visible_songs = [song for song, artist in visible_all_songs]
            all_songs_by_artist = []

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

            # Handle song ending: repeat, shuffle to next, or stop
            if player.get_state() == vlc.State.Ended:
                if repeat:
                    # Repeat current song
                    player.stop()
                    media = instance.media_new(curr_song)
                    player.set_media(media)
                    player.play()
                elif shuffle and shuffle_playlist:
                    # Play next song in shuffle playlist
                    curr_song, curr_artist, current_playlist_index = play_next_song(
                        player, instance, shuffle, shuffle_playlist, current_playlist_index, library, curr_song
                    )

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
        if ui_style == 1:
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
                    selected_all_song = 0
                    all_song_offset = 0
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
            selected_all_song = 0
            all_song_offset = 0

        # Switch UI style with '1' and '2' keys
        if key == ord("1"):
            ui_style = 1
            # Reset selections when switching views
            selected_artist = 0
            artist_offset = 0
            selected_song = 0
            song_offset = 0
        elif key == ord("2"):
            ui_style = 2
            # Reset selections when switching views
            selected_all_song = 0
            all_song_offset = 0

        # ---------- NAVIGATION ----------
        if ui_style == 1:
            # Two-pane navigation
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
                if len(all_songs_by_artist) > 0:
                    if selected_song < min(max_rows - 1, len(all_songs_by_artist) - 1):
                        selected_song += 1
                    elif selected_song + song_offset < len(all_songs_by_artist) - 1:
                        song_offset += 1
        else:
            # Single list navigation
            current_all_songs = []
            if search_query:
                for artist, albums in filtered_library.items():
                    songs = flatten_album(albums)
                    for song in songs:
                        current_all_songs.append((song, artist))
            else:
                current_all_songs = all_songs_list

            if key == curses.KEY_UP:
                if selected_all_song > 0:
                    selected_all_song -= 1
                elif selected_all_song + all_song_offset > 0:
                    all_song_offset -= 1
            elif key == curses.KEY_DOWN:
                if selected_all_song < min(max_rows - 1, len(current_all_songs) - 1):
                    selected_all_song += 1
                elif selected_all_song + all_song_offset < len(current_all_songs) - 1:
                    all_song_offset += 1

        if key == curses.KEY_ENTER or key == 10 or key == 13:
            if ui_style == 1:
                # Two-pane mode song selection
                if visible_songs and selected_song < len(visible_songs):
                    curr_song = visible_songs[selected_song]
                    curr_artist = visible_artists[selected_artist] if visible_artists and selected_artist < len(visible_artists) else "Unknown Artist"
                    media = instance.media_new(curr_song)
                    player.set_media(media)
                    player.play()
                    playing = True

                    # If shuffle mode is on, find this song in the shuffle playlist
                    if shuffle and shuffle_playlist:
                        for i, (song, artist) in enumerate(shuffle_playlist):
                            if song == curr_song:
                                current_playlist_index = i
                                break
            else:
                # Single list mode song selection
                current_all_songs = []
                if search_query:
                    for artist, albums in filtered_library.items():
                        songs = flatten_album(albums)
                        for song in songs:
                            current_all_songs.append((song, artist))
                else:
                    current_all_songs = all_songs_list

                if current_all_songs and selected_all_song < len(current_all_songs):
                    visible_all_songs = current_all_songs[all_song_offset:all_song_offset + max_rows]
                    if selected_all_song < len(visible_all_songs):
                        curr_song, curr_artist = visible_all_songs[selected_all_song]
                        media = instance.media_new(curr_song)
                        player.set_media(media)
                        player.play()
                        playing = True

                        # If shuffle mode is on, find this song in the shuffle playlist
                        if shuffle and shuffle_playlist:
                            for i, (song, artist) in enumerate(shuffle_playlist):
                                if song == curr_song:
                                    current_playlist_index = i
                                    break
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
        elif key == ord("s"):
            shuffle = not shuffle
            if shuffle:
                # Create shuffle playlist when enabling shuffle
                current_library = filtered_library if search_query else library
                shuffle_playlist = create_shuffle_playlist(current_library)
                if curr_song:
                    # Find current song in shuffle playlist and set index
                    for i, (song, artist) in enumerate(shuffle_playlist):
                        if song == curr_song:
                            current_playlist_index = i
                            break
                    else:
                        current_playlist_index = 0
                else:
                    # No current song, start playing a random one
                    if shuffle_playlist:
                        current_playlist_index = 0
                        curr_song, curr_artist = shuffle_playlist[current_playlist_index]
                        media = instance.media_new(curr_song)
                        player.set_media(media)
                        player.play()
                        playing = True
            else:
                shuffle_playlist = []
                current_playlist_index = 0
        elif key == ord("n"):
            # Next song
            if shuffle and shuffle_playlist:
                curr_song, curr_artist, current_playlist_index = play_next_song(
                    player, instance, shuffle, shuffle_playlist, current_playlist_index, library, curr_song
                )
                playing = True
        elif key == ord("b"):
            # Previous song
            if shuffle and shuffle_playlist:
                curr_song, curr_artist, current_playlist_index = play_previous_song(
                    player, instance, shuffle, shuffle_playlist, current_playlist_index, library, curr_song
                )
                playing = True
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