import os
import json
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths
CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources.json")
RAW_DATA_PATH = os.path.join(BASE_DIR, "data", "bronze")

os.makedirs(RAW_DATA_PATH, exist_ok=True)


def load_sources():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def download_file(name, url):
    logging.info(f"Downloading {name} data...")
    response = requests.get(url)

    if response.status_code == 200:
        file_path = os.path.join(RAW_DATA_PATH, f"{name}.csv")
        with open(file_path, "wb") as f:
            f.write(response.content)
        logging.info(f"{name} saved successfully.")
    else:
        logging.error(f"Failed to download {name}. Status code: {response.status_code}")


def main():
    sources = load_sources()

    for name, url in sources.items():
        download_file(name, url)


if __name__ == "__main__":
    main()
# price index