import os
import ctypes
import json
from vic.objects import hash_object, read_object
from vic.utils import is_ignored

# Creates the repo, makes the directories structure and sets the .vic directory to hidden
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

"""
Receives a list of files and directories,
it navigates the directories to find the files,
for each file uses hash_object and updates the .vic/index
"""
def cmd_add(files):
    
    # Loads the index dictionary
    try:
        with open(".vic/index", "r") as f:
            indexRaw=f.read()
        index = json.loads(indexRaw)
    except FileNotFoundError:
        index = {}
        
    for file in files:
        if os.path.isfile(file):
            if not is_ignored(file): # Check if it is in .vicignore
                with open(file, "rb") as f:
                    content=f.read()
                sha = hash_object(content, "blob")
                if index.get(file) != sha:
                    index[file] = sha
            else:
                print(f"{file} is ignored")
        elif os.path.isdir(file) or file == ".":
            if not is_ignored(file):
                for root, dirs, items in os.walk(file):
                    dirs[:] = [d for d in dirs if not is_ignored(d)] # Check if it is in .vicignore
                    for item in items:
                        path = os.path.join(root,item)
                        if not is_ignored(path): # Check if it is in .vicignore
                            with open(path, "rb") as f:
                                content=f.read()
                            sha = hash_object(content, "blob")
                            if index.get(path) != sha:
                                index[path] = sha
                        else:
                            print(f"{path} is ignored")
                            
                    
            elif os.path.isdir(file):
                print(f"{file} is ignored")
        else:
            print(f"{file} does not exist")

    with open(".vic/index", "w") as f:
        json.dump(index, f)



def cmd_commit(message):
    print("commit")
    print(message)


def cmd_log():
    print("log")


def cmd_status():
    print("status")