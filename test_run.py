#!/usr/bin/env python3
import sys
import os

# Add the current directory to the path so we can import tmus
sys.path.insert(0, os.path.dirname(__file__))

try:
    from tmus.app import main
    print("Starting tmus...")
    main()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()