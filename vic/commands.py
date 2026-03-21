import os
import ctypes
import json
from vic.objects import hash_object, read_object
from vic.utils import is_ignored, get_hash, get_tree, get_merge_base, get_all_reachable, get_config
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

        # Checking for merge_commit
        merge_commit = None
        try:
            with open(".vic/MERGE_HEAD", "r") as f:
                merge_commit=f.read()
        except FileNotFoundError:
            pass
        
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
        if merge_commit:
            os.remove(".vic/MERGE_HEAD")
            lines.append(f"parent {merge_commit }")
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
        base_sha = sha
        
        # Loop until it finds root commit
        while sha !=None:
            base_sha = sha
            
            type, content = read_object(sha)
            content = content.decode()
            content = content.split("\n")
            
            parent_found = False
            merge_commit = False
            
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
                    if parent_found:
                        merge_commit = True
                    else:
                        parent_found = True
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
                    
            if merge_commit:
                print(f"merge commit {base_sha[:7]}",end="")
            else:
                print(f"commit {base_sha[:7]}",end="")
            
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
    tree_dict = tree_dict = get_tree(commit_sha)
    
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
                    print(" *",end="")
                print("")
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
        
        path = f".vic/refs/heads/{name}"
        if os.path.exists(f".vic/refs/heads/{name}"):
            print(f"Branch {name} already exist, use a different name or use vic branch -d {name} to delete it")
            return
        
        with open(path, "w") as f:
            f.write(f"{commit_sha}")
            
        print(f"{name} has been created, navigate to it using vic checkout {name}")
    else:
        try:
            with open(".vic/HEAD", "r") as f:
                HEAD=f.read()
        except FileNotFoundError:
            print("Missing HEAD file")
            return
        current = HEAD.strip().split("/")[-1]
        if current == delete:
            print("Cannot delete current branch, use vic checkout <branch> to switch between branches")
            return
        path = f".vic/refs/heads/{delete}"
        if os.path.exists(path):
            os.remove(path)
            print("Branch deleted")
        else:
            print("Branch doesn't exist")

def cmd_checkout(name):
    path = f".vic/refs/heads/{name}"
    
    try:
        with open(path, "r") as f:
            commit_sha = f.read()
    except FileNotFoundError:
        print("Branch doesn't exist")
        return
    
    # Current tree
    try:
        with open(".vic/HEAD", "r") as f:
            HEAD=f.read()
    except FileNotFoundError:
        print("Missing HEAD file")
        return
    
    key, head_path = HEAD.split(" ")
    try:
        with open(f".vic/{head_path}") as f:
            current_commit_sha=f.read()
    except FileNotFoundError:
        print("No previous commits")
    
    current_branch = head_path.strip().split("/")[-1]
    if current_branch == name:
        print(f"You are already in the {name} branch")
        return
    
    current_tree_dict = get_tree(current_commit_sha)
    
    # Tree object
    tree_dict = get_tree(commit_sha)
    
    # Deliting current branch files
    for file in current_tree_dict:
        path = os.path.normpath(file)
        try:
            os.remove(path)
        except FileNotFoundError:
            continue
        dirs = path.replace("\\", "/").split("/")
        dirs = dirs[:-1]
        
        for i in range(len(dirs), 0, -1):
            dir_path = os.path.normpath("/".join(dirs[:i]))
            try:
                os.rmdir(dir_path)
            except OSError:
                pass
    
    for file in tree_dict:
        path = os.path.normpath(file)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent,exist_ok=True)
        key, data = read_object(tree_dict[file])
        with open(path,"wb") as f:
            f.write(data)
    

    with open(".vic/index", "w") as f:
        json.dump(tree_dict, f)
        
    with open(".vic/HEAD", "w") as f:
        f.write(f"ref: refs/heads/{name}")

    print(f"Switched to branch '{name}'")



