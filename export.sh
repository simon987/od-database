#!/usr/bin/env bash
sqlite3 -header -csv db.sqlite3 < export.sql > out.csv
echo "Exported $(wc -l < out.csv) files"
rm out.csv.xz
xz out.csv
echo "Compressed to $(stat --printf="%s" out.csv.xz) bytes"