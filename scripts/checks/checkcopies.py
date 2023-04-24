import getopt
import sys
import os

def usage():
    print("""
usage:
    checkcopies.py -d <directory> 
    
    <directory> is a folder containing svg files.  
    looks for files that have the same content but different names
    
    Part of CI tests
    """)


def run_fast_scandir(scan_dir, ext):    # scan_dir: str, ext: list
    subfolders, files = [], []

    for f in os.scandir(scan_dir):
        if f.is_dir():
            subfolders.append(f.path)
        if f.is_file():
            if os.path.splitext(f.name)[1].lower() in ext:
                files.append(f.path)

    for d in list(subfolders):
        sf, f = run_fast_scandir(d, ext)
        subfolders.extend(sf)
        files.extend(f)
    return subfolders, files


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hd:", ["help", "directory"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err))  # will print something like "option -a not recognized"
        usage()
        return

    outputDir = None
    gotnot = 0

    for o, a in opts:
        # print o
        # print a
        if o in ("-d", "--directory"):
            outputDir = a
        elif o in ("-h", "--help"):
            usage()
            return
        else:
            assert False, "unhandled option"

    if not outputDir:
        print("missing -d {directory} parameter")
        usage()
        return

    subfolders, files = run_fast_scandir(outputDir, [".svg"])
    print("Checking %d files for duplicates" % len(files))
    files.sort(key=lambda f: os.stat(f).st_size, reverse=True)
    matches = []
    for i in range(0, len(files)-1):
        f1 = files[i]
        s = os.stat(f1).st_size
        # print("Check candidate %s , %d" % (files[i], s))
        j = i + 1
        while s == os.stat(files[j]).st_size:            
            f2 = files[j]
            # print("          other %s , %d" % (files[j], s))
            j += 1
            txt1 = None
            try:
                infile = open(f1, "r")
                txt1 = infile.read()
                infile.close()
            except IOError:
                print("failure", f1)
            if txt1 is None:
                continue

            txt2 = None
            try:
                infile = open(f2, "r")
                txt2 = infile.read()
                infile.close()
            except IOError:
                print("failure", f2)
                continue
            if txt2 is None:
                continue

            if txt1 == txt2:
                matches.append(
                    "<map package='{0}' to='{1}' />".format(f1, f2))

    print("%d duplicate pairs found" % len(matches))


if __name__ == "__main__":
    main()