"""
Takes the name of another branch as an input
merges the other branch with the current one by checking which files have been modified in each branch
makes the users resolve conflicts
"""
def cmd_merge(other_branch):
    # Commit
    try:
        with open(".vic/HEAD", "r") as f:
            HEAD=f.read()
    except FileNotFoundError:
        print("Missing HEAD file")
        return
    
    key, head_path = HEAD.split(" ")
    current_branch = head_path.strip().split("/")[-1]
    try:
        with open(f".vic/{head_path}") as f:
            current_commit_sha=f.read()
    except FileNotFoundError:
        print("No previous commits")
        return
        
        
    
    other_head_path = f".vic/refs/heads/{other_branch}"
    try:
        with open(other_head_path) as f:
            other_commit_sha=f.read()
    except FileNotFoundError:
        print("No previous commits")
        return
        
    base_sha = get_merge_base(current_commit_sha,other_commit_sha)

    # tree_dicts
    current_tree_dict = get_tree(current_commit_sha)
    other_tree_dict = get_tree(other_commit_sha)
    base_tree_dict = get_tree(base_sha)
    
    # Fast foward case, the current branch hasn't been modified since the other branch was created
    if base_sha == current_commit_sha:
        commit_sha = other_commit_sha
        
        # Deliting current branch files
        for file in current_tree_dict:
            path = os.path.normpath(file)
            try:
                os.remove(path)
            except FileNotFoundError:
                continue
            dirs = path.replace("\\", "/").split("/")
            dirs = dirs[:-1]
            
            for i in range(len(dirs), 0, -1):
                dir_path = os.path.normpath("/".join(dirs[:i]))
                try:
                    os.rmdir(dir_path)
                except OSError:
                    pass
        # Writing other files
        for file in other_tree_dict:
            path = os.path.normpath(file)
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent,exist_ok=True)
            key, data = read_object(other_tree_dict[file])
            with open(path,"wb") as f:
                f.write(data)
        

        with open(".vic/index", "w") as f:
            json.dump(other_tree_dict, f)
            
        with open(f".vic/{head_path}", "w") as f:
            f.write(other_commit_sha)
        
        print("Fast-Foward")
    else:
        unique_keys = current_tree_dict.keys() | other_tree_dict.keys() | base_tree_dict.keys()
        
        new_index = {}
        conflicts = []
        
        for file in unique_keys:
            current_sha = current_tree_dict.get(file)
            other_sha = other_tree_dict.get(file)
            base_sha = base_tree_dict.get(file)
            
            if current_sha == other_sha and current_sha != None: # File hasn't been modified in neither branches
                new_index[file] = other_sha 
            elif current_sha == base_sha: # Modified or deleted in other branch
                if other_sha != None:
                    new_index[file] = other_sha
            elif other_sha == base_sha: # Modified or deleted in current branch
                if current_tree_dict[file] != None:
                    new_index[file] = current_tree_dict[file]
            else: # Conflict
                conflicts.append(file)
                new_index[file] = current_sha   
            
            
        # Deleting current files
        for file in current_tree_dict:
            path = os.path.normpath(file)
            try:
                os.remove(path)
            except FileNotFoundError:
                continue
            dirs = path.replace("\\", "/").split("/")
            dirs = dirs[:-1]
            
            for i in range(len(dirs), 0, -1):
                dir_path = os.path.normpath("/".join(dirs[:i]))
                try:
                    os.rmdir(dir_path)
                except OSError:
                    pass
        
        # Writing files
        for file in new_index:
            if file not in conflicts:
                path = os.path.normpath(file)
                parent = os.path.dirname(path)
                if parent:
                    os.makedirs(parent,exist_ok=True)
                key, data = read_object(new_index[file])
                with open(path,"wb") as f:
                    f.write(data)
            else:
                path = os.path.normpath(file)
                parent = os.path.dirname(path)
                if parent:
                    os.makedirs(parent,exist_ok=True)
                key, current_data = read_object(current_tree_dict.get(file))
                key, other_data = read_object(other_tree_dict.get(file))
                conflict_file_data = "<<<<<<<<< CURRENT BRANCH\n"
                conflict_file_data += current_data.decode()
                conflict_file_data += "\n========================================================================\n"
                conflict_file_data += other_data.decode()
                conflict_file_data += "\n>>>>>>>>> OTHER BRANCH"
                with open(path,"w") as f:
                    f.write(conflict_file_data)
            
        with open(".vic/index", "w") as f:
            json.dump(new_index, f)
            
        if conflicts == []:
            # Creating tree object
            tree_object = b""
            for file in new_index:
                tree_object += b"100644 " + file.encode() + b"\0" + bytes.fromhex(new_index[file])
            
            tree_sha = hash_object(tree_object, "tree")
            
            message = f"Merge commit between {current_branch} and {other_branch}"
            
            # Creating commit object
            lines = []
            lines.append(f"tree {tree_sha}")
            lines.append(f"parent {current_commit_sha}")
            lines.append(f"parent {other_commit_sha}")
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
            
        else:
            with open(".vic/MERGE_HEAD", "w") as f:
                f.write(other_commit_sha)
            
            for file in conflicts:
                print(f"CONFLICT: {file}")
            
            print("Fix all conflicts and run vic add ., and vic commit")
            

"""
Garbage collector function
iterates over all branches and commits to find all referenced objects
and then deletes from the file system the one that aren't referenced
"""
def cmd_gc():
    
    #get reachables
    reachable = set()
    for root, dirs, items in os.walk(".vic/refs/heads/"):
        for item in items:
            path = os.path.join(root, item)
            with open(path, "r") as f:
                reachable=reachable | get_all_reachable(f.read())
    
    count = 0
    # Walk objects directory
    for root, dirs, items in os.walk(".vic/objects/"):
        for item in items:
            folder_part = os.path.join(root,item).replace("\\", "/").split("/")[-2]
            file_part = item
            sha = folder_part+file_part
            if sha not in reachable:
                try:
                    os.remove(os.path.join(root, item))
                    count+=1
                except FileNotFoundError:
                    continue
                try:
                    os.rmdir(root)
                except OSError:
                    pass
    
    print(f"Removed {count} unreachable objects")
    
"""    
Takes as input a list of files and restores each one of teh to the index saved version
"""    
def cmd_restore(files):
    try:
        with open(".vic/index", "r") as f:
            indexRaw=f.read()
        index = json.loads(indexRaw)
    except FileNotFoundError:
        index = {}
    for file in files:
        path = os.path.normpath(file)
        if path not in index.keys():
            print(f"File {path} isn't in index")
        else:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            key, blob = read_object(index[path])
            with open(path,"wb") as f:
                f.write(blob)
            print(f"{path} has been restored")
            

"""
Takes as input either:
nothing -> prints current config
name and/or email -> saves new configuration to .vic/config
"""
def cmd_config(name, email):
    config = get_config()
    modified = False
    if name:
        config["name"] = name
        print("Name set")
        modified = True
    if email:
        config["email"] = email
        print("Email set")
        modified = True
    
    if modified:
        with open(".vic/config", "w")as f:
            json.dump(config,f)
    else:
        print(f"Name: {config["name"]}")
        print(f"Email: {config["email"]}")
