import sys
import os
import fileinput
from FileSystem import *

class Shell:
    """ Simple Python shell """


def repl():
    fs = None
    fsExists = False
    prompt = '> '
    cmd = ''
    sys.stdout.write(prompt)
    sys.stdout.flush()
    for line in sys.stdin:
        words = line.split()
        if len(words) == 0:
            pass
        elif words[0] in ('exit', 'quit'):
            print("Bye!")
            quit()
        elif words[0] == 'newfs':
            if len(words) < 3 and len(words) > 4:
                print('Number of arguments to the command incorrect. please use the following: newfs <filename> <block_count> [optional block size]')
            elif len(words) == 3:
                if tryAsNum(words[2]):
                    FileSystem.createFileSystem(words[1], int(words[2]))
            elif len(words) == 4:
                if tryAsNum(words[2]) and tryAsNum(words[3]):
                    FileSystem.createFileSystem(words[1], int(words[2]), int(words[3]))
            else:
                print('There were too many arguments. Please try again')
        elif words[0] == 'mount':
            if len(words) != 2:
                print('Number of arguments to the command incorrect. please use the following: mount <filename>')
            elif fsExists == True:
                print("file system already mounted. Cannot mount another one")
            else:
                fs = FileSystem(words[1])
                try:
                    fs
                except NameError:
                    fsExists = False
                else:
                    fsExists = True
######## EVERYTHING PAST THIS LINE MUST CHECK FOR FS ####
        elif words[0] == 'blockmap' and fsExists:
            if len(words) != 1:
                print('Number of arguments to the command incorrect. please use the following: blockmap')
            else:
                fs.getBlockMap()
        elif words[0] == 'alloc_block' and fsExists:
            if len(words) != 1:
                print('Number of arguments to the command incorrect. please use the following: alloc_block')
            else:
                fs.alloc_Block()
        elif words[0] == 'free_block' and fsExists:
            if len(words) != 2:
                print('Number of arguments to the command incorrect. please use the following: free_block <n>')
            else:
                if tryAsNum(words[1]):
                    fs.free_Block(int(words[1]))
        elif words[0] == 'inode_map'  and fsExists:
            if len(words) != 1:
                print('Number of arguments to the command incorrect. please use the following: inode_map')
            else:
                fs.getInodeMap()
        elif words[0] == 'alloc_inode' and fsExists:
            if len(words) != 2:
                print('Number of arguments to the command incorrect. please use the following: alloc_inode <type>\n Types are: 0 = free, f = file, d = Dir, s = symLink, b = block pointer, D = Data')
            else:
                fs.alloc_INode(words[1])
        elif words[0] == 'free_inode' and fsExists:
            if len(words) != 2:
                print('Number of arguments to the command incorrect. please use the following: free_inode <number>')
            else:
                if tryAsNum(words[1]):
                    fs.free_INode(int(words[1]))
        elif words[0] == 'unmount' and fsExists:
            if len(words) != 1:
                print('Number of arguments to the command incorrect. please use the following: unmount')
            else:
                fs.unmount
                fsExists = False
                del fs
        else:
            print("unknown command {}".format(words[0]))

        sys.stdout.write(prompt)
        sys.stdout.flush()

    # all done, clean exit
    print("Bye!")


###### helper functions ###########################
def tryAsNum(num):
    try:
        int(num)
    except ValueError:
        print('Cannot interpret that as a number, please try again')
        return False
    else:
        return True


assert sys.version_info >= (3,0), "This program requires Python 3"

if __name__ == '__main__':
    repl()
