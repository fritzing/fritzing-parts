import os
import os.path
import xml.dom.minidom
import xml.dom
import optparse


def usage():
    print("""
usage:
    listfamilies.py -d [fzp folder] {-p [prefix] }
    lists families and optionally provides a prefix
""")


def main():
    parser = optparse.OptionParser()
    parser.add_option('-d', '--directory', dest="dir")
    parser.add_option('-p', '--prefix', dest="prefix")
    (options, args) = parser.parse_args()

    if not options.dir:
        usage()
        parser.error("dir argument not given")
        return

    names = []
    for root, dirs, files in os.walk(options.dir, topdown=False):
        for filename in files:
            if not filename.endswith(".fzp"):
                continue

            fzpFilename = os.path.join(root, filename)
            try:
                dom = xml.dom.minidom.parse(fzpFilename)
            except xml.parsers.expat.ExpatError as err:
                print(str(err), fzpFilename)
                continue

            fzp = dom.documentElement
            properties = fzp.getElementsByTagName("property")
            for part_property in properties:
                if part_property.getAttribute("name") == 'family':
                    value = getText(part_property.childNodes)
                    if value not in names:
                        names.append(value)

                    if options.prefix:
                        for node in part_property.childNodes:
                            if node.nodeType == node.TEXT_NODE:
                                if options.prefix.lower() not in node.data.lower():
                                    node.data = options.prefix + " " + node.data
                                    outfile = open(fzpFilename, 'wb')
                                    s = dom.toxml("UTF-8")
                                    outfile.write(s)
                                    outfile.close()

                                break
                    break

    names.sort()
    for name in names:
        print(name)


def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


if __name__ == "__main__":
    main()
