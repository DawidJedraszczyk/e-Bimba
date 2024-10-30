from pathlib import Path
import shutil
import subprocess
import zipfile


_FUSE_ZIP = "fuse-zip"


def unzip(file: Path, folder: Path):
  if folder.exists():
    if next(folder.iterdir(), None) is not None:
      print(f"Folder '{folder}' is not empty, assuming alread unzipped")
      return

    print(f"Removing empty folder '{folder}'")
    folder.rmdir()

  if shutil.which(_FUSE_ZIP) is not None:
    try:
      print(f"Mounting '{file}' as '{folder}' using {_FUSE_ZIP}")
      folder.mkdir()
      subprocess.run([_FUSE_ZIP, "-r", file, folder], check=True)
      return
    except Exception as e:
      print(f"Failed ({e})")
      folder.rmdir()

  print(f"Unzipping '{file}' to '{folder}'")

  with zipfile.ZipFile(file, "r") as zip:
    zip.extractall(folder)
