import os
import ctypes
import json
from vic.objects import hash_object, read_object
from vic.utils import is_ignored
import time

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
    try:
        with open(".vic/index", "r") as f:
            indexRaw=f.read()
        index = json.loads(indexRaw)
        
        if index == {}:
            print("There is nothing to commit, use 'vic add filename' to add files to commit")
            return
        
        tree_object = b""
        for file in index:
            tree_object += b"100644 " + file.encode() + b"\0" + bytes.fromhex(index[file])
        
        tree_sha = hash_object(tree_object, "tree")
        
        try:
            with open(".vic/HEAD", "r") as f:
                HEAD=f.read()
        except FileNotFoundError:
            print("Missing HEAD file in .vic")
            return
        
        key, head_path = HEAD.split(" ")
        
        try:
            with open(f".vic/{head_path}") as f:
                parent_sha=f.read()
        except FileNotFoundError:
            parent_sha = None
            
        lines = []
        lines.append(f"tree {tree_sha}")
        if parent_sha:
            lines.append(f"parent {parent_sha}")
        lines.append(f"author Utente <utente@gmail.com> {int(time.time())}")
        lines.append(f"committer Utente <utente@gmail.com> {int(time.time())}")
        lines.append("")
        lines.append(message)
        commit = "\n".join(lines)
        commit = commit.encode()
        commit_sha = hash_object(commit,"commit")
        
        with open(f".vic/{head_path}", "w") as f:
            f.write(commit_sha)
        
        print(f"Commit made at {time.ctime(int(time.time()))}: {message}")
        
            
    except FileNotFoundError:
        print("There is nothing to commit, use 'vic add filename' to add files to commit")


def cmd_log():
    try:
        with open(".vic/HEAD", "r") as f:
            HEAD=f.read()
        
        key, head_path = HEAD.split(" ")
        
        try:
            with open(f".vic/{head_path}") as f:
                sha=f.read()
        except FileNotFoundError:
            sha = None
        
        if sha == "" or sha==None:
                print("No commits were made yet")
                return
        
        while sha !=None:
            
            print(f"commit {sha[:7]}",end="")
            type, content = read_object(sha)
            content = content.decode()
            content = content.split("\n")
            
            sha = None
            author = "unknown"
            committer = "unknown"
            date = "unknown"
            message = False
            
            for row in content:
                if message:
                    message = row
                    break
                key = row.split(" ",1)
                if key[0]=="parent":
                    sha = key[1]
                elif key[0]=="author":
                    tmp = key[1].split(" ")
                    author = tmp[0] + tmp[1]
                elif key[0] == "committer":
                    tmp = key[1].split(" ")
                    committer = tmp[0] + tmp[1]
                    date = time.ctime(int(tmp[2]))
                if row=="":
                    message = True
            
            print(f" made {date}")
            print(f"author {author}")
            print(f"committer {committer}")
            print(f"     {message}")
            print()
        
        
    except FileNotFoundError:
        print("Missing HEAD file in .vic")
        return


def cmd_status():
    #index
    try:
        with open(".vic/index", "r") as f:
            indexRaw=f.read()
        index = json.loads(indexRaw)
    except FileNotFoundError:
        index = {}
    
    # tree
    with open(".vic/HEAD", "r") as f:
            HEAD=f.read()

    key, head_path = HEAD.split(" ")
    
    try:
        with open(f".vic/{head_path}") as f:
            sha=f.read()
    except FileNotFoundError:
        sha = None
    
    if sha == "" or sha==None:
            tree = {}
    else:
        pass
    
    