# usage:
#    svgNoLayer.py -d <directory>
#
#    <directory> is a folder, with subfolders, containing .svg files.  In each svg file in the directory or its children
#    look for id='[layer]' where layer is the set of all layers in fritzing

import sys
import os
import re
import xml.dom.minidom
import xml.dom
import argparse


def usage():
    print("""
usage:
    svgNoLayer.py -d <directory> [-s <skipfile>] 
    
    <directory> is a folder, with subfolders, containing .svg files.  In each svg file in the directory or its children 
    look for id='[layer]' where layer is the set of all layers in fritzing.
    <skipfile> is a file containing a list of files that should be excluded from the check
    """)


layers = ["icon", "breadboardbreadboard", "breadboard", "breadboardWire", "breadboardLabel", "breadboardNote", "breadboardRuler", "schematic", "schematicWire", "schematicTrace", "schematicLabel", "schematicRuler", "board", "ratsnest",
          "silkscreen", "silkscreenLabel", "groundplane", "copper0", "copper0trace", "groundplane1", "copper1", "copper1trace", "silkscreen0", "silkscreen0Label", "soldermask",  "outline",  "keepout", "partimage", "pcbNote", "pcbRuler"]


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', dest='svgdir',
                        help="svg directory", default='.')
    parser.add_argument('-s', '--skip', dest='skipfile',
                        help="list of files to skip", default='')
    args = parser.parse_args()

    if not args.svgdir:
        usage()
        parser.error("directory argument not given")
        return -1

    outputDir = args.svgdir

    if(not(outputDir)):
        usage()
        sys.exit(2)

    skipFiles = readSkip(args.skipfile)

    count_errors = 0
    count_checks = 0
    count_skips = 0

    for root, dirs, files in os.walk(outputDir, topdown=False):
        for filename in files:
            if (filename.endswith(".svg")):
                # print(filename)
                # print(os.path.normpath(filename))
                if (os.path.normpath(filename) in skipFiles):
                    count_skips += 1
                    continue

                count_checks += 1
                infile = open(os.path.join(root, filename), "r")
                svg = infile.read()
                infile.close()

                msg = parseIDs(svg)
                if msg:
                    print("{0} {1}".format(
                        os.path.join(root, filename), msg))
                    count_errors += 1

    print("%s svg files checked." % count_checks)
    print("%s svg files skipped." % count_skips)
    print("%s svg layer id errors found." % count_errors)

    return count_errors

def parseElement(element):
    for c in element.childNodes:
        if c.nodeType != c.ELEMENT_NODE:
            continue

        tag = c.tagName
        if tag in ["metadata", "title", "desc", "defs", "sodipodi:namedview"]:
            continue

        id = c.getAttribute("id")
        if id in layers:
            continue

        if tag == 'g':
            return parseElement(c)

        return "child element '" + tag + "' with no layer id"

    return None

def parseIDs(svg):
    try:
        dom = xml.dom.minidom.parseString(svg)
    except xml.parsers.expat.ExpatError as err:
        return "xml error " + str(err)

    root = dom.documentElement
    id = root.getAttribute("id")
    if id in layers:
        # Note: This is an error, Fritzing has problems with
        # layer ids in the root element at least until
        # version 0.9.9
        return "svg contains layer id " + id
    return parseElement(root)


def readSkip(skipfile):
    skip_files = []
    if(skipfile):
        infile = open(skipfile, "r")
        skip_files = infile.read().splitlines()
        infile.close()
    for i, item in enumerate(skip_files):
        skip_files[i] = os.path.basename(item)

    return skip_files


if __name__ == "__main__":
    sys.exit(main())
