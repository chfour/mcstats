#!/usr/bin/env python3
import glob, sys, os.path, re, gzip
from datetime import datetime, date, timedelta
import time
from math import inf, floor

root_dir = sys.argv[1]
stats = {
    "server": {
        "last": None,
        "total": timedelta(),
        "idle": timedelta(),
        "idlestart": None
    },
    "players": {}
}

def _stripext(fname: str) -> str:
    fname = os.path.basename(fname)
    while fname.endswith(".gz") or fname.endswith(".log"):
        fname = fname[:fname.rindex(".")]

    return fname

def _sortkey(fname: str) -> list:
    fname = _stripext(fname)
    if fname == "latest":
        return [inf]
    return [int(i) for i in fname.split("-")]

for logfile in sorted(glob.iglob("*.log*", root_dir=root_dir), key=_sortkey):
    logfile = os.path.join(root_dir, logfile)
    print(f"  opening {logfile}", file=sys.stderr)

    _fname = _stripext(logfile)
    if _fname == "latest": # assume latest.log has correct timestamp
        filedate = date.fromtimestamp(os.path.getctime(logfile))
        print(f"  assuming latest.log has correct ctime {filedate}", file=sys.stderr)
    else:
        filedate = datetime.strptime(_fname[:_fname.rindex("-")], "%Y-%m-%d")

    if logfile.endswith(".gz"):
        print("  -> is gzip...", file=sys.stderr)
        f = gzip.open(logfile, "rt")
    else:
        f = open(logfile, "rt")

    with f:
        for line in f:
            line = line.strip()
            if not re.match(r"^\[\d\d:\d\d:\d\d\] \[", line): continue
            msgtime = datetime.combine(filedate, datetime.strptime(line[:line.index(" ")], "[%H:%M:%S]").time())
            line = line[line.index(" ")+1:]
            
            if line.startswith("[Server thread/INFO]: "):
                line = line[22:]

                # start
                if line.startswith("Starting minecraft server"):
                    stats["server"]["idlestart"] = stats["server"]["last"] = msgtime
                    print(f"! {msgtime} : start", file=sys.stderr)
                    print("* idle: started", file=sys.stderr)

                # stop
                elif line == "Closing Server":
                    stats["server"]["total"] += msgtime - stats["server"]["last"]
                    stats["server"]["idle"] += msgtime - stats["server"]["idlestart"]
                    stats["server"]["last"] = None
                    print(f"! {msgtime} : stop -> running count is {stats['server']['total']}", file=sys.stderr)
                    print(f"* dump idle: server stop -> running count is {stats['server']['idle']}", file=sys.stderr)

                # joined
                elif re.match(r"^[a-zA-Z0-9_]* joined the game$", line):
                    player = line[:line.index(" ")]
                    print(f"! {msgtime} : joined:  '{player: <16}'", file=sys.stderr)
                    if player not in stats["players"]: stats["players"][player] = {
                        "last": None, "playtime": timedelta(),
                        "deaths": 0, "commands": 0,
                        "messages": 0, "advancements": 0
                    }
                    stats["players"][player]["last"] = msgtime
                    stats["players"][player]["online"] = True
                    if len(list(filter(lambda p: p["online"], stats["players"].values()))) < 2:
                        stats["server"]["idle"] += msgtime - stats["server"]["idlestart"]
                        stats["server"]["idlestart"] = None
                        print(f"* no longer idle: first player joined -> running count is {stats['server']['idle']}", file=sys.stderr)

                # left
                elif re.match(r"^[a-zA-Z0-9_]* lost connection: .*$", line):
                    player = line[:line.index(" ")]
                    reason = line[line.index(" "):][18:]
                    stats["players"][player]["playtime"] += msgtime - stats["players"][player]["last"]
                    stats["players"][player]["online"] = False
                    print(f"! {msgtime} : left:    '{player: <16}', '{reason}' -> running count is {stats['players'][player]['playtime']}", file=sys.stderr)
                    if not any([p["online"] for p in stats["players"].values()]):
                        stats["server"]["idlestart"] = msgtime
                        print("* idle: no online players", file=sys.stderr)
                        

                # death
                elif re.match(r"^[a-zA-Z0-9_]* (was|drowned|experienced|blew|hit|fell|went|walked|burned|discovered|froze|starved|suffocated|didn't|withered|died).*$", line):
                    player = line[:line.index(" ")]
                    reason = line[line.index(" ")+1:]
                    print(f"! {msgtime} : death:   '{player: <16}', '{reason}'", file=sys.stderr)
                    stats["players"][player]["deaths"] += 1

                # command
                elif re.match(r"^[a-zA-Z0-9_]* issued server command: .*$", line):
                    player = line[:line.index(" ")]
                    command = line[line.index(": ")+2:]
                    print(f"! {msgtime} : command: '{player: <16}', '{command}'", file=sys.stderr)
                    stats["players"][player]["commands"] += 1

                elif re.match(r"^[a-zA-Z0-9_]* has made the advancement \[.*\]$", line):
                    player = line[:line.index(" ")]
                    advname = line[line.index(" [")+2:-1]
                    print(f"! {msgtime} : adv:     '{player: <16}', '{advname}'", file=sys.stderr)
                    stats["players"][player]["advancements"] += 1

            # chatmsg
            elif re.match(r"^\[Async Chat Thread - #\d+/INFO\]:( \[Not Secure\]){0,1} <", line):
                line = line[line.index("]: ")+3:]
                if line.startswith("[Not Secure] "):
                    line = line[line.index("] <")+3:]
                else:
                    line = line[1:]
                player = line[:line.index("> ")]
                content = line[line.index("> ")+2:]
                print(f"! {msgtime} : chatmsg: '{player: <16}', '{content}'", file=sys.stderr)
                stats["players"][player]["messages"] += 1

