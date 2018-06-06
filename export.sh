#!/usr/bin/env bash
sqlite3 -header -csv db.sqlite3 < export.sql > static/out.csv
echo "Exported $(wc -l < static/out.csv) files"
rm static/out.csv.xz
xz static/out.csv
echo "Compressed to $(stat --printf="%s" static/out.csv.xz) bytes"