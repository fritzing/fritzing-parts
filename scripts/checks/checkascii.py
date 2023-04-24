import sys
import os
import os.path
import re
import argparse

# Part of CI tests

def main():
    parser = argparse.ArgumentParser(
        description="recursively checks that all filenames in folder are ascii")
    parser.add_argument('folder')
    args = parser.parse_args()

    ret = 0
    for root, dirs, files in os.walk(args.folder, topdown=False):
        for filename in files:
            remainder = re.sub('[ -~]', '', filename)
            if remainder:
                print("not ascii", os.path.join(root, filename))
                ret = -1

    sys.exit(ret)


if __name__ == "__main__":
    main()
