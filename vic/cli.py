import argparse, sys
from commands import cmd_init, cmd_add, cmd_commit, cmd_log, cmd_status


def main():
    parser=argparse.ArgumentParser(prog="vic",description='A simple version control system.')
    sub= parser.add_subparsers(dest='command')
    
    sub.add_parser("init", help='Initialize a new repository')
    
    p_add=sub.add_parser("add")
    p_add.add_argument("files",nargs="+")
    
    p_commit=sub.add_parser("commit")
    p_commit.add_argument("-m","--message", required=True)
    
    sub.add_parser("log")
    sub.add_parser("status")
    
    args = parser.parse_args()
    
    match args.command:
        case "init": cmd_init()
        case "add": cmd_add(args.files)
        case "commit": cmd_commit(args.message)
        case "log": cmd_log()
        case "status": cmd_status()
        case _:
            parser.print_help()
            sys.exit(1)
            
if __name__ == "__main__":
    main()