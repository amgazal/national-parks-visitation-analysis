"""Download official NPS 2025 visitation and metadata inputs."""

from pathlib import Path
from urllib.request import urlopen
import hashlib
import json
import csv
import shutil
from datetime import datetime, timezone
import xml.etree.ElementTree as ET


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
    manifest = {}
    for filename, url in SOURCES.items():
        destination = RAW / filename
        temporary = destination.with_suffix(destination.suffix + ".part")
        print(f"Downloading {filename}...", flush=True)
        try:
            with urlopen(url, timeout=120) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
            if filename.endswith(".csv"):
                with temporary.open() as handle:
                    columns = next(csv.reader(handle))
                if not {"UnitCode", "Year", "Month", "Statistic", "Value"}.issubset(columns):
                    raise ValueError("Unexpected CSV schema")
            elif filename.endswith(".xml"):
                ET.parse(temporary)
            else:
                payload = json.loads(temporary.read_text())
                if int(payload["total"]) != len(payload["data"]):
                    raise ValueError("API response is truncated; pagination required")
            temporary.replace(destination)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Download failed for {filename}; existing snapshot preserved: {exc}") from exc
        manifest[filename] = dict(url=url, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                                  bytes=destination.stat().st_size,
                                  sha256=hashlib.file_digest(destination.open("rb"), "sha256").hexdigest())
    (RAW / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Downloaded {len(SOURCES)} files to {RAW}")


if __name__ == "__main__":
    main()
