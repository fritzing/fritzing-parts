import sys
import re
import argparse

def usage():
    print("""
    Remove 'gorn' attributes which have been inserted by the fritzing parts editor from SVGFILE
    
    """)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', dest='svgfile',
                        help="file to be cleaned up")
    args = parser.parse_args()

    if not args.svgfile:
        usage()
        parser.error("file argument not given")
        return -1

    svgfile = args.svgfile

    if(not(svgfile)):
        usage()
        sys.exit(2)

    text = r"\s*gorn=\"[\.\d]*\"\s*"
    subs = ' '
    replace(svgfile, text, subs, re.MULTILINE)

def replace(file_path, text, subs, flags=0):
    with open(file_path, "r+") as file:
        file_contents = file.read()
        text_pattern = re.compile(text, flags)
        file_contents, count = text_pattern.subn(repl=subs, string= file_contents)
        print(count, "gorns removed")
        file.seek(0)
        file.truncate()
        file.write(file_contents)


if __name__ == "__main__":
    sys.exit(main())