stats["server"]["running"] = stats["server"]["last"] is not None
stats["server"]["isidle"] = stats["server"]["idlestart"] is not None
now = datetime.fromtimestamp(floor(time.time()))
if stats["server"]["running"]:
    stats["server"]["total"] += now - stats["server"]["last"]
if stats["server"]["isidle"]:
    stats["server"]["idle"] += now - stats["server"]["idlestart"]

for p in stats["players"]:
    if stats["players"][p]["online"]:
        stats["players"][p]["playtime"] += now - stats["players"][p]["last"]

#print(stats)
if "-fjson" in sys.argv:
    import json
    newstats = {
        "server": {
            "total_uptime": stats["server"]["total"].seconds,
            "idle_time": stats["server"]["idle"].seconds,
            "is_idle": stats["server"]["isidle"],
            "running": stats["server"]["running"]
        },
        "players": {}
    }
    for p in stats["players"]:
        newstats["players"][p] = {
            "playtime": stats["players"][p]["playtime"].seconds,
            "is_online": stats["players"][p]["online"],
            "deaths": stats["players"][p]["deaths"],
            "messages": stats["players"][p]["messages"],
            "commands": stats["players"][p]["commands"],
            "advancements": stats["players"][p]["advancements"]
        }
    json.dump(newstats, sys.stdout)
    sys.stdout.write("\n")
else:
    print(f"""Server:
  Total uptime: {stats['server']['total']}{' + running' if stats['server']['running'] else ''}
  Idle: {stats['server']['idle']}{' + idling' if stats['server']['isidle'] else ''}
Players:""")
    for p, s in sorted(stats["players"].items(), key=lambda p: p[1]["playtime"], reverse=True):
        print(f"""  {p: <16}
    total playtime: {stats['players'][p]['playtime']}{' + online' if stats['players'][p]['online'] else ''}
    deaths:{stats['players'][p]['deaths']: >7}, messages:{stats['players'][p]['messages']: >8}
    commands:{stats['players'][p]['commands']: >5}, advancements:{stats['players'][p]['advancements']: >4}""")
