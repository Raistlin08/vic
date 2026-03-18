import argparse, sys
from vic.commands import cmd_init, cmd_add, cmd_rm, cmd_commit, cmd_log, cmd_status

"""
Main functions, handles iteraction through cli
calls all the functions in commands.py
"""
def main():
    
    parser=argparse.ArgumentParser(prog="vic",description='A version controll system')
    sub= parser.add_subparsers(dest='command')
    
    sub.add_parser("init", help='Initialize a new repository')
    
    p_add=sub.add_parser("add")
    p_add.add_argument("files",nargs="+")
    
    p_rm=sub.add_parser("rm")
    p_rm.add_argument("--cached", action="store_true", default=False)
    p_rm.add_argument("files",nargs="+")
    
    p_diff = sub.add_parser("diff")
    p_diff.add_argument("files", nargs="*")
    
    p_commit=sub.add_parser("commit")
    p_commit.add_argument("-m","--message", required=True)
    
    sub.add_parser("log")
    sub.add_parser("status")
    
    args = parser.parse_args()
    
    match args.command:
        case "init": cmd_init()
        case "add": cmd_add(args.files)
        case "rm": cmd_rm(args.files, args.cached)
        case "commit": cmd_commit(args.message)
        case "log": cmd_log()
        case "status": cmd_status()
        case _:
            parser.print_help()
            sys.exit(1)
            
if __name__ == "__main__":
    main()