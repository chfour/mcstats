#!/usr/bin/env python3
import glob, sys, os.path, locale, re
from datetime import datetime, date, time

root_dir = sys.argv[1]

for logfile in sorted(glob.iglob("*.log", root_dir=root_dir), key=lambda n: [int(i) for i in n[:-4].split("-")]):
    filedate = datetime.strptime(logfile[:logfile.rindex("-")], "%Y-%m-%d")
    
    logfile = os.path.join(root_dir, logfile)
    print(f"  opening {logfile} ({filedate.date()})", file=sys.stderr)

    with open(logfile) as f:
        for line in f:
            line = line.strip()
            if not re.match(r"^\[\d\d:\d\d:\d\d\] \[", line): continue
            msgtime = datetime.combine(filedate, datetime.strptime(line[:line.index(" ")], "[%H:%M:%S]").time())
            line = line[line.index(" ")+1:]
            if line.startswith("[Server thread/INFO]: Starting minecraft server"):
                print(f"! start @ {msgtime}", file=sys.stderr)
            elif line == "[Server thread/INFO]: Closing Server":
                print(f"! stop  @ {msgtime}", file=sys.stderr)
