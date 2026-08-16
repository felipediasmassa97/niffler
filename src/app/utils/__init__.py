"""General utils."""

import glob


def get_latest_data_path() -> str:
    """Get the latest data path."""
    files = glob.glob("data/????????.xlsx")
    if not files:
        raise FileNotFoundError("No data files found in 'data/' directory.")
    return max(files)
