#!/usr/bin/env python3
"""Add part icons to the fritzing-parts database.

This script:
1. Finds all .fzp files in core/ and contrib/ directories
2. Extracts moduleID and icon path from each .fzp file
3. Converts icon SVGs to PNG format (42x42 pixels) using cairosvg
4. Inserts them into the icons table with name format: moduleID_icon

"""

import os
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from multiprocessing import Pool, cpu_count
import io

try:
    import cairosvg
except ImportError:
    print("Error: cairosvg not available. Install with: pip install cairosvg")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: PIL/Pillow not available. Install with: pip install Pillow")
    sys.exit(1)


def svg_to_png_bytes(svg_path, size=42):
    """Convert SVG file to PNG bytes using cairosvg.

    Creates a centered icon on a transparent background with exact dimensions.

    Args:
        svg_path (str): Path to SVG file
        size (int): Output size in pixels (default 42x42)

    Returns:
        bytes: PNG image data, or None if conversion fails
    """
    try:
        # Read SVG file
        with open(svg_path, 'rb') as f:
            svg_data = f.read()

        # Convert SVG to PNG using cairosvg, ensuring it's at least size x size
        # so small SVGs get scaled up rather than leaving a border
        png_data = cairosvg.svg2png(bytestring=svg_data)

        # Open with PIL to check dimensions
        img = Image.open(io.BytesIO(png_data))

        # If the rendered image is smaller than target, re-render at a larger size
        if img.width < size or img.height < size:
            scale = max(size / img.width, size / img.height)
            png_data = cairosvg.svg2png(
                bytestring=svg_data,
                output_width=int(img.width * scale),
                output_height=int(img.height * scale),
            )
            img = Image.open(io.BytesIO(png_data))

        # Convert to RGBA if necessary
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Scale down to fit within size x size while preserving aspect ratio
        img.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Create a new transparent canvas of exact size
        canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))

        # Calculate position to center the image
        offset_x = (size - img.width) // 2
        offset_y = (size - img.height) // 2

        # Paste the resized image onto the canvas
        canvas.paste(img, (offset_x, offset_y), img)

        # Convert to PNG bytes
        output = io.BytesIO()
        canvas.save(output, format='PNG')
        png_bytes = output.getvalue()
        output.close()

        return png_bytes

    except Exception as e:
        print(f"Warning: Failed to convert {svg_path}: {e}")
        return None


def parse_fzp_file(fzp_path):
    """Parse .fzp file to extract moduleID and icon path.

    Args:
        fzp_path (str): Path to .fzp file

    Returns:
        tuple: (moduleID, icon_svg_path) or (None, None) if parsing fails
    """
    try:
        tree = ET.parse(fzp_path)
        root = tree.getroot()

        # Get moduleID from root element
        module_id = root.get('moduleId')
        if not module_id:
            print(f"Warning: No moduleId found in {fzp_path}")
            return None, None

        # Find iconView image path
        icon_view = root.find('.//iconView/layers')
        if icon_view is None:
            print(f"Warning: No iconView found in {fzp_path}")
            return None, None

        icon_image = icon_view.get('image')
        if not icon_image:
            print(f"Warning: No image attribute in iconView for {fzp_path}")
            return None, None

        return module_id, icon_image

    except ET.ParseError as e:
        print(f"Warning: Failed to parse {fzp_path}: {e}")
        return None, None
    except Exception as e:
        print(f"Warning: Error processing {fzp_path}: {e}")
        return None, None


def find_fzp_files_and_extract_info(base_path):
    """Find all .fzp files and extract moduleID and icon paths.

    Args:
        base_path (str): Base path to fritzing-parts repository

    Returns:
        list: List of tuples (moduleID, full_icon_svg_path, fzp_path)
    """
    parts_info = []
    search_paths = [
        ('core', os.path.join(base_path, 'core')),
        ('contrib', os.path.join(base_path, 'contrib')),
    ]

    for part_type, search_path in search_paths:
        if not os.path.exists(search_path):
            print(f"Warning: Path does not exist: {search_path}")
            continue

        for root, dirs, files in os.walk(search_path):
            for filename in files:
                if filename.endswith('.fzp'):
                    fzp_path = os.path.join(root, filename)
                    module_id, icon_rel_path = parse_fzp_file(fzp_path)

                    if module_id and icon_rel_path:
                        # Icon path in .fzp is relative to svg/{core|contrib}/
                        # e.g., "icon/capacitor_tantalum.svg" or "breadboard/part_breadboard.svg"
                        icon_svg_path = os.path.join(base_path, 'svg', part_type, icon_rel_path)

                        if os.path.exists(icon_svg_path):
                            parts_info.append((module_id, icon_svg_path, fzp_path))
                        else:
                            print(f"Warning: Icon file not found: {icon_svg_path} (from {fzp_path})")

    return parts_info


