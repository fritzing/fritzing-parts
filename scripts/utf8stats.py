import os
import argparse
import sys
import re
import colorama

# Initialize colorama to allow colored output on all platforms
colorama.init(strip=False)

class Config:
    def __init__(self):
        self.verbose = False

def skip(filename):

    skip_files_string = """
        """
    skip_files = [os.path.normpath(file) for file in skip_files_string.split('\n') if file]
    normalized_filename = os.path.normpath(filename)
    if normalized_filename in skip_files:
        return True

    return False


# Chardet had problems detecting utf-8 chars for omega, male and female symbols.
# import chardet
# def get_encoding_type_chardet(file_path):
#     with open(file_path, 'rb') as f:
#         rawdata = f.read()
#     return chardet.detect(rawdata)


# Charamel has problem with the Ohm symbol
# import charamel
# def get_encoding_type_charamel(file_path):
#     detector = charamel.Detector()
#     with open(file_path, 'rb') as f:
#         rawdata = f.read()
#     # Get the top probable encoding
#     probable_encoding = detector.probe(rawdata, top=50)
#     # Return encoding name and confidence
#     print(probable_encoding)
#     return probable_encoding[0][0].name, probable_encoding[0][1]

from charset_normalizer import detect

def get_encoding_type_charset_normalizer(file_path):
    with open(file_path, 'rb') as f:
        rawdata = f.read()

    result = detect(rawdata)
    # print(result)
    if result['encoding'] is not None:
        # print('got', result['encoding'], 'as detected encoding')
        return result['encoding'], result['confidence']
    else:
        return "unknown", 0

def highlight_non_ascii(file_path):
    with open(file_path, 'r', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if re.search(r'[^\x00-\x7F]', line):
                print(colorama.Fore.GREEN + f'Line {line_num}:' + colorama.Style.RESET_ALL, end='')
                for char in line:
                    if ord(char) > 127:
                        print(colorama.Fore.RED + char + colorama.Style.RESET_ALL, end='')
                    else:
                        print(char, end='')


def check_file(target, file_extension, encoding_statistic, non_utf8_files):
    if target.endswith(file_extension):
        encoding = "skipped"
        if not skip(target):
            encoding, confidence = get_encoding_type_charset_normalizer(target)
        if encoding not in ["utf-8", "ascii", "skipped"]:
            print(f"File: {target}, Encoding: {encoding}, Confidence: {confidence}")
            if confidence < 0.8:
                encoding = encoding + " maybe"
            else:
                non_utf8_files.append(target)
        if encoding not in ['ascii'] and global_config.verbose:
            print(f"File: {target}, Encoding: {encoding}, Confidence: {confidence}")
            highlight_non_ascii(target)

        encoding_statistic[encoding] = encoding_statistic.get(encoding, 0) + 1


def search_directory(target, file_extension, encoding_statistic, non_utf8_files):
    for root, dirs, files in os.walk(target):
        for file in files:
            full_file_path = os.path.join(root, file)
            check_file(full_file_path, file_extension, encoding_statistic, non_utf8_files)


def get_file_statistic(target, file_extension):
    encoding_statistic = {}
    non_utf8_files = []

    if os.path.isfile(target):
        check_file(target, file_extension, encoding_statistic, non_utf8_files)
    elif os.path.isdir(target):
        search_directory(target, file_extension, encoding_statistic, non_utf8_files)

    return encoding_statistic, non_utf8_files


def print_statistic(target):
    print("Statistics for fzp files:")
    fzp_statistic, fzp_non_utf8_files = get_file_statistic(target, ".fzp")
    for encoding, count in fzp_statistic.items():
        print(f"Encoding: {encoding}, Count: {count}")

    print(f"\nNon-UTF8/ASCII fzp files: {len(fzp_non_utf8_files)}")
    for file in fzp_non_utf8_files:
        print(file)

    print("\nStatistics for svg files:")
    svg_statistic, svg_non_utf8_files = get_file_statistic(target, ".svg")
    for encoding, count in svg_statistic.items():
        print(f"Encoding: {encoding}, Count: {count}")

    print(f"\nNon-UTF8/ASCII svg files, Count: {len(svg_non_utf8_files)}")
    for file in svg_non_utf8_files:
        print(file)

    print(f"\nPlease note that ASCII is a subset of UTF-8.")

    return len(fzp_non_utf8_files) + len(svg_non_utf8_files) > 0




global_config = Config()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('target', metavar='target', type=str, help='a directory or filename')
    parser.add_argument('--verbose', action='store_true', help='if set, will print in verbose mode')

    args = parser.parse_args()

    # Store verbose parameter in globally accessible object
    global_config.verbose = args.verbose

    target = args.target

    has_non_utf8_files = print_statistic(target)

    if has_non_utf8_files:
        sys.exit("Error: found files that are not UTF-8 or ASCII encoded.")


if __name__ == "__main__":
    main()