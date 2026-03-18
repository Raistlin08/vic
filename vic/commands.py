import os
import ctypes
import json
from vic.objects import hash_object, read_object
from vic.utils import is_ignored, get_hash
import time
from difflib import unified_diff

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

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
                        path = os.path.normpath(os.path.join(root, item))
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

"""
Receives a list of files and removes them from the index file and the file system
if the cached flag is on it just removes them from the index file
"""
def cmd_rm(files, cached=False):
    try:
        with open(".vic/index", "r") as f:
            index = json.loads(f.read())
    except FileNotFoundError:
        print("No index found")
        return
    
    # Loop over every file
    for file in files:
        path=os.path.normpath(file)
        if path not in index:
            print(f"Item {path} does not exist")
            continue
        else:
            index.pop(path)
            if not cached: # Checks cached flag and deletes he file from the directory
                try:
                    os.remove(path)
                except FileNotFoundError:
                    print(f"{path} already deleted from disk")

            print(f"Item {path} has been deleted")
    with open(".vic/index", "w") as f:
        json.dump(index, f)

"""
Takes as input a list of files and it tells the differences 
between the file saved in index and the file saved in the directory
"""
def cmd_diff(files):
    try:
        with open(".vic/index", "r") as f:
            index = json.loads(f.read())
    except FileNotFoundError:
        print("No index found")
        return
    if not files:
        files=list(index.keys())

    # Loops over every file to confront
    for file in files:
        path = os.path.normpath(file)
        if path not in index:
            print(f"Item {path} isn't in the index file, add it with: vic add {path}")
            continue
        
        # Index file
        key, index_data = read_object(index[path])
        index_data = index_data.decode()
        index_data = index_data.splitlines()
        
        # Directory file
        try:
            with open(f"{os.path.join(path)}", "rb") as f:
                dir_data=f.read()
        except FileNotFoundError:
            print(f"Item {path} isn't in the directory")
            continue
        dir_data = dir_data.decode()
        dir_data=dir_data.splitlines()
        
        # Generate diff
        diff = unified_diff(index_data,dir_data,"index file","dir file",lineterm="")
        
        # Print diff
        print(f"Diff for file {path}")
        for row in diff:
            if row[0]=="+":
                print(f"{GREEN}{row}{RESET}")
            elif row[0]=="-":
                print(f"{RED}{row}{RESET}")
            elif row[0]=="@":
                print(f"{YELLOW}{row}{RESET}")
            else:
                print(row)
        print("")

"""
Takes as input the commit message,
Opens the index file and creates the tree_object, saving the hash
Then opens the HEAD file to find the hash of the previos commit
and creates the commit object, that stores the tree_object sha, 
the parent_commit sha and the message
plus some other QoL data
"""
def cmd_commit(message):
    try:
        with open(".vic/index", "r") as f:
            indexRaw=f.read()
        index = json.loads(indexRaw)
        
        if index == {}:
            print("There is nothing to commit, use 'vic add filename' to add files to commit")
            return
        
        # Creatin tree object
        tree_object = b""
        for file in index:
            tree_object += b"100644 " + file.encode() + b"\0" + bytes.fromhex(index[file])
        
        tree_sha = hash_object(tree_object, "tree")
        
        # Finding parent sha
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
        
        # Creating commit object
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

"""
Walks down the commit chain, and lists the commits with their message
"""
def cmd_log():
    try:
        
        # Finds head commit
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
        
        # Loop until it finds root commit
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
            
            # Parsing of the commit
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

