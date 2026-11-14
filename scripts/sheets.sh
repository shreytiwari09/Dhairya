#!/bin/sh
# Usage: scripts/sheets.sh <dir>  - joins s00..s15.jpg into four 2x2 contact sheets
d="$1"
i=0
while [ $i -lt 16 ]; do
  a=$(printf "%02d" $i); b=$(printf "%02d" $((i+1))); c=$(printf "%02d" $((i+2))); e=$(printf "%02d" $((i+3)))
  ffmpeg -y -loglevel error -i "$d/s$a.jpg" -i "$d/s$b.jpg" -i "$d/s$c.jpg" -i "$d/s$e.jpg" -filter_complex "[0][1]hstack[x];[2][3]hstack[y];[x][y]vstack,scale=1440:-1" "$d/sheet_$a.jpg"
  i=$((i+4))
done
