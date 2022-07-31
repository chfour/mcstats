#!/usr/bin/env python3
import glob, sys, os.path, locale

root_dir = sys.argv[1]

for logfile in sorted(glob.iglob("*.log", root_dir=root_dir), key=lambda n: [int(i) for i in n[:-4].split("-")]):
    logfile = os.path.join(root_dir, logfile)
    print(logfile)
