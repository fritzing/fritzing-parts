# Part obsoletion script
# TODO: Support obsoleting a part without having a replacement. This could be useful for parts whic are not available anymore.
#

import argparse
import textwrap
import sys
import subprocess
import xml.dom.minidom
import os
import random
import uuid
import re
from copy import deepcopy

simulate = None

# Part of CI tests

def get_dom(filename):
    try:
        dom = xml.dom.minidom.parse(filename)
    except xml.parsers.expat.ExpatError as err:
        print(str(err), filename)
        sys.exit(-1)

    return dom.documentElement


def set_module_id(dom, name):
    newModuleID = '%.8s%s' % (re.sub(r'\s+|_', '', name), uuid.uuid4().hex)
    dom.setAttribute("moduleId", newModuleID)
    return newModuleID


def command(*args):
    global simulate
    print(args, flush=True)
    if not simulate:
        result = subprocess.run(
            args, capture_output=True, text=True
        )
        if result.returncode != 0:
            print("stdout:", result.stdout)
            print("stderr:", result.stderr)
            raise Exception("command error")


def main():
    parser = argparse.ArgumentParser(
        description="Replace a part with a new version of itself.",
        epilog=textwrap.dedent('''
            Run this before editing a part that you want to fix. The script does the following steps.\n 
                    1. move and the part image to the obsolete directory\n
                    2. add a copy of the part and the images with a new name\n
                    3. set a new moduleId for the new part.
                    4. set a replacedby link in the obsoleted part\n
                    5. All changes are already add to git.\n
                    After running the script, you can modify the part, increase the version, fix bugs in the graphics and so on.        
            
            ''')
    )
    parser.add_argument("part", help="The part file that should be replaced.")
    parser.add_argument(
        "name", help="The name of the part. This can be the same as before or a new name")
    parser.add_argument(
        "-s", "--simulate", help="No modifications, just show what would happen.", action='store_true')
    parser.add_argument("-r", "--revision", type=int,
                        help="revision number to use. This is the Fritzing internal revision, not any hardware related revision")

    parser.add_argument(
        "-x", "--hash", help="7 digit number to avoid collisions, like two different \"ArduinoUno_v2\" files.")

    if len(sys.argv) < 3:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    fzpFilename = os.path.normpath(args.part)
    if not fzpFilename.endswith(".fzp"):
        print("File ending should be fzp: %s" % fzpFilename)
        return -1

    if not os.path.basename(os.path.dirname(fzpFilename)) == 'core':
        print("Obsoletion script is currently only tested with core parts")
        return -1

    if not os.path.isfile(fzpFilename):
        print("File not found '%s' " % fzpFilename)
        return -1

    global simulate
    simulate = args.simulate
    commands = []

    if sys.version_info < (3, 8, 0):
        print("Need at least python 3.8. Switching to dry run.")
        simulate = True

    if simulate:
        print("Dry run, no file changes will be written.")

    fzpdir = os.path.dirname(fzpFilename)
    topdir = os.path.dirname(fzpdir)
    obsolete_fzp = os.path.join(
        topdir, 'obsolete', os.path.basename(fzpFilename))

    if re.search(r"/|\.fzp", args.name):
        print("<name> should be a name, not a filename. Got: '%s' " % args.name)
        return -1

    name = args.name
    if args.revision:
        revision = "%03d" % args.revision
    else:
        revision = "%03d" % 2

    if args.hash:
        part_hash = "%07x" % int(args.hash, 0)
    else:
        part_hash = "%07x" % random.randint(1, 268435454)
        
    new_fzp_filename = "_".join([name, part_hash, revision]) + ".fzp"
    new_svg_filename = "_".join([name, part_hash, revision]) + ".svg"

    new_fzp = os.path.join(fzpdir, new_fzp_filename)
    obsolete_fzp_dom = get_dom(fzpFilename)

    if os.path.isfile(obsolete_fzp):
        raise Exception("Error: destination already exists %s " % obsolete_fzp)
    command("git", "mv", fzpFilename, obsolete_fzp)

    new_fzp_dom = deepcopy(obsolete_fzp_dom)

    layers = new_fzp_dom.getElementsByTagName("layers")
    for layer in layers:
        # 1 cp to new name
        image = os.path.normpath(layer.getAttribute("image"))
        # look in ../svg/<subpath>/<image>
        # e.g. ../svg/core/breadboard/imagefile.svg
        path = os.path.join(os.path.dirname(fzpdir), "svg",
                            os.path.basename(fzpdir), image)
        if not os.path.isfile(path):
            print("Warning: %s not found. Ignoring" % path)
            continue

        new_svg = os.path.join(os.path.dirname(path), new_svg_filename)

        command("cp", path, new_svg)

        # 2 mv from core to obsolete
        dest = os.path.join(topdir, "svg", "obsolete", os.path.basename(
            os.path.dirname(path)), os.path.basename(path))
        if os.path.isfile(dest):
            raise Exception("Error: destination already exists %s " % dest)

        command("git", "mv", path, dest)

        command("git", "add", new_svg)

        # 3 set new name in dom
        new_image = os.path.join(os.path.basename(
            os.path.dirname(image)), new_svg_filename)
        print("set layer image to %s" % new_image)
        layer.setAttribute("image", new_image)

    old_module_id = obsolete_fzp_dom.getAttribute("moduleId")
    print("replace moduleId=\"%s\"" % old_module_id)

    new_module_id = set_module_id(new_fzp_dom, name)
    print("with moduleId=\"%s\"" % new_module_id)
    versions = obsolete_fzp_dom.getElementsByTagName("version")
    if not versions:
        doc = obsolete_fzp_dom.ownerDocument
        version = doc.createElement("version")
        version.appendChild(doc.createTextNode("2"))
        obsolete_fzp_dom.appendChild(version)
    else:
        version = versions[0]

    version.setAttribute("replacedby", new_module_id)

    if not simulate:
        print("Write %s" % new_fzp)
        outfile = open(new_fzp, 'wb')
        s = new_fzp_dom.toxml("UTF-8")
        outfile.write(s)
        outfile.close()

        print("Write %s" % obsolete_fzp)
        outfile = open(obsolete_fzp, 'wb')
        s = obsolete_fzp_dom.toxml("UTF-8")
        outfile.write(s)
        outfile.close()

    # s = obsolete_fzp_dom.toxml("UTF-8")
    # print(s)
    command("git", "add", new_fzp)
    command("git", "add", obsolete_fzp)

    return 0


if __name__ == "__main__":
    sys.exit(main())
