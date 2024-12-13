# Minecraft Mod Items Fetcher

Script for collecting information about items from Minecraft mods and optionally downloading their images with multi-threaded processing.

## Description

This script collects information about items from specified Minecraft mods by:
1. Reading mod list from mods_data.json or command line arguments
2. Searching for mod items via the Minecraft Wiki API
3. Collecting item details and associated images
4. Saving data to a single JSON file
5. Optionally downloading images to a local directory

## Features

- Multi-threaded processing at three levels:
  - Parallel mod processing
  - Parallel item processing within each mod
  - Parallel image processing for each item
- Configurable number of worker threads
- Automatic rate limiting with configurable delays
- Comprehensive error handling and logging
- Progress tracking and detailed statistics
- Supports both individual mod processing and batch processing
- Automatic file naming and sanitization
- Checks for existing mod data to avoid duplicates

## Requirements

- Python 3.6+
- Required packages:
  - requests
  - concurrent.futures (built-in)
  - logging (built-in)

## Configuration

The script uses the following configurable settings:
- `MAX_WORKERS`: Maximum number of concurrent threads (default: 10)
- `DELAY_BETWEEN_REQUESTS`: Delay between API requests in seconds (default: 1)

## Data Structure

The script generates a JSON file with the following structure:
```json
{
  "mods": [
    {
      "mod_name": "ModName",
      "items": [
        {
          "images": [
            {
              "name": "Item Name",
              "url": "https://...",
              "localPath": "mod_items_data/ItemName_hash.png"
            }
          ]
        }
      ]
    }
  ]
}
```

## Usage

### Basic usage (collect data only):
```bash
python scripts/get_mod_items.py --mods ModName
```

### Process mods from mods_data.json:
```bash
python scripts/get_mod_items.py --from-json
```

### Download images with custom thread count:
```bash
python scripts/get_mod_items.py --from-json --download --workers 15
```

### Process specific mods with image downloading:
```bash
python scripts/get_mod_items.py --mods ModName1 ModName2 --download
```

## Arguments

- `--mods`: List of mod names to process (optional)
- `--from-json`: Read mod list from mods_data.json
- `--download`: Enable image downloading
- `--workers`: Number of worker threads (default: 10)

## Output Files

- `mod_items_data.json`: Main data file containing all mod information
- `mod_items_data/`: Directory containing downloaded images (when using --download)
- `mod_items.log`: Detailed log file with operation information

## Statistics

The script provides detailed statistics after completion:
- Total number of processed mods
- Successfully processed mods
- Failed mod processing attempts
- Processing time and other metrics

## Notes

- Images are only downloaded when using the --download flag
- Existing mod data is skipped to avoid duplicates
- Image filenames are generated using item name and URL hash
- All paths are automatically sanitized for cross-platform compatibility
- The script implements rate limiting to avoid overwhelming the API
