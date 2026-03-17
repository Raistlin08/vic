from fnmatch import fnmatch


def is_ignored(path):
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