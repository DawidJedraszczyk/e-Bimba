#!/usr/bin/env python3

from pathlib import Path
import sys

SCRIPT_FOLDER = Path(__file__).parent
sys.path.append(str(SCRIPT_FOLDER.parent / "ebus"))

from transit.db import *
from transit.transitdb import *
from transit.unzip import *


SQL_GTFS_FOLDER = SCRIPT_FOLDER.parent / "ebus" / "transit" / "sql" / "gtfs"


def get_import_script(name: str) -> str:
  return (SQL_GTFS_FOLDER / "import" / f"{name}.sql").read_text().replace(
    "insert into gtfs_",
    "insert into ",
  )


def import_gtfs(gtfs_zip: Path, db_path: Path):
  init_script = (SQL_GTFS_FOLDER / "init.sql").read_text().replace(
    "create temp table gtfs_",
    "create table ",
  )

  gtfs_folder = gtfs_zip.parent / gtfs_zip.name.replace(".zip", "")
  unzip(gtfs_zip, gtfs_folder)

  with Db(db_path, Path.cwd()) as db:
    db.set_variable("GTFS_FOLDER", str(gtfs_folder))
    db.sql(init_script)
    db.sql(get_import_script("required"))

    for opt in TransitDb.OPTIONAL_GTFS_FILES:
      if (gtfs_folder / opt).exists():
        db.sql(get_import_script(opt[:-4].replace("_", "-")))


if __name__ == "__main__":
  args = sys.argv

  if len(args) < 3:
    print(f"Usage: {args[0]} GTFS_ZIP GTFS_DB")
  else:
    gtfs_zip = Path(args[1])
    gtfs_db = Path(args[2])
    import_gtfs(gtfs_zip, gtfs_db)
