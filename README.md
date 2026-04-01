[![Actions Status](https://github.com/fritzing/fritzing-parts/workflows/check-all-parts/badge.svg?branch=master)](https://github.com/fritzing/fritzing-parts/actions)
*master*
[![Actions Status](https://github.com/fritzing/fritzing-parts/workflows/check-all-parts/badge.svg?branch=develop)](https://github.com/fritzing/fritzing-parts/actions)
*develop*


This repository contains all part definitions that are shipped with the [fritzing app](https://github.com/fritzing/fritzing-app). Every fritzing installation contains a clone of this repository and is continuously updated through github, so take great care when making changes.

Parts are composed of meta-data (.fzp) and related graphics (.svg). Read more on the [part folder structure and file format](https://github.com/fritzing/fritzing-app/wiki/2.1-Part-file-format).

## Contributing parts

See the [contribution guidelines](https://github.com/fritzing/fritzing-parts/blob/master/CONTRIBUTING.md) on how to contribute directly to this repository. If this seems too complex, you may alternatively share your part in the [fritzing forum](http://forum.fritzing.org/c/parts-submit).

### Pull Requests

Because a master-pull request results in a parts-update for all fritzing users, there is a develop branch. This branch is for new parts, testing and quality management. Please commit your pull-requests to this branch, so the master branch is clean and ready to use for all fritzing users. The develop branch gets merged from time to time after the QA is done.

## Creating parts

Learn [how to create custom parts](http://fritzing.org/learning/tutorials/creating-custom-parts/)

## Running Quality Checks

The repository includes a checker script to validate FZP and SVG files for common issues. The script can detect errors, provide warnings, and automatically fix many problems.

### Basic Usage

```bash
# Check a single FZP or FZPZ file
python fzp_checker.py path/to/part.fzp
python fzp_checker.py path/to/part.fzpz

# Check all parts in a directory
python fzp_checker.py core/

# Check a specific SVG file
python fzp_checker.py -s path/to/file.svg

# Automatically fix detected errors
python fzp_checker.py path/to/part.fzp --fix
```

### Options

- `-c, --checks`: Specify which checks to run (default: all)
- `-s, --svg`: Check an SVG file or find FZP files using an SVG
- `-f, --file`: Path to a file containing a list of files to check
- `-v, --verbose`: Enable verbose output
- `--fix`: Automatically fix errors when possible

### Examples

```bash
# Check specific types
python fzp_checker.py mypart.fzp -c svg-dimensions svg-units

# Find all FZP files that use a specific SVG
python fzp_checker.py -s myfile.svg contrib/

# View all available checks
python fzp_checker.py --help
```


