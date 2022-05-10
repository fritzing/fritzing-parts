# usage:
# 	    coppersvgparent.py -d [svg folder]
#       looks for files where copper0/copper1 are not parent/child or child/parent


import getopt
import sys
import os
import os.path
import re
import xml.dom.minidom
import xml.dom


def usage():
    print("""
usage:
    coppersvgparent.py -d [svg folder]
    looks for files where copper0/copper1 are not parent/child or child/parent
""")


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:", ["help", "directory"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    dir = None

    for o, a in opts:
        # print o
        # print a
        if o in ("-d", "--directory"):
            dir = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit(2)
        else:
            assert False, "unhandled option"

    if(not(dir)):
        usage()
        sys.exit(2)

    hasErrors = 0
    for root, dirs, files in os.walk(dir, topdown=False):
        for filename in files:
            if not filename.endswith(".svg"):
                continue

            svgFilename = os.path.join(root, filename)
            try:
                dom = xml.dom.minidom.parse(svgFilename)
            except xml.parsers.expat.ExpatError as err:
                print(str(err), svgFilename)
                continue

            svg = dom.documentElement
            gNodes = svg.getElementsByTagName("g")
            copper1 = None
            copper0 = None
            for g in gNodes:
                if g.getAttribute("id") == "copper1":
                    copper1 = g
                if g.getAttribute("id") == "copper0":
                    copper0 = g

            if not copper1:
                continue

            if not copper0:
                continue

            if copper1.parentNode == copper0:
                continue

            if copper0.parentNode == copper1:
                continue

            print("not parents", svgFilename)
            hasErrors += 1

    if (hasErrors > 0):
        sys.exit(127)


if __name__ == "__main__":
    main()
