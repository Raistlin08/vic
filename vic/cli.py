import argparse, sys
from vic.commands import cmd_init, cmd_add, cmd_rm, cmd_diff, cmd_commit
from vic.commands import cmd_log, cmd_status, cmd_branch, cmd_checkout, cmd_merge, cmd_gc, cmd_restore

"""
Main functions, handles iteraction through cli
calls all the functions in commands.py
"""
def main():
    
    parser=argparse.ArgumentParser(prog="vic",description='A version controll system')
    sub = parser.add_subparsers(dest='command')
    
    sub.add_parser("init", help='Initialize a new repository') # Init command
    
    p_add=sub.add_parser("add", help='Adds items to index file, ready to be committed') # Add command
    p_add.add_argument("files",nargs="+")
    
    p_rm=sub.add_parser("rm", help='Removes items from index file) and directory, --cached param to only delete from index') # Remove command
    p_rm.add_argument("--cached", action="store_true", default=False)
    p_rm.add_argument("files",nargs="+")
    
    p_diff = sub.add_parser("diff", help="Tells the differences between the file in the index and thee files in the directory") # Diff command
    p_diff.add_argument("files", nargs="*") 
    
    p_commit=sub.add_parser("commit", help="Commit the index file") # Commit command
    p_commit.add_argument("-m","--message", required=True)
    
    sub.add_parser("log", help="Gives you the history of commits for the branch") # Log command
    sub.add_parser("status", help="Tells the status of the files in the directory") # Status command
    
    p_branch = sub.add_parser("branch", help="Manage branches, creates or deletes them with --delete flag") # Branch command
    p_branch.add_argument("branch",nargs="?")
    p_branch.add_argument("-d", "--delete", metavar="BRANCH", default=None)
    
    p_checkout = sub.add_parser("checkout", help="Used to switch between braches") # Checkout command
    p_checkout.add_argument("branch")
    
    p_branch = sub.add_parser("merge", help="Merges current branch with the specified one") # Merge command
    p_branch.add_argument("branch")
    
    sub.add_parser("gc", help="Run this to clear un-referenced files in .vic folder") # Garbage collector command
    
    p_restore = sub.add_parser("restore", help="Restore specified files to their index version")
    p_restore.add_argument("files",nargs="+")
    
    args = parser.parse_args()
    
    match args.command:
        case "init": cmd_init()
        case "add": cmd_add(args.files)
        case "rm": cmd_rm(args.files, args.cached)
        case "diff": cmd_diff(args.files)
        case "commit": cmd_commit(args.message)
        case "log": cmd_log()
        case "status": cmd_status()
        case "branch": cmd_branch(args.branch, args.delete)
        case "checkout": cmd_checkout(args.branch)
        case "merge": cmd_merge(args.branch)
        case "gc": cmd_gc()
        case "restore": cmd_restore(args.files)
        case _:
            parser.print_help()
            sys.exit(1)
            
if __name__ == "__main__":
    main()