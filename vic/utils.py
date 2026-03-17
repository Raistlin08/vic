from fnmatch import fnmatch
from hashlib import sha1


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

def hash(data, obj_type):
    header  = f"{obj_type} {len(data)}\0".encode()
    full = header+data
    sha = sha1(full).hexdigest()
    return sha