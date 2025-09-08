from setuptools import setup, find_packages
import sys

# Base dependencies
requirements = [
    "python-vlc",
]

# Platform-specific dependencies
if sys.platform.startswith("win"):
    requirements.append("windows-curses")

setup(
    name="tmus",
    version="0.4.0",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "tmus=tmus.app:main",  # tmus command calls tmus/app.py main()
        ],
    },
    python_requires=">=3.8",
)