def convert_icon_worker(args):
    """Worker function to convert a single icon (for parallel processing).

    Args:
        args: Tuple of (module_id, icon_svg_path, size)

    Returns:
        tuple: (module_id, png_data, success, error_msg)
    """
    module_id, icon_svg_path, size = args
    png_data = svg_to_png_bytes(icon_svg_path, size)
    if png_data is None:
        return (module_id, None, False, f"Conversion failed for {icon_svg_path}")
    return (module_id, png_data, True, None)


def add_icons_to_database(db_path, parts_info, size=42, dry_run=False, workers=None):
    """Add icons to the database with parallel conversion.

    Args:
        db_path (str): Path to parts.db database
        parts_info (list): List of tuples (moduleID, icon_svg_path, fzp_path)
        size (int): Icon size in pixels (default 42x42)
        dry_run (bool): If True, don't actually insert into database
        workers (int): Number of parallel workers (default: cpu_count)

    Returns:
        dict: Statistics about the operation
    """
    stats = {
        'total': len(parts_info),
        'converted': 0,
        'inserted': 0,
        'skipped': 0,
        'failed': 0
    }

    if dry_run:
        print("DRY RUN MODE - No changes will be made to the database")

    if workers is None:
        workers = cpu_count()

    # Prepare data for parallel conversion
    print(f"Converting {len(parts_info)} icons using {workers} workers...")
    to_convert = [(module_id, icon_svg_path, size) for module_id, icon_svg_path, fzp_path in parts_info]

    # Convert SVGs to PNGs in parallel
    with Pool(workers) as pool:
        results = pool.map(convert_icon_worker, to_convert)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Insert or update converted icons in database
        for module_id, png_data, success, error_msg in results:
            icon_name = f"{module_id}_icon"

            if not success:
                print(f"Warning: {error_msg}")
                stats['failed'] += 1
                continue

            stats['converted'] += 1

            if not dry_run:
                try:
                    # Check if icon exists
                    cursor.execute("SELECT COUNT(*) FROM icons WHERE name = ?", (icon_name,))
                    exists = cursor.fetchone()[0] > 0

                    if exists:
                        # Update existing icon
                        cursor.execute(
                            "UPDATE icons SET data = ? WHERE name = ?",
                            (png_data, icon_name)
                        )
                        print(f"Converted {icon_name} ({len(png_data)} bytes) - will update")
                        stats['skipped'] += 1
                    else:
                        # Insert new icon
                        cursor.execute(
                            "INSERT INTO icons (name, data) VALUES (?, ?)",
                            (icon_name, png_data)
                        )
                        print(f"Converted {icon_name} ({len(png_data)} bytes) - will insert")
                        stats['inserted'] += 1
                except sqlite3.Error as e:
                    print(f"Warning: Failed to save {icon_name}: {e}")
                    stats['failed'] += 1
            else:
                print(f"Would add/update {icon_name} ({len(png_data)} bytes)")
                stats['inserted'] += 1

        if not dry_run:
            print("Committing changes to database...")
            conn.commit()
            print("Database updated successfully!")
        conn.close()

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        sys.exit(1)

    return stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Add part icons to fritzing-parts database'
    )
    parser.add_argument(
        '--db',
        default='parts.db',
        help='Path to parts.db database (default: parts.db)'
    )
    parser.add_argument(
        '--base-path',
        default='.',
        help='Base path to fritzing-parts repository (default: current directory)'
    )
    parser.add_argument(
        '--size',
        type=int,
        default=42,
        help='Icon size in pixels (default: 42)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers for conversion (default: number of CPU cores)'
    )

    args = parser.parse_args()

    # Resolve paths
    db_path = os.path.abspath(args.db)
    base_path = os.path.abspath(args.base_path)

    # Verify database exists
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print(f"Database: {db_path}")
    print(f"Base path: {base_path}")
    print(f"Icon size: {args.size}x{args.size}")
    print()

    # Find .fzp files and extract info
    print("Searching for .fzp files and extracting icon information...")
    parts_info = find_fzp_files_and_extract_info(base_path)
    print(f"Found {len(parts_info)} parts with icons")
    print()

    if len(parts_info) == 0:
        print("No parts with icons found. Exiting.")
        sys.exit(0)

    # Add icons to database
    print("Adding icons to database...")
    stats = add_icons_to_database(db_path, parts_info, args.size, args.dry_run, args.workers)

    # Print statistics
    print()
    print("Summary:")
    print(f"  Total parts found: {stats['total']}")
    print(f"  Successfully converted: {stats['converted']}")
    print(f"  Inserted: {stats['inserted']}")
    print(f"  Updated: {stats['skipped']}")
    print(f"  Failed: {stats['failed']}")


if __name__ == '__main__':
    main()
