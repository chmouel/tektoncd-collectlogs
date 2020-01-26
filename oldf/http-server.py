#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Chmouel Boudjnah <chmouel@chmouel.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import glob
import json
import os.path
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

DATADIR = os.environ.get(
    'DATADIR',
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "data")))
HOST = os.environ.get("HOST", 'localhost')
PORT = os.environ.get("PORT", 8080)

LINK_TEMPLATE = f"""
           <a href="/log/%(prname)s"
              class="list-group-item list-group-item-%(classname)s">
           %(prname)s
           </a>
           """

LOG_POD_TEMPLATE = """
      <button type="button" class="btn btn-%(classname)s">Taskrun: %(taskrun)s
      </button>
      <br/>
      <div style="margin-right: 5px; margin-left: 5px; padding: 10px;"
           class="text-justify shadow-lg p-3 lb-5 bg-white rounded
                  border shadow border mx-auto">
"""

LOG_STEP_TEMPLATE = """
      <button type="button" class="btn btn-%(classname)s">
                Step: %(stepname)s
      </button>
      <div style="margin-right: 5px; margin-left: 5px; padding: 10px;"
           class="text-justify shadow-mg p-3 mb-5 bg-white rounded
                  border-%(classname)s shadow border mx-auto">
        %(log)s
      </div>

"""


def highlight_log(data):
    ret = re.sub("((ERROR|FAIL).*?)\n",
                 "<span class='text-white bg-danger'>\\1</span><br/>", data)
    ret = re.sub("((SUCCESS).*?)\n",
                 "<span class='text-white bg-success'>\\1</span><br/>", ret)
    return ret.replace("\n", "<br/>")


def build_all_prs():
    ret = ""
    for log in glob.glob(DATADIR + "/*.json"):
        j = json.load(open(log))
        if j['conditions'][0]['reason'] == 'Succeeded':
            classname = 'success'
        elif j['conditions'][0]['reason'] == 'Failed':
            classname = 'danger'
        else:
            print(j['conditions'][0])
        prname = os.path.basename(log.replace(".json", ""))
        ret += LINK_TEMPLATE % {
            'classname': classname,
            'prname': prname
        } + "\n"
    return ret


def show_log(prun):
    fpath = os.path.join(DATADIR, prun + ".json")
    if not os.path.exists(fpath):
        return ('%s is not found' % (prun))
    ret = ""
    j = json.load(open(fpath))

    for trn in j['taskRuns']:
        tr = j['taskRuns'][trn]
        if tr['status']['conditions'][0]['reason'] == 'Succeeded':
            classname = 'success'
        elif tr['status']['conditions'][0]['reason'] == 'Failed':
            classname = 'danger'
        else:
            classname = 'info'

        ret += LOG_POD_TEMPLATE % {
            'classname': classname,
            # 'log': highlight_log(open(logpath).read()),
            "prname": prun,
            'taskrun': trn,
            'steps': "",
        } + "\n"

        for container in tr['status']['steps']:
            logpath = os.path.join(
                DATADIR, prun + "-" + tr['status']['podName'] + "-" +
                container['container'] + ".log")
            if 'terminated' in container and container['terminated'][
                    'exitCode'] == 0:
                classname = 'success'
            elif 'terminated' in container and container['terminated'][
                    'exitCode'] == 1:
                classname = 'danger'
            else:
                classname = 'warning'

            ret += LOG_STEP_TEMPLATE % {
                'classname': classname,
                'log': highlight_log(open(logpath).read()),
                'stepname': container['name'],
            }
        ret += "</div><br/>\n"
    return ret


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        ret = ''
        retcode = 200
        contenttype = "text/html"

        if not self.path or self.path == "/":
            ret = open('frontend/index.html').read().replace(
                "%LI%", build_all_prs())
        elif self.path.startswith("/js"):
            ret = open('frontend/js/' + self.path.replace("/js", "")).read()
            contenttype = 'application/javascript'
        elif self.path.startswith("/css"):
            ret = open('frontend/css/' + self.path.replace("/css", "")).read()
            contenttype = 'text/css'
        elif self.path.startswith("/log") and not self.path.endswith(".log"):
            ret = open('frontend/log.html').read()
            pipelinerun = self.path.replace("/log/", "")
            ret = ret.replace("%PIPELINE%", pipelinerun)
            ret = ret.replace("%LOGS%", show_log(pipelinerun))

        else:
            retcode = 404
            ret = '%s not Found' % (self.path)

        self.send_response(retcode)
        self.send_header("Content-type", contenttype)
        self.end_headers()
        self.wfile.write(bytes(ret, "utf8"))
        return


print("Starting webserver on %s:%d" % (HOST, PORT))
httpd = HTTPServer((HOST, PORT), SimpleHTTPRequestHandler)
httpd.serve_forever()
