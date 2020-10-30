# usage:
#	    invisibleconnectors.py -d [svg folder]
#       looks for connector-like svg elements with no fill or stroke


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
    invisibleconnectors.py -d [svg folder] 
    looks for connector-like svg elements with no fill or stroke
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

            changed = 0
            todo = [dom.documentElement]
            while len(todo) > 0:
                element = todo.pop(0)
                for node in element.childNodes:
                    if node.nodeType == node.ELEMENT_NODE:
                        todo.append(node)
                stroke = element.getAttribute("stroke")
                fill = element.getAttribute("fill")
                strokewidth = element.getAttribute("stroke-width")
                id = element.getAttribute("id")
                if not "connector" in id:
                    continue

                if len(stroke) == 0:
                    style = element.getAttribute("style")
                    if len(style) != 0:
                        style = style.replace(";", ":")
                        styles = style.split(":")
                        for index, name in enumerate(styles):
                            if name == "stroke":
                                stroke = styles[index + 1]
                            elif name == "stroke-width":
                                strokewidth = styles[index + 1]
                            elif name == "fill":
                                fill = styles[index + 1]

                if len(fill) > 0 and fill != "none":
                    continue

                if len(strokewidth) > 0 and strokewidth != "0":
                    continue

                print("invisible connector", svgFilename, id)


if __name__ == "__main__":
    main()
