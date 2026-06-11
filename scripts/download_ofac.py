"""Download the real OFAC SDN list and convert it to our simple CSV shape.

The U.S. Treasury publishes the Specially Designated Nationals (SDN) list for
free. This script downloads the consolidated CSV and writes a normalised file
with just the columns our sanctions tool expects: name, program, type.

Usage:
    python scripts/download_ofac.py

Then tell the sanctions tool to use it:
    export SANCTIONS_FILE=data/ofac_sdn.csv          # macOS / Linux
    set SANCTIONS_FILE=data\\ofac_sdn.csv             # Windows

The published format changes occasionally; if the columns below don't line up,
open the downloaded file and adjust the indices. Treating real-world data as
"will break eventually" is itself a lesson worth keeping.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import requests

# Treasury's consolidated SDN CSV. (No header row; positional columns.)
SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
OUT = Path(__file__).resolve().parents[1] / "data" / "ofac_sdn.csv"


def main() -> None:
    print(f"Downloading {SDN_URL} ...")
    resp = requests.get(SDN_URL, timeout=60)
    resp.raise_for_status()

    rows_in = csv.reader(io.StringIO(resp.text))
    written = 0
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["name", "program", "type"])
        for row in rows_in:
            # SDN columns: 0=ent_num, 1=name, 2=type, 3=program, ...
            if len(row) < 4:
                continue
            name = row[1].strip().strip('"')
            if not name or name == "-0-":
                continue
            writer.writerow([name, row[3].strip(), row[2].strip()])
            written += 1

    print(f"Wrote {written} entries to {OUT}")
    print("Now set SANCTIONS_FILE to this path to use it.")


if __name__ == "__main__":
    main()
