import os

def cmd_init():
    path = os.getcwd()
    try:
        os.makedirs(".vic", exist_ok=False)
        os.makedirs(".vic/objects",exist_ok=True)
        os.makedirs(".vic/refs",exist_ok=True)
        os.makedirs(".vic/refs/heads",exist_ok=True)
        os.makedirs(".vic/refs/tags",exist_ok=True)
        with open(".vic/HEAD", "a") as f:
            f.write("ref: refs/heads/main")
    except FileExistsError:
        print("La cartella esisteva già!")

    
    print("Empty repository inizialized in " + path)
    

def cmd_add(files):
    print("add")
    print(files)

def cmd_commit(message):
    print("commit")
    print(message)

def cmd_log():
    print("log")

def cmd_status():
    print("status")