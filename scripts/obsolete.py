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


def get_xml_declaration(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if first_line.startswith('<?xml') and first_line.endswith('?>'):
            return first_line + '\n'
    return '<?xml version="1.0" encoding="UTF-8"?>\n'  # fallback default


def main():
    parser = argparse.ArgumentParser(
        description="Replace a part with a new version of itself.",
        epilog=textwrap.dedent('''
            Run this before editing a part that you want to fix. The script does the following steps:

            1. move the part image to the obsolete directory
            2. add a copy of the part and the images with a new name
            3. set a new moduleId for the new part
            4. set a replacedby link in the obsoleted part
            5. All changes are already added to git

            After running the script, you can modify the part, increase the version, fix bugs in the graphics and so on.        

            Examples:
                1. Basic usage with automatic name generation:
                   python3 scripts/obsolete.py core/RFM23BP.fzp

                2. Specify a custom name and revision:
                   python3 scripts/obsolete.py core/Arduino_Uno.fzp ArduinoUno_Rev3 -r 3

                3. Process an already modified fzp and keep existing SVGs:
                   python3 scripts/obsolete.py core/RFM23BP.fzp --keep-svgs --fzp-already-modified
                   (Use when you've already updated the fzp and want to preserve existing SVG files)
            '''),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("part", help="The part file that should be replaced.")
    parser.add_argument(
        "name", nargs='?', help="The base name for the new part files. If omitted, the name will be derived from the part filename.")
    parser.add_argument(
        "-s", "--simulate", help="No modifications, just show what would happen.", action='store_true')
    parser.add_argument("-r", "--revision", type=int,
                        help="revision number to use. This is the Fritzing internal revision, not any hardware related revision")

    parser.add_argument(
        "-x", "--hash", help="7 digit number to avoid collisions, like two different \"ArduinoUno_v2\" files.")
    parser.add_argument("--keep-svgs", action="store_true", help="Don't move or copy SVGs to new locations. Only the fzp is obsoleted.")
    parser.add_argument("--fzp-already-modified", action="store_true",
                        help="Use when you've already updated the input fzp file. Without this flag, you should run this script "
                             "on the original fzp file before making changes. With this flag, the script will use git to recover "
                             "the original version for the obsolete copy while preserving your modifications as the new version. "
                             "Requires git to be installed.")

    if len(sys.argv) < 2:
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

    if args.name:
        name = args.name
    else:
        # Extract the name from the fzpFilename
        name = os.path.splitext(os.path.basename(fzpFilename))[0]
        print(f"Name parameter not provided. Deriving name from the part filename: {name}")

    if re.search(r"/|\.fzp", name):
        print("<name> should be a name, not a filename. Got: '%s' " % name)
        return -1

    if args.revision:
        revision = "%03d" % args.revision
    else:
        revision = "%03d" % 2

    if args.hash:
        part_hash = "%07x" % int(args.hash, 0)
    else:
        part_hash = "%07x" % random.randint(1, 268435454)

    if args.fzp_already_modified:
        temp_modified = fzpFilename + ".modified"
        command("mv", fzpFilename, temp_modified)
        # Restore the original version
        command("git", "checkout", "HEAD", fzpFilename)

    new_fzp_filename = "_".join([name, part_hash, revision]) + ".fzp"

    new_fzp = os.path.join(fzpdir, new_fzp_filename)
    obsolete_fzp_dom = get_dom(fzpFilename)

    xml_decl = get_xml_declaration(fzpFilename)

    if os.path.isfile(obsolete_fzp):
        raise Exception("Error: destination already exists %s " % obsolete_fzp)
    command("git", "mv", fzpFilename, obsolete_fzp)

    if args.fzp_already_modified:
        # Instead of copying from obsolete, use our saved modified version
        command("mv", temp_modified, new_fzp)
        new_fzp_dom = get_dom(new_fzp)
    else:
        new_fzp_dom = deepcopy(obsolete_fzp_dom)

    if not args.keep_svgs:
        new_svg_filename = "_".join([name, part_hash, revision]) + ".svg"
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
        with open(new_fzp, 'wb') as outfile:
            outfile.write(xml_decl.encode('utf-8'))
            s = new_fzp_dom.toxml("UTF-8")
            outfile.write(s)

        print("Write %s" % obsolete_fzp)
        with open(obsolete_fzp, 'wb') as outfile:
            outfile.write(xml_decl.encode('utf-8'))
            s = obsolete_fzp_dom.toxml("UTF-8")
            outfile.write(s)

    # s = obsolete_fzp_dom.toxml("UTF-8")
    # print(s)
    command("git", "add", new_fzp)
    command("git", "add", obsolete_fzp)

    return 0


if __name__ == "__main__":
    sys.exit(main())