"""
Confronts the sha of the files in the index file
with the ones in the last commit and the ones of the files in the directory
STAGED-the file is present in index but the hash is different from the one in the tree, or in the tree there isn't
UNTRACKED-the file isn't present in the index but is present in the directory
MODIFIED-the file is present in the directory but its hash is different from the one in index
"""
def cmd_status():
    # Creating index dict
    try:
        with open(".vic/index", "r") as f:
            indexRaw=f.read()
        index = json.loads(indexRaw)
    except FileNotFoundError:
        index = {}
    
    # Creating tree dict
    try:
        with open(".vic/HEAD", "r") as f:
                HEAD=f.read()
    except FileNotFoundError:
        print("No previous commits")
        return

    key, head_path = HEAD.split(" ")
    
    try:
        with open(f".vic/{head_path}") as f:
            commit_sha=f.read()
    except FileNotFoundError:
        commit_sha = None
    tree_dict = {}
    if not (commit_sha == "" or commit_sha==None):
        type, commit = read_object(commit_sha)
        tree_to_parse = commit.decode()
        tree_to_parse = tree_to_parse.split("\n",1)[0]
        tree_sha = tree_to_parse.split(" ")[1]

        type, tree = read_object(tree_sha)
        i = 0
        while i < len(tree):
            null = tree.index(b"\0", i)
            header = tree[i:null].decode()
            mode, filename = header.split(" ", 1)
            sha_bytes = tree[null+1:null+21]
            tree_dict[filename] = sha_bytes.hex()
            i = null + 21
    
    # Creating directory dict
    dir_files = {}
    for root, dirs, items in os.walk("."):
            dirs[:] = [d for d in dirs if not is_ignored(d)] # Check if it is in .vicignore
            for item in items:
                path = os.path.normpath(os.path.join(root, item))
                if not is_ignored(path): # Check if it is in .vicignore
                    with open(path,"rb") as f:
                        data = f.read()
                    dir_files[path]=get_hash(data,"blob")
    
    # Confronting the dicts
    for filepath, sha in index.items():
        if filepath not in tree_dict:
            print(f"{GREEN}staged:    {filepath}{RESET}")
        elif tree_dict[filepath] != sha:
            print(f"{GREEN}staged:    {filepath}{RESET}")
    
    for filepath, sha in dir_files.items():
        if filepath not in index:
            print(f"{YELLOW}untracked: {filepath}{RESET}")
        elif sha != index[filepath]:
            print(f"{RED}modified:  {filepath}{RESET}")



"""
Takes name and delete as parameters
Then there are three cases:
1. name and delete are None, lists all branches present in .vic/refs/heads and puts a * in the current one
2. name is set, creates a new branch in .vic/refs/heads with the inserted name, puts the SHA of the last commit
3. delete is set, deletes a branch by deleting the relative file in .vic/refs/heads, you can't delete the current branch
"""
def cmd_branch(name, delete):
    if name==None and delete==None:
        try:
            with open(".vic/HEAD", "r") as f:
                HEAD=f.read()
        except FileNotFoundError:
            print("Missing HEAD file")
            return
        current = HEAD.strip().split("/")[-1]
        for root, dirs, items in os.walk(".vic/refs/heads/"):
            for item in items:
                print(f"{item}",end="")
                if item== current:
                    print(" *")
    elif name and delete:
        print("Error: cannot use both a name and --delete at the same time")
        return
    elif name:
        try:
            with open(".vic/HEAD", "r") as f:
                HEAD=f.read()
        except FileNotFoundError:
            print("Missing HEAD file")
            return
        
        # Commit sha
        key, head_path = HEAD.split(" ")

        try:
            with open(f".vic/{head_path}") as f:
                commit_sha=f.read()
        except FileNotFoundError:
            print("No previous commits")
            
        with open(f".vic/refs/heads/{name}", "w") as f:
            f.write(f"{commit_sha}")
    else:
        try:
            with open(".vic/HEAD", "r") as f:
                HEAD=f.read()
        except FileNotFoundError:
            print("Missing HEAD file")
            return
        current = HEAD.strip().split("/")[-1]
        if current == delete:
            print("Cannot delete current branch, use vic checkout <branch> to switch betweeb branches")
            return
        path = f".vic/refs/heads/{delete}"
        if os.path.exists(path):
            os.remove(path)
            print("Branch deleted")
        else:
            print("Branch doesn't exist")

def cmd_checkout(name):
    path = f".vic/refs/heads/{name}"
    if not os.path.exists(path):    
        print("Branch doesn't exist")

            