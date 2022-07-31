#!/usr/bin/env python3
import glob, sys, os.path, re
from datetime import datetime, date, time, timedelta

root_dir = sys.argv[1]
stats = {
    "server": {
        "last": None,
        "total": timedelta()
    },
    "players": {}
}

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
            
            if line.startswith("[Server thread/INFO]: "):
                line = line[22:]

                # start
                if line.startswith("Starting minecraft server"):
                    stats["server"]["last"] = msgtime
                    print(f"! {msgtime} : start", file=sys.stderr)

                # stop
                elif line == "Closing Server":
                    stats["server"]["total"] += msgtime - stats["server"]["last"]
                    print(f"! {msgtime} : stop -> running count is {stats['server']['total']}", file=sys.stderr)

                # joined
                elif re.match(r"^[a-zA-Z0-9_]* joined the game$", line):
                    player = line[:line.index(" ")]
                    print(f"! {msgtime} : joined:  '{player: <16}'")
                    if player not in stats["players"]: stats["players"][player] = {
                        "last": None, "playtime": timedelta(),
                        "deaths": 0, "commands": 0,
                        "messages": 0, "advancements": 0
                    }
                    stats["players"][player]["last"] = msgtime
                    stats["players"][player]["online"] = True

                # left
                elif re.match(r"^[a-zA-Z0-9_]* lost connection: .*$", line):
                    player = line[:line.index(" ")]
                    reason = line[line.index(" "):][18:]
                    stats["players"][player]["playtime"] += msgtime - stats["players"][player]["last"]
                    stats["players"][player]["online"] = False
                    print(f"! {msgtime} : left:    '{player: <16}', '{reason}' -> running count is {stats['players'][player]['playtime']}")

                # death
                elif re.match(r"^[a-zA-Z0-9_]* (was|drowned|experienced|blew|hit|fell|went|walked|burned|discovered|froze|starved|suffocated|didn't|withered|died).*$", line):
                    player = line[:line.index(" ")]
                    reason = line[line.index(" ")+1:]
                    print(f"! {msgtime} : death:   '{player: <16}', '{reason}'")
                    stats["players"][player]["deaths"] += 1

                # command
                elif re.match(r"^[a-zA-Z0-9_]* issued server command: .*$", line):
                    player = line[:line.index(" ")]
                    command = line[line.index(": ")+2:]
                    print(f"! {msgtime} : command: '{player: <16}', '{command}'")
                    stats["players"][player]["commands"] += 1

                elif re.match(r"^[a-zA-Z0-9_]* has made the advancement \[.*\]$", line):
                    player = line[:line.index(" ")]
                    advname = line[line.index(" [")+2:-1]
                    print(f"! {msgtime} : adv:     '{player: <16}', '{advname}'")
                    stats["players"][player]["advancements"] += 1

            # chatmsg
            elif re.match(r"^\[Async Chat Thread - #\d+/INFO\]: <", line):
                line = line[line.index(": <")+3:]
                player = line[:line.index("> ")]
                content = line[line.index("> ")+2:]
                print(f"! {msgtime} : chatmsg: '{player: <16}', '{content}'")
                stats["players"][player]["messages"] += 1
                

#print(stats)
print(f"Server:\n Total uptime: {stats['server']['total']}\nPlayers:")
for p, s in sorted(stats["players"].items(), key=lambda p: p[1]["playtime"], reverse=True):
    print(f" {p: <16} {stats['players'][p]['playtime']} total playtime, deaths: {stats['players'][p]['deaths']}")
    print(" "*18+f"messages sent: {stats['players'][p]['messages']: >5}, commands issued: {stats['players'][p]['commands']: >5}")
    print(" "*18+f"advancements made: {stats['players'][p]['advancements']: >3}")
