from fnmatch import fnmatch
from hashlib import sha1
from vic.objects import read_object


# Checks if a given file or direcotory is to ignore using .vicingore
def is_ignored(path):
    for part in path.replace("\\", "/").split("/"):
                    if fnmatch(part, ".vic"):
                        return True
    try:
        with open(".vicignore", "r") as f:
            for line in f:
                line = line.strip()  # removes newline + spaces
                if not line or line.startswith("#"):
                    continue
                for part in path.replace("\\", "/").split("/"):
                    if fnmatch(part, line):
                        return True

    except FileNotFoundError:
        return False

    return False

# Generate the hash of a given file
def get_hash(data, obj_type):
    header  = f"{obj_type} {len(data)}\0".encode()
    full = header+data
    sha = sha1(full).hexdigest()
    return sha


# Parses the tree from a commit and returns it as a dict
def get_tree(commit_sha):
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
    return tree_dict