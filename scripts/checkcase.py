
import sys
import os
import os.path
import re
import xml.dom.minidom
import xml.dom
import argparse


def usage():
    print("""
usage:
    checkcase.py -f [fzp folder] -s [svg folder]
    ensure all fzp files case-sensitively match svg file names
    This will modify fzp files
""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fzp', dest='fzpdir',
                        help="fzp directory", default='.')
    parser.add_argument('-s', '--svg', dest='svgdir',
                        help="svg directort", default='svg')
    args = parser.parse_args()

    if not args.fzpdir:
        usage()
        parser.error("fzp dir argument not given")
        return -1

    if not args.svgdir:
        usage()
        parser.error("svg dir argument not given")
        return -1

    ret = 0
    svgdir = args.svgdir
    fzpdir = args.fzpdir
    allsvgs = []
    lowersvgs = {}
    for root, dirs, files in os.walk(svgdir, topdown=False):
        for filename in files:
            if not filename.endswith(".svg"):
                continue
            path = os.path.join(root, filename)
            allsvgs.append(path)
            lowersvgs[path.lower()] = filename

    for root, dirs, files in os.walk(fzpdir, topdown=False):
        for filename in files:
            if not filename.endswith(".fzp"):
                continue

            fzpFilename = os.path.join(root, filename)
            try:
                dom = xml.dom.minidom.parse(fzpFilename)
            except xml.parsers.expat.ExpatError as err:
                print(str(err), fzpFilename)
                continue

            doUpdate = False
            fzp = dom.documentElement
            layerss = fzp.getElementsByTagName("layers")
            for layers in layerss:
                image = os.path.normpath(layers.getAttribute("image"))
                if ("dip_" in image) and ("mil_" in image):
                    continue
                if ("sip_" in image) and ("mil_" in image):
                    continue
                if ("jumper_" in image) and ("mil_" in image):
                    continue
                if ("screw_terminal_" in image):
                    continue
                if ("jumper" in image):
                    continue
                if ("mystery_" in image):
                    continue
                if ("LED-" in image):
                    continue
                if ("axial_lay" in image):
                    continue
                if ("resistor_" in image):
                    continue
                if ("generic" in image) and ("header" in image):
                    continue
                path1 = os.path.join(svgdir, "core", image)
                path2 = os.path.join(svgdir, "contrib", image)
                path3 = os.path.join(svgdir, "obsolete", image)

                if os.path.isfile(path1) or os.path.isfile(path2) or os.path.isfile(path3):
                    for path in [path1, path2, path3]:
                        try:
                            handle = open(path)
                            if not path in allsvgs:
                                print("mismatch", fzpFilename)
                                print("\t", path)
                                print()
                                thing = layers.getAttribute("image").split("/")
                                thing[1] = lowersvgs[path.lower()]
                                layers.setAttribute("image", "/".join(thing))
                                doUpdate = True

                        except:
                            pass
                else:
                    # TODO: Fix missing files in fritzing-parts repo, so we can treat this as error
                    print("Warning: missing", fzpFilename, image)

            if doUpdate:
                outfile = open(fzpFilename, 'wb')
                s = dom.toxml("UTF-8")
                outfile.write(s)
                outfile.close()
                ret = -1
    return ret


if __name__ == "__main__":
    sys.exit(main())
