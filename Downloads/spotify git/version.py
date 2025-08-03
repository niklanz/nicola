#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version management for Music Hub Pi Controller
"""

import os
import json
from datetime import datetime

# Current version
VERSION = "1.1.0"
BUILD_DATE = "2025-08-03"

def get_version():
    """Get current version string"""
    return VERSION

def get_build_date():
    """Get build date"""
    return BUILD_DATE

def get_build_date_formatted():
    """Get build date in DD/MM/YYYY format"""
    try:
        # Convert from YYYY-MM-DD to DD/MM/YYYY
        date_obj = datetime.strptime(BUILD_DATE, "%Y-%m-%d")
        return date_obj.strftime("%d/%m/%Y")
    except:
        return BUILD_DATE

def get_version_info():
    """Get complete version information"""
    return {
        "version": VERSION,
        "build_date": get_build_date_formatted(),
        "app_name": "Music Hub Pi Controller"
    }

def update_version(new_version=None, auto_increment=True):
    """Update version number
    
    Args:
        new_version (str): Specific version to set
        auto_increment (bool): Auto increment patch version if new_version is None
    """
    global VERSION, BUILD_DATE
    
    if new_version:
        VERSION = new_version
    elif auto_increment:
        # Auto increment patch version (x.y.z -> x.y.z+1)
        parts = VERSION.split('.')
        if len(parts) == 3:
            try:
                patch = int(parts[2]) + 1
                VERSION = f"{parts[0]}.{parts[1]}.{patch}"
            except ValueError:
                # If patch is not a number, just append .1
                VERSION = f"{VERSION}.1"
    
    BUILD_DATE = datetime.now().strftime("%Y-%m-%d")
    
    # Update this file
    update_version_file()

def update_version_file():
    """Update the version.py file with new values"""
    file_path = __file__
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace version and build date
        import re
        content = re.sub(r'VERSION = "[^"]*"', f'VERSION = "{VERSION}"', content)
        content = re.sub(r'BUILD_DATE = "[^"]*"', f'BUILD_DATE = "{BUILD_DATE}"', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Version updated to {VERSION} (build: {BUILD_DATE})")
        
    except Exception as e:
        print(f"Error updating version file: {e}")

def get_git_version():
    """Try to get version from git if available"""
    try:
        import subprocess
        result = subprocess.run(['git', 'describe', '--tags', '--always'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--increment":
            update_version()
        elif sys.argv[1] == "--set" and len(sys.argv) > 2:
            update_version(sys.argv[2], auto_increment=False)
        elif sys.argv[1] == "--info":
            info = get_version_info()
            print(f"App: {info['app_name']}")
            print(f"Version: {info['version']}")
            print(f"Build Date: {info['build_date']}")
            git_version = get_git_version()
            if git_version:
                print(f"Git Version: {git_version}")
    else:
        print(f"Music Hub Pi Controller v{VERSION} (build: {BUILD_DATE})")