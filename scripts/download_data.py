"""Download official NPS 2025 visitation and metadata inputs."""

from pathlib import Path
from urllib.request import urlretrieve


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SOURCES = {
    "Main_Data.csv": "https://irma.nps.gov/DataStore/DownloadFile/756959?Reference=2317666",
    "Main_State_Data.csv": "https://irma.nps.gov/DataStore/DownloadFile/756960?Reference=2317666",
    "NPS_VUStats_Data_2025_metadata.xml": "https://irma.nps.gov/DataStore/DownloadFile/756961?Reference=2317666",
    "nps_parks_api.json": "https://developer.nps.gov/api/v1/parks?limit=500&api_key=DEMO_KEY",
}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for filename, url in SOURCES.items():
        destination = RAW / filename
        print(f"Downloading {filename}...")
        urlretrieve(url, destination)
    print(f"Downloaded {len(SOURCES)} files to {RAW}")


if __name__ == "__main__":
    main()
