import os
import chardet

def get_encoding_type(file_path):
    with open(file_path, 'rb') as f:
        rawdata = f.read()
    return chardet.detect(rawdata)['encoding']

def get_file_statistic(directory, file_extension):
    encoding_statistic = {}

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(file_extension):
                full_file_path = os.path.join(root, file)
                encoding = get_encoding_type(full_file_path)
                encoding_statistic[encoding] = encoding_statistic.get(encoding, 0) + 1

    return encoding_statistic

def print_statistic(directory):
    print("Statistics for fzp files:")
    fzp_statistic = get_file_statistic(directory, ".fzp")
    for encoding, count in fzp_statistic.items():
        print(f"Encoding: {encoding}, Count: {count}")

    print("\nStatistics for svg files:")
    svg_statistic = get_file_statistic(directory, ".svg")
    for encoding, count in svg_statistic.items():
        print(f"Encoding: {encoding}, Count: {count}")

print_statistic("..")