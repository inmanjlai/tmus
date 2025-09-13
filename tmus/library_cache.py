import os
import json
import time
from pathlib import Path

def get_cache_path(music_dir):
    cache_name = f"library_cache_{os.path.basename(os.path.abspath(music_dir))}.json"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), cache_name)

def get_directory_mtime(music_dir):
    """Get the most recent modification time in the music directory"""
    latest_mtime = 0
    try:
        # Check if directory exists first
        if not os.path.exists(music_dir):
            return 0  # Return 0 if directory doesn't exist

        # Check the root directory
        latest_mtime = max(latest_mtime, os.path.getmtime(music_dir))

        # Walk through subdirectories (but don't open files)
        for root, dirs, files in os.walk(music_dir):
            try:
                # Check directory modification time
                latest_mtime = max(latest_mtime, os.path.getmtime(root))

                # Optional: check file modification times (slower but more accurate)
                # for file in files:
                #     if file.lower().endswith(('.mp3', '.flac', '.wav', '.m4a', '.ogg', '.aac')):
                #         file_path = os.path.join(root, file)
                #         latest_mtime = max(latest_mtime, os.path.getmtime(file_path))

            except (OSError, IOError):
                continue  # Skip files we can't access

    except (OSError, IOError):
        return 0  # Return 0 if we can't check (directory likely doesn't exist)

    return latest_mtime

def load_library_cache(music_dir):
    cache_path = get_cache_path(music_dir)
    if not os.path.exists(cache_path):
        return None

    # Check if music directory exists first
    if not os.path.exists(music_dir):
        print("Music directory doesn't exist, invalidating cache...")
        try:
            os.remove(cache_path)  # Remove stale cache
        except OSError:
            pass
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Check if cache has required metadata
        if not isinstance(cache_data, dict) or 'timestamp' not in cache_data or 'library' not in cache_data:
            return None

        # Check if music directory has been modified since cache was created
        cache_timestamp = cache_data['timestamp']
        current_mtime = get_directory_mtime(music_dir)

        if current_mtime > cache_timestamp:
            print("Music directory modified since cache created, rescanning...")
            return None

        return cache_data['library']

    except (json.JSONDecodeError, OSError, IOError):
        return None

def save_library_cache(music_dir, library):
    cache_path = get_cache_path(music_dir)
    try:
        cache_data = {
            'timestamp': get_directory_mtime(music_dir),
            'library': library
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except (OSError, IOError) as e:
        print(f"Warning: Could not save cache: {e}")

def quick_file_count(music_dir):
    """Fast file counting using os.scandir (faster than os.walk)"""
    count = 0
    allowed_extensions = {'.mp3', '.flac', '.wav', '.m4a', '.ogg', '.aac'}
    
    try:
        with os.scandir(music_dir) as entries:
            for entry in entries:
                if entry.is_file() and Path(entry.name).suffix.lower() in allowed_extensions:
                    count += 1
                elif entry.is_dir():
                    # Recursively count in subdirectories
                    count += quick_file_count(entry.path)
    except (OSError, IOError):
        pass
    
    return count

def update_library_cache(music_dir, scan_func, progress_callback=None):
    # Try to load cached data first
    cached = load_library_cache(music_dir)
    
    if cached is not None:
        print("Using cached library data")
        if progress_callback:
            # Smoothly animate progress from 0 → 100 for cached data
            total_steps = 10
            for i in range(1, total_steps + 1):
                progress_callback(i, total_steps)
                time.sleep(0.03)  # small delay to make it visible but fast
        return cached
    
    print("Cache miss or expired, scanning music directory...")
    
    # Cache miss - need to scan
    if progress_callback:
        # Quick file count for progress tracking
        total_files = quick_file_count(music_dir)
        progress_callback(0, total_files)
        library = scan_func(music_dir, progress_callback, total_files)
    else:
        library = scan_func(music_dir)
    
    # Save the new scan results
    save_library_cache(music_dir, library)
    return library

# Alternative: Even faster cache check using just directory timestamps
def update_library_cache_fast(music_dir, scan_func, progress_callback=None):
    """
    Faster cache implementation that only checks directory modification times
    This is less accurate but much faster for large libraries
    """
    cache_path = get_cache_path(music_dir)
    
    # Quick timestamp check
    if os.path.exists(cache_path):
        try:
            cache_stat = os.path.getmtime(cache_path)
            music_stat = os.path.getmtime(music_dir)
            
            # If cache is newer than the music directory, use it
            if cache_stat > music_stat:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                if isinstance(cache_data, dict) and 'library' in cache_data:
                    print("Using cached library data (fast check)")
                    if progress_callback:
                        progress_callback(1, 1)
                    return cache_data['library']
        except (OSError, IOError, json.JSONDecodeError):
            pass
    
    # Need to scan
    print("Cache miss, scanning music directory...")
    if progress_callback:
        total_files = quick_file_count(music_dir)
        progress_callback(0, total_files)
        library = scan_func(music_dir, progress_callback, total_files)
    else:
        library = scan_func(music_dir)
    
    save_library_cache(music_dir, library)
    return library