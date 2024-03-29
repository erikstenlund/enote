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

class App():
    def __init__(self, conf):
        self.conf = conf
        self.date = dt.datetime.now().date().isoformat()
        self.timelog = conf["timelog"]

    def log_time(self, args):
        date = self.date
        if len(args) > 0:
            date = args[0]

        with open(self.timelog, 'r') as f:
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


    def start_time(self, args):
        self._write_time("S")


    def end_time(self, args):
        self._write_time("E")


    def _write_time(self, t, post=""):
        pt = "S"
        if pt == t:
            pt = "E"

        template = t + "{}"

        if post != "":
            template += (" " + post)

        time_events_json = {}
        with open(self.timelog, 'r') as f:
            time_events_json = json.load(f)
            now = dt.datetime.now()
            time_event = template.format(now.time().isoformat(timespec='minutes'))
            if self.date in time_events_json:
                if pt not in time_events_json[self.date][-1]:
                    time_events_json[self.date].append(pt)
                time_events_json[self.date].append(time_event)
            else:
                time_events_json[self.date] = [time_event]

        with open(self.timelog, 'w') as f:
            json.dump(time_events_json, f)


    def _create_daily(self):
        with open(self.conf["daily"] + "/" + self.date + ".md", "w") as f:
            f.write("# {}\n".format(self.date))
            with open(self.conf["template"], "r") as t:
                f.writelines(t.readlines())


    def edit_daily(self, args):
        if len(args) > 0:
            return self._edit_prev(args[0])

        path = self.conf["daily"] + "/" + self.date + ".md"
        if not os.path.exists(path):
            self._create_daily()

        subprocess.run([self.conf["editor"], path])


    def _edit_prev(self, date):
        path = self.conf["daily"] + "/" + date + ".md"
        if not os.path.exists(path):
            print("No daily note from {} exist!".format(date))

        subprocess.run([self.conf["editor"], path])


    def edit_fixed(self, args):
        subprocess.run([self.conf["editor"], self.conf["fixed"]])


    def cat_yesterday(self, args):
        if len(args) > 0:
            date = args[0]
        else:
            date = (dt.datetime.now() - dt.timedelta(1)).date().isoformat()

        path = self.conf["daily"] + "/" + date + ".md"
        grep = subprocess.run(["grep", "--after-context=50", "Summary", path], capture_output=True)
        grep = subprocess.run(["grep", "--invert-match", "Summary"], input=grep.stdout, capture_output=True)

        print(grep.stdout.decode("utf-8"))


    def grep(self, args):
        dailies = [self.conf["daily"] + "/" + note for note in os.listdir(self.conf["daily"])]
        grep = subprocess.run(["grep", *args, *dailies, self.conf["fixed"]], capture_output=True)

        print(grep.stdout.decode("utf-8"))


    def backup(self, args):
        files_to_backup = [
            self.conf["daily"],
            self.conf["fixed"],
            self.timelog
        ]

        subprocess.run(["git", "add"] + files_to_backup)
        subprocess.run(["git", "commit", "-m", dt.datetime.now().isoformat()])
        # subprocess.run(["git", "push", "origin", "main"])


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
        empty = {}
        json.dump(empty, f)

    with open(initial_config["workingdir"] + '/' + initial_config["template"], "w") as f:
        template = """## ToDo
## Notes
## Summary
        """
        f.write(template)

    os.chdir(initial_config["workingdir"])
    subprocess.run(["git", "init"])


def enote(command, args, conf):
    app = App(conf)
    commands = {
        "backup": app.backup,
        "start": app.start_time,
        "end": app.end_time,
        "log": app.log_time,
        "daily": app.edit_daily,
        "edit": app.edit_fixed,
        "standup": app.cat_yesterday,
        "grep": app.grep
    }

    if command in commands:
        commands[command](args)
    else:
        print_usage()


def print_usage():
    usage = """usage: {} <command>

commands:
    backup - Create a git commit with notes and timelog
    start - Start logging time
    end - Stop logging time
    log - Print time worked today
    daily - Edit notes for today
    edit - Edit static note
    standup - Print summary for yesterdays note
    grep - Grep notes
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
        enote(sys.argv[1], sys.argv[2:], conf)


if __name__ == "__main__":
    cli()