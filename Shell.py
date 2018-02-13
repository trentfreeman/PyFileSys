import sys
import os
import fileinput

class Shell:
    """ Simple Python shell """

def repl():
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
        elif words[0] in ('ls', 'dir'):
            arr = os.listdir()
            for item in arr :
                print(item)
        elif words[0] == 'cat':
            arr = os.listdir()
            if words[1] in arr:
                f = open(words[1], 'r')
                print(f.read())
            else:
                print("File not found: " + words[1] + "\nPlease try again.")
        elif words[0] == 'mkdir':
            os.makedirs(words[1])
        elif words[0] == 'touch':
            f = open(words[1], 'w+')
            f.close()
        elif words[0] == 'cd':
            os.chdir("./" + words[1])
        elif words[0] == 'echo':
            print(' '.join(words[1:]))
        elif words[0] == 'pwd':
            print(os.getcwd())
        else:
            print("unknown command {}".format(words[0]))

        sys.stdout.write(prompt)
        sys.stdout.flush()

    # all done, clean exit
    print("Bye!")

assert sys.version_info >= (3,0), "This program requires Python 3"

if __name__ == '__main__':
    repl()
