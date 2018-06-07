#!/usr/bin/env bash
sqlite3 -header -csv db.sqlite3 < export.sql > out.csv.temp
echo "Exported $(wc -l < out.csv.temp) files"
xz out.csv.temp
mv out.csv.temp.xz static/out.csv.xz
echo "Compressed to $(stat --printf="%s" static/out.csv.xz) bytes"