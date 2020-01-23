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
import os.path
from http.server import BaseHTTPRequestHandler, HTTPServer

DATADIR = os.environ.get('DATADIR', "./data")
HOST = 'localhost'
PORT = 8000

TEMPLATE = """
           <li> <div class="showp"> %s
           <div id="%s" class="log"
           style="visibility: hidden; display: none;"></div>
           </div> </li>
           """


def build_all_prs():
    ret = ""
    for log in glob.glob(DATADIR + "/*.json"):
        sansext = os.path.basename(log.replace(".json", ""))
        ret += TEMPLATE % (sansext, sansext) + "\n"
    return ret


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        ret = ''
        retcode = 200
        if not self.path or self.path == "/":
            ret = open('frontend/index.html').read().replace(
                "%LI%", build_all_prs())
        elif self.path.startswith("/log"):
            fname = self.path.replace("/log/", "")
            path = os.path.join(DATADIR, fname)
            if not os.path.exists(path):
                self.send_response(404)
                ret = '%s is not found' % (fname)
                retcode = 404
            else:
                ret = open(path).read()
        else:
            retcode = 404
            ret = '%s not Found' % (self.path)

        self.send_response(retcode)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(ret, "utf8"))
        return


print("Starting webserver on %s:%d" % (HOST, PORT))
httpd = HTTPServer((HOST, PORT), SimpleHTTPRequestHandler)
httpd.serve_forever()
