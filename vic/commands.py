import os
import ctypes
import json
import vic.objects
from vic.utils import is_ignored

def cmd_init():
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        path = os.getcwd()
        folder=".vic"
        os.makedirs(folder, exist_ok=False)
        os.makedirs(".vic/objects",exist_ok=True)
        os.makedirs(".vic/refs",exist_ok=True)
        os.makedirs(".vic/refs/heads",exist_ok=True)
        os.makedirs(".vic/refs/tags",exist_ok=True)
        with open(".vic/HEAD", "w") as f:
            f.write("ref: refs/heads/main")
        ctypes.windll.kernel32.SetFileAttributesW(folder, FILE_ATTRIBUTE_HIDDEN)
        print("Empty repository inizialized in " + path)
    except FileExistsError:
        print("Repo già presente")

    
    
    

def cmd_add(files):
    for file in files:
        if os.path.isfile(file):
            if not is_ignored(file):
                pass
            else:
                print(f"{file} is ignored")
        elif os.path.isdir(file) or file == ".":
            if not is_ignored(file):
                pass
            else:
                print(f"{file} is ignored")
        else:
            print(f"{file} does not exist")

def cmd_commit(message):
    print("commit")
    print(message)

def cmd_log():
    print("log")

def cmd_status():
    print("status")