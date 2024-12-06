#!/usr/bin/env python3

from pathlib import Path
import pyarrow.parquet as pq
import sys

if len(sys.argv) < 3:
  print(f"Usage: {sys.argv[0]} SRC_FOLDER DST_FILE")
  sys.exit()

table = pq.read_table(sys.argv[1])
pq.write_table(table, sys.argv[2])
