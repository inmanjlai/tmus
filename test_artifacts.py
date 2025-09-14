#!/usr/bin/env python3
import curses
import time

def test_artifacts(stdscr):
    curses.curs_set(0)
    height, width = stdscr.getmaxyx()

    # Create a window
    win = curses.newwin(height-5, width-4, 2, 2)

    # Test data with varying lengths
    test_items = [
        "Short",
        "Medium length text here",
        "This is a very very very long song name that might cause artifacts when replaced with shorter text subaru",
        "Short again",
        "Another medium one",
        "Back to short"
    ]

    current_item = 0

    while True:
        # Clear the window
        win.clear()
        win.box()

        # Display current item
        item = test_items[current_item % len(test_items)]
        win.addstr(1, 2, f"Item {current_item}: {item}")
        win.addstr(3, 2, "Press 'n' for next, 'q' to quit")

        win.refresh()

        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == ord('n'):
            current_item += 1

if __name__ == "__main__":
    curses.wrapper(test_artifacts)