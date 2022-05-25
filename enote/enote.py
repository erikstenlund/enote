#!/usr/bin/env python3
#
# Script to log working hours and manage simple notes
#
# Copyright (c) 2022 Erik Stenlund
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software 
# Foundation, either version 3 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
# 
# You should have received a copy of the GNU General Public License along with this
# program. If not, see <https://www.gnu.org/licenses/>. 

import json
import datetime as dt
import sys
from dateutil import parser
import subprocess
import os

def log_time(conf, date = ''):
    if date == '':
        date = dt.datetime.now().date().isoformat()

    with open(conf["timelog"], 'r') as f:
        today = json.load(f)[date]
        start_times = today[::2]
        end_times = today[1::2]
        tuples = zip(start_times, end_times)
        tuples = map(lambda t: (t[0][1:], t[1][1:]), tuples)
        tuples = filter(lambda t: t[0] != "" and t[1] != "", tuples)
        tuples = map(lambda t: (parser.parse(t[0]), parser.parse(t[1])), tuples)
        diff = dt.timedelta()
        for x in tuples:
            diff = diff + (x[1] - x[0])
            
        print(diff)


def start_time(conf):
    _write_time(conf, "S")


def end_time(conf):
    _write_time(conf, "E")


def _write_time(conf, t, post=""):
    pt = "S"
    if pt == t:
        pt = "E"

    template = t + "{}"
    
    if post != "":
        template += (" " + post)

    time_events_json = {}
    with open(conf["timelog"], 'r') as f:
        time_events_json = json.load(f)
        now = dt.datetime.now()
        date = now.date().isoformat()
        time_event = template.format(now.time().isoformat(timespec='minutes'))
        if date in time_events_json:
            if pt not in time_events_json[date][-1]:
                time_events_json[date].append(pt)
            time_events_json[date].append(time_event)
        else:
            time_events_json[date] = [time_event]

    with open(conf['timelog'], 'w') as f:
        json.dump(time_events_json, f)


def _create_daily(conf):
    now = dt.datetime.now()
    date = now.date().isoformat()
    with open(conf["daily"] + "/" + date + ".md", "w") as f:
        f.write("# {}\n".format(date))
        with open(conf["template"], "r") as t:
            f.writelines(t.readlines())


def edit_daily(conf):
    now = dt.datetime.now()
    date = now.date().isoformat()
    path = conf["daily"] + "/" + date + ".md"
    if not os.path.exists(path):
        _create_daily()

    subprocess.run([conf["editor"], path])


def edit_fixed(conf):
    subprocess.run([conf["editor"], conf["fixed"]])


def backup():
    files_to_backup = [
        conf["daily"],
        conf["fixed"],
        conf["timelog"]
    ]

    subprocess.run(["git", "add"] + files_to_backup)
    subprocess.run(["git", "commit", "-m", dt.datetime.now().isoformat()])
    subprocess.run(["git", "push", "origin", "main"])
    

def initialize(home):
    initial_config = {
        "workingdir": home + ".enote",
        "timelog": "timelog.txt",
        "template": "template.md",
        "fixed": "notes.md",
        "daily": "daily",
        "editor": "gvim"
    }
    os.mkdir(initial_config["workingdir"])
    os.mkdir(initial_config["workingdir"] + '/' + initial_config["daily"])
    with open(home + ".enote.conf", "w") as f:
        json.dump(initial_config, f)

    with open(initial_config["workingdir"] + '/' + initial_config["timelog"], "w") as f:
        json.dump("{}", f)

    with open(initial_config["workingdir"] + '/' + initial_config["template"], "w") as f:
        template = """## ToDo
## Notes
## Summary
        """
        f.write(template)

    os.chdir(initial_config["workingdir"])
    subprocess.run(["git", "init"])
    





def enote(command, conf):
    commands = {
        "backup": backup,
        "start": start_time,
        "end": end_time,
        "log": log_time,
        "daily": edit_daily,
        "edit": edit_fixed
    }

    if command in commands:
        commands[command](conf)
    else:
        print_usage()


def print_usage():
    usage = """usage: {} <command>
            
commands:
    backup -
    start -
    end -
    log -
    daily -
    edit -
    """.format(sys.argv[0])
    print(usage)


def cli():
    conf_path = os.path.expanduser("~/.enote.conf")
    if not os.path.exists(conf_path):
        print("{} not found, initializing enote".format(conf_path))
        initialize(os.path.expanduser("~/"))
    
    with open(conf_path) as f:
        conf = json.load(f)

    if len(sys.argv) < 2:
        print_usage()
    else:
        os.chdir(conf["workingdir"])
        enote(sys.argv[1], conf)


if __name__ == "__main__":
    cli()