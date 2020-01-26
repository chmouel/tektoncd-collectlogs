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
import re

import flask
from dateutil import parser as dtparse

DATADIR = os.environ.get(
    'DATADIR',
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "data")))

app = flask.Flask(__name__, static_url_path='')


def highlight_log(data):
    ret = re.sub("((ERROR|FAIL).*?)\n",
                 "<span class='text-white bg-danger'>\\1</span><br/>", data)
    ret = re.sub("((SUCCESS).*?)\n",
                 "<span class='text-white bg-success'>\\1</span><br/>", ret)
    return ret.replace("\n", "<br/>")


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


def steps_status(prun, podName, steps):
    ret = []
    for container in steps:
        logpath = os.path.join(
            DATADIR,
            prun + "-" + podName + "-" + container['container'] + ".log")
        # TODO: handle erorr not found
        if 'terminated' in container and container['terminated'][
                'exitCode'] == 0:
            classname = 'success'
            starttime = dtparse.parse(container['terminated']['startedAt'])
        elif 'terminated' in container and container['terminated'][
                'exitCode'] == 1:
            classname = 'danger'
            starttime = dtparse.parse(container['terminated']['startedAt'])
        elif 'running' in container:
            starttime = dtparse.parse(container['running']['startedAt'])
            classname = 'primary'
        else:
            classname = 'warning'
            starttime = None

        # TODO: step time
        ret.append({
            'time': starttime,
            'classname': classname,
            'log': highlight_log(open(logpath).read()),
            'stepname': container['name'],
        })

    return sorted(ret, key=lambda p: p['time'])


def build_pr_log(pr):
    fpath = os.path.join(DATADIR, pr + ".json")
    if not os.path.exists(fpath):
        return ('%s is not found' % (pr))
    ret = []
    j = json.load(open(fpath))

    for trn in j['taskRuns']:
        tr = j['taskRuns'][trn]
        if tr['status']['conditions'][0]['reason'] == 'Succeeded':
            emoji = '✅'
        elif tr['status']['conditions'][0]['reason'] == 'Failed':
            emoji = '❌'
        else:
            emoji = '❓'

        if 'completionTime' in tr['status']:
            time = tr['status']['completionTime']
        elif 'startTime' in tr['status']:
            time = tr['status']['startTime']
        else:
            time = None

        ret.append({
            'time':
            time,
            'emoji':
            emoji,
            'taskrun':
            trn,
            'steps':
            steps_status(pr, tr['status']['podName'], tr['status']['steps']),
        })

    return sorted(ret, key=lambda p: p['time'], reverse=True)


@app.route('/log/<pr>')
def log(pr):
    return flask.render_template('log.html', pr=pr, prlog=build_pr_log(pr))


@app.route('/')
def index():
    return flask.render_template('index.html', prs=build_pipelineruns_status())


if __name__ == '__main__':
    app.run()