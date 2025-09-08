import os
from pathlib import Path

def flatten_album(albums):
    return [song for album in albums.values() for song in album]

def scan_music_optimized(path, progress_callback=None, total_files=None, flatten=False):
    """
    Optimized music directory scanner using os.scandir for better performance
    """
    library = {}
    processed = 0
    allowed_extensions = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".webm", ".m4a"}
    
    path = Path(path)
    
    # Use scandir for better performance than listdir
    def has_music_files_fast(directory):
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file() and Path(entry.name).suffix.lower() in allowed_extensions:
                        return True
        except (OSError, IOError):
            pass
        return False
    
    def get_music_files_fast(directory):
        music_files = []
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file() and Path(entry.name).suffix.lower() in allowed_extensions:
                        music_files.append(entry.path)
        except (OSError, IOError):
            pass
        return sorted(music_files)
    
    def get_subdirs_fast(directory):
        subdirs = []
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_dir():
                        subdirs.append(entry.path)
        except (OSError, IOError):
            pass
        return sorted(subdirs)
    
    # Check if this is a flat directory
    if has_music_files_fast(path):
        songs = get_music_files_fast(path)
        
        if songs:
            artist_name = path.name or "Unknown Artist"
            
            if flatten:
                library[artist_name] = songs
            else:
                library[artist_name] = {"All Songs": songs}
        
        if progress_callback:
            progress_callback(1, 1)
        
        return library
    
    # Handle structured directory
    artist_dirs = get_subdirs_fast(path)
    
    # Estimate total work if not provided
    if progress_callback and total_files is None:
        total_files = 0
        for artist_path in artist_dirs:
            if has_music_files_fast(artist_path):
                total_files += 1
            total_files += len(get_subdirs_fast(artist_path))
    
    for artist_path in artist_dirs:
        artist_name = Path(artist_path).name
        albums = {} if not flatten else []
        
        # Check for direct songs in artist folder
        direct_songs = get_music_files_fast(artist_path)
        
        if direct_songs:
            if flatten:
                albums.extend(direct_songs)
            else:
                albums["Singles"] = direct_songs
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total_files or processed)
        
        # Process album subdirectories
        album_dirs = get_subdirs_fast(artist_path)
        
        for album_path in album_dirs:
            album_name = Path(album_path).name
            songs = get_music_files_fast(album_path)
            
            if songs:
                if flatten:
                    albums.extend(songs)
                else:
                    albums[album_name] = songs
            
            processed += 1
            if progress_callback:
                progress_callback(processed, total_files or processed)
        
        if albums:
            library[artist_name] = albums
    
    return library


def scan_music_parallel(path, progress_callback=None, total_files=None, flatten=False):
    """
    Parallel version using concurrent.futures for even better performance on large libraries
    Only use this for very large music collections (10k+ files)
    """
    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    library = {}
    processed = 0
    processed_lock = threading.Lock()
    allowed_extensions = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".webm", ".m4a"}
    
    path = Path(path)
    
    def update_progress():
        nonlocal processed
        with processed_lock:
            processed += 1
            if progress_callback:
                progress_callback(processed, total_files or processed)
    
    def process_album(album_path):
        """Process a single album directory"""
        songs = []
        try:
            with os.scandir(album_path) as entries:
                for entry in entries:
                    if entry.is_file() and Path(entry.name).suffix.lower() in allowed_extensions:
                        songs.append(entry.path)
        except (OSError, IOError):
            pass
        
        update_progress()
        return Path(album_path).name, sorted(songs)
    
    # Check if flat directory
    try:
        with os.scandir(path) as entries:
            has_music = any(entry.is_file() and Path(entry.name).suffix.lower() in allowed_extensions 
                          for entry in entries)
    except (OSError, IOError):
        has_music = False
    
    if has_music:
        # Handle flat directory
        songs = []
        try:
            with os.scandir(path) as entries:
                songs = [entry.path for entry in entries 
                        if entry.is_file() and Path(entry.name).suffix.lower() in allowed_extensions]
        except (OSError, IOError):
            pass
        
        if songs:
            artist_name = path.name or "Unknown Artist"
            if flatten:
                library[artist_name] = sorted(songs)
            else:
                library[artist_name] = {"All Songs": sorted(songs)}
        
        if progress_callback:
            progress_callback(1, 1)
        return library
    
    # Handle structured directory with parallel processing
    artist_dirs = []
    try:
        with os.scandir(path) as entries:
            artist_dirs = [entry.path for entry in entries if entry.is_dir()]
    except (OSError, IOError):
        pass
    
    with ThreadPoolExecutor(max_workers=4) as executor:  # Limit threads to avoid overwhelming filesystem
        for artist_path in sorted(artist_dirs):
            artist_name = Path(artist_path).name
            albums = {} if not flatten else []
            
            # Get direct songs in artist folder
            direct_songs = []
            try:
                with os.scandir(artist_path) as entries:
                    direct_songs = [entry.path for entry in entries 
                                  if entry.is_file() and Path(entry.name).suffix.lower() in allowed_extensions]
            except (OSError, IOError):
                pass
            
            if direct_songs:
                if flatten:
                    albums.extend(sorted(direct_songs))
                else:
                    albums["Singles"] = sorted(direct_songs)
                update_progress()
            
            # Get album directories
            album_dirs = []
            try:
                with os.scandir(artist_path) as entries:
                    album_dirs = [entry.path for entry in entries if entry.is_dir()]
            except (OSError, IOError):
                pass
            
            # Process albums in parallel
            if album_dirs:
                future_to_album = {executor.submit(process_album, album_path): album_path 
                                 for album_path in album_dirs}
                
                for future in future_to_album:
                    album_name, songs = future.result()
                    if songs:
                        if flatten:
                            albums.extend(songs)
                        else:
                            albums[album_name] = songs
            
            if albums:
                library[artist_name] = albums
    
    return library