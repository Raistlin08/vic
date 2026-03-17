from hashlib import sha1
import zlib
import os

def hash_object(data, obj_type):
    header  = f"{obj_type} {len(data)}\0".encode()
    full = header+data
    sha = sha1(full).hexdigest()
    compressed_full =  zlib.compress(full)
    path = f".vic/objects/{sha[:2]}/"
    filename = f"{sha[2:]}"
    os.makedirs(path, exist_ok=True)
    with open(f"{path}{filename}", "wb") as f:
        f.write(compressed_full)
    return sha


def read_object(sha):
    path = f".vic/objects/{sha[:2]}/"
    filename = f"{sha[2:]}"
    try:
        with open(f"{os.path.join(path,filename)}", "rb") as f:
            blob=f.read()
        
        full = zlib.decompress(blob)
        header, content = full.split(b"\0", 1)
        obj_type, size = header.decode().split(" ")
        return (obj_type,content)
    except FileNotFoundError:
        print(f"object {os.path.join(path,filename)} not found")
    