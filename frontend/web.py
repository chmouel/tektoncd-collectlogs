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
import os

import flask

from dateutil import parser as dtparse

DATADIR = os.environ.get(
    'DATADIR',
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "data")))

app = flask.Flask(__name__, static_url_path='')


def build_pipelineruns_status():
    ret = []
    for log in glob.glob(DATADIR + "/*.json"):
        j = json.load(open(log))

        if j['conditions'][0]['reason'] == 'Succeeded':
            classname = 'success'
        elif j['conditions'][0]['reason'] == 'Failed':
            classname = 'danger'
        else:
            classname = 'info'
        prname = os.path.basename(log.replace(".json", ""))
        ret.append({
            'finishtime': dtparse.parse(j['completionTime']),
            'classname': classname,
            'prname': prname
        })
    return sorted(ret, key=lambda p: p['finishtime'])


@app.route('/')
def index():
    prs = build_pipelineruns_status()
    from pprint import pprint as p
    p(prs)

    return flask.render_template('index.html', prs=prs)


if __name__ == '__main__':
    app.run()
