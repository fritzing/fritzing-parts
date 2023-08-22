import os
import chardet
import sys

def get_encoding_type(file_path):
    with open(file_path, 'rb') as f:
        rawdata = f.read()
    return chardet.detect(rawdata)['encoding']

def get_file_statistic(target, file_extension):
    encoding_statistic = {}

    if os.path.isfile(target) and target.endswith(file_extension):
        encoding = get_encoding_type(target)
        encoding_statistic[encoding] = encoding_statistic.get(encoding, 0) + 1
    elif os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            for file in files:
                if file.endswith(file_extension):
                    full_file_path = os.path.join(root, file)
                    encoding = get_encoding_type(full_file_path)
                    encoding_statistic[encoding] = encoding_statistic.get(encoding, 0) + 1

    return encoding_statistic

def print_statistic(target):
    print("Statistics for fzp files:")
    fzp_statistic = get_file_statistic(target, ".fzp")
    for encoding, count in fzp_statistic.items():
        print(f"Encoding: {encoding}, Count: {count}")

    print("\nStatistics for svg files:")
    svg_statistic = get_file_statistic(target, ".svg")
    for encoding, count in svg_statistic.items():
        print(f"Encoding: {encoding}, Count: {count}")

    # Many files claim UTF-8 in their header but are reported as ASCII. This is correct.
    print(f"Please note that ASCII is a subset of UTF-8.")

# Get target from command line arguments
if len(sys.argv) > 1:
    target = sys.argv[1]
    print_statistic(target)
else:
    print("Please   provide a directory or filename as a parameter.")