#!/usr/bin/env python3
"""
Build script for MeshCore Test Controller
Run on each platform to create native executable

Usage:
    python build.py        # Build for current platform
    python build.py clean  # Clean build artifacts
"""

import os
import platform
import shutil
import subprocess
import sys

APP_NAME = "MeshCore_Test"
MAIN_SCRIPT = "main.py"


def get_platform_info():
    """Get current platform info"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos", ".app"
    elif system == "windows":
        return "windows", ".exe"
    else:
        return "linux", ""


def clean():
    """Clean build artifacts"""
    dirs_to_remove = ["build", "dist", "__pycache__"]
    files_to_remove = [f for f in os.listdir(".") if f.endswith(".spec")]

    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"Removed: {d}")

    for f in files_to_remove:
        os.remove(f)
        print(f"Removed: {f}")

    print("Clean complete!")


def build():
    """Build executable for current platform"""
    plat, ext = get_platform_info()
    print(f"Building for: {plat}")

    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"], check=True
        )

    # Build command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--clean",
        "--hidden-import=tkinter",
        "--collect-all=customtkinter",
    ]

    # Platform-specific options
    if plat == "macos":
        cmd.extend(
            [
                "--osx-bundle-identifier",
                "com.meshcore.testcontroller",
                "--target-architecture",
                "universal2",  # Support both Intel and Silicon
            ]
        )
    elif plat == "windows":
        # Add icon if exists
        if os.path.exists("icon.ico"):
            cmd.extend(["--icon", "icon.ico"])

    cmd.append(MAIN_SCRIPT)

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n✅ Build successful!")
        print(f"Output: dist/{APP_NAME}{ext}")

        # Additional info for macOS
        if plat == "macos":
            print(f"\nTo distribute: zip -r {APP_NAME}.app.zip dist/{APP_NAME}.app")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)


def main():
    # Pre-flight check for tkinter
    try:
        import tkinter
    except ImportError:
        print("\n❌ Error: 'tkinter' module not found!")
        system = platform.system().lower()
        if system == "darwin":
            print("👉 On macOS, please install python-tk:")
            print("   brew install python-tk")
        elif system == "linux":
            print("👉 On Linux, please install python3-tk:")
            print("   sudo apt-get install python3-tk")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean()
    else:
        build()


if __name__ == "__main__":
    main()
