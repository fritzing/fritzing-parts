#!/usr/bin/env python3

import argparse
import subprocess
import os
import sys

def get_modified_fzps(directory):
    """Get list of modified .fzp files in the given directory"""
    try:
        # Run git status to get modified files
        result = subprocess.run(
            ['git', 'status', '--porcelain', directory],
            capture_output=True,
            text=True,
            check=True
        )

        modified_files = []
        for line in result.stdout.splitlines():
            # Check if file is modified (M) and ends with .fzp
            if line.startswith(' M') or line.startswith('M '):
                filepath = line[3:].strip()
                if filepath.endswith('.fzp'):
                    modified_files.append(filepath)

        return modified_files

    except subprocess.CalledProcessError as e:
        print(f"Error running git status: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Find modified .fzp files and obsolete them"
    )
    parser.add_argument("directory", help="Directory to search for modified .fzp files")
    parser.add_argument("-s", "--simulate", action="store_true", 
                        help="Dry run - show what would be done without making changes")

    args = parser.parse_args()

    # Get list of modified .fzp files
    modified_fzps = get_modified_fzps(args.directory)

    if not modified_fzps:
        print("No modified .fzp files found")
        return 0

    print(f"Found {len(modified_fzps)} modified .fzp files:")
    for fzp in modified_fzps:
        print(f"- {fzp}")

    # Call obsolete.py for each modified file
    for fzp in modified_fzps:
        print(f"\nProcessing {fzp}...")

        cmd = [
            'python3',
            'scripts/obsolete.py',
            fzp,
            '--keep-svgs',
            '--fzp-already-modified'
        ]

        if args.simulate:
            cmd.append('--simulate')

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error processing {fzp}: {e}")
            continue

    return 0

if __name__ == "__main__":
    sys.exit(main())
