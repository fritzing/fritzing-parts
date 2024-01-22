# Part obsoletion script
# TODO: Support obsoleting a part without having a replacement. This could
# be useful for parts which are not available anymore.

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

    return dom


def set_module_id(dom, name):
    newModuleID = '%.8s%s' % (re.sub(r'\s+|_', '', name), uuid.uuid4().hex)
    dom.documentElement.setAttribute("moduleId", newModuleID)
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
            Run this before editing a part that you want to fix.\n
            The script does the following steps.\n
                    1. move the fzp to the obsolete directory\n
                    2. copies the current version, or sets version 1 if it\n
                         doesn't exist\n
                    3. copy the original fzp file to a new one.\n
                    4. set a new moduleId for the new part.\n
                    5. set a replacedby link in the obsoleted part\n
                    6. add //obsolete// to the family in the obsoleted part\n
                    7. adds a copy of the svgs with a new name and version + 1\n
                    8. if the part is in bins/core.fzb,\n
                        replaces the old moduleId with the new one.\n
                        replaces the path with the new fzp filename.\n
                    9. All changes are already added to git.\n
                    After running the script, you can modify the part\n
                     fix bugs in the graphics and so on.\n
            ''')
    )
    parser.add_argument("part", help="The part file that should be replaced.")
    parser.add_argument(
        "name", help="The name of the part. This can be the same as before or a new name")
    parser.add_argument(
        "-s", "--simulate", help="No modifications, just show what would happen.", action='store_true')

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

    if sys.version_info < (3, 9, 0):
        print("Need at least python 3.9. Switching to dry run.")
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

    if args.hash:
        part_hash = "%07x" % int(args.hash, 0)
    else:
        part_hash = "%07x" % random.randint(1, 268435454)

    obsolete_fzp_dom = get_dom(fzpFilename)

    # 1. Move the original fzp to the obsolete directory.

    if os.path.isfile(obsolete_fzp):
        raise Exception("Error: destination already exists %s " % obsolete_fzp)
    command("git", "mv", fzpFilename, obsolete_fzp)

    # 2. Set the version to 1 if it doesn't exist then set the new version
    #    to version + 1.

    versions = obsolete_fzp_dom.getElementsByTagName("version")
    if not versions:
        doc = obsolete_fzp_dom.documentElement.ownerDocument
        version = doc.createElement("version")
        version.appendChild(doc.createTextNode("1"))
        before_node = obsolete_fzp_dom.documentElement.childNodes[1]
        obsolete_fzp_dom.documentElement.insertBefore(version, before_node)
        print("Set version to 1 as it didn\'t exist")
        orig_version = 1
    else:
        tag_name = obsolete_fzp_dom.getElementsByTagName("version")[0]
        orig_version = tag_name.firstChild.nodeValue
        if re.search(r"^[0-9]+$", orig_version):
            print("Set orig version to \"%s\"" % orig_version)
        else:
            print("Error: version must be only digits, not %s " % orig_version)
            return -1

    # 3. Copy the original fzp file to a new one.

    new_fzp_dom = deepcopy(obsolete_fzp_dom)

    # 4. Set new moduleId.

    old_module_id = obsolete_fzp_dom.documentElement.getAttribute("moduleId")
    print("replace moduleId=\"%s\"" % old_module_id)

    new_module_id = set_module_id(new_fzp_dom, name)
    print("with moduleId=\"%s\"" % new_module_id)

    # 5. Set version replacedby new_module_id in the obsolete_fzp.

    versions = obsolete_fzp_dom.getElementsByTagName("version")
    version = versions[0]
    version.setAttribute("replacedby", new_module_id)

    new_version = str(int(orig_version) + 1)
    tag_name = new_fzp_dom.getElementsByTagName("version")[0]
    tag_name.firstChild.nodeValue = new_version

    print("set new version to \"%s\"" % new_version)

    # 6. Set //obsolete// in family of obsolete_fzp.

    properties =  obsolete_fzp_dom.getElementsByTagName("property")
    for element in properties:
        if element.getAttribute('name') == "family":
            family = element.firstChild.nodeValue
            family = "//obsolete//" + family
            element.firstChild.nodeValue = family
            print("set obsolete_fzp family to \"%s\"" % family)
            break

    # 7. copy and rename the svg files for the part.

    new_fzp_filename = "_".join([name, part_hash, new_version]) + ".fzp"
    new_svg_filename = "_".join([name, part_hash, new_version])
    new_fzp = os.path.join(fzpdir, new_fzp_filename)

    svgs = {}
    layers = new_fzp_dom.getElementsByTagName("layers")
    for layer in layers:

        image = os.path.normpath(layer.getAttribute("image"))

        print("image \"%s\"" % image)
        # look in ../svg/<subpath>/<image>
        # e.g. ../svg/core/breadboard/imagefile.svg
        path = os.path.join(os.path.dirname(fzpdir), "svg",
                            os.path.basename(fzpdir), image)
        print("path \"%s\"" % path)

        if not os.path.isfile(path):
            if  path in svgs:
                # It is in svgs so replace it in the fzp (the file has already
                # been copied and renamed the first time it was found.)
                print("set dup layer image to %s" % svgs[path])
                layer.setAttribute("image", svgs[path])
            else:
                # Otherwise warn of a problem that needs resolving
                print("Warning: %s not found. Ignoring" % path)
            continue

        # Append the layer to the end of the svg filename so the svg can be
        # moved to a single directory to create a .fzpz file without colliding.

        new_svg = os.path.join(os.path.dirname(path), new_svg_filename +
                               "_" + os.path.dirname(image) + ".svg")

        command("cp", path, new_svg)

        dest = os.path.join(topdir, "svg", "obsolete", os.path.basename(
            os.path.dirname(path)), os.path.basename(path))
        if os.path.isfile(dest):
            raise Exception("Error: destination already exists %s " % dest)

        command("git", "mv", path, dest)

        command("git", "add", new_svg)

        new_image = os.path.join(os.path.basename(
            os.path.dirname(image)), new_svg_filename + "_" +
                            os.path.dirname(image) + ".svg")

        # Save a copy of the new svg path indexed by the original path to deal
        # with duplicate svgs (such as breadboard also being icon!)
        svgs[path] = new_image
        print("set layer image to %s" % new_image)
        layer.setAttribute("image", new_image)

    # 8. update bins/core.fzb if needed.

    bins_file = os.path.join(fzpdir,"../bins/core.fzb")

    if not os.path.isfile(bins_file):
            print("Warning: %s not found. Not updating core.fzb" % bins_file)

    else:

        bins_dom = get_dom(bins_file)

        instances = bins_dom.getElementsByTagName("instance")
        found = False
        for instance in instances:

            if instance.getAttribute("moduleIdRef") == old_module_id:

                instance.setAttribute("moduleIdRef", new_module_id)
                print("replace moduleId=\"%s\"" % old_module_id)
                print("in bins/core.fzb with moduleId=\"%s\"" % new_module_id)
                old_path = instance.getAttribute("path")
                instance.setAttribute("path", new_fzp_filename)
                print("replace path=\"%s\"" % old_path)
                print("in bins/core.fzb with path=\"%s\"" % new_fzp_filename)
                found = True
                break

        if not simulate and found == True:

            print("Write %s" % bins_file)
            outfile = open(bins_file, 'wb')
            s = bins_dom.toxml("UTF-8", False)
            outfile.write(s)
            outfile.close()
            command("git", "add", bins_file)

        elif not found == True:

            print("warning: moduleId=\"%s\"" % old_module_id)
            print("not found in bins/core.fzb, core.fzb not updated.")

    if not simulate:
        print("Write %s" % new_fzp)
        outfile = open(new_fzp, 'wb')
        s = new_fzp_dom.toxml("UTF-8", False)
        outfile.write(s)
        outfile.close()

        print("Write %s" % obsolete_fzp)
        outfile = open(obsolete_fzp, 'wb')
        s = obsolete_fzp_dom.toxml("UTF-8", False)
        outfile.write(s)
        outfile.close()

    # s = obsolete_fzp_dom.toxml("UTF-8")
    # print(s)
    command("git", "add", new_fzp)
    command("git", "add", obsolete_fzp)

    return 0


if __name__ == "__main__":
    sys.exit(main())
