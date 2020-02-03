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
# NOTE: This still is modeled to the old simple filesystem based pre-DB
# way... which is not very efficient but still maps it well to DB, will change
# it when i have the courage.
import json
import os
import re
import sqlite3

import flask
from dateutil import parser as dtparse

DATADIR = os.environ.get(
    'DATADIR',
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "data")))

DATABASE_FILE = os.environ.get(
    'DATABASE_FILE', os.path.abspath(os.path.join(DATADIR, "database.sqlite")))

app = flask.Flask(__name__, static_url_path='')


def get_db():
    db = getattr(flask.g, '_database', None)

    def make_dicts(cursor, row):
        return dict((cursor.description[idx][0], value)
                    for idx, value in enumerate(row))

    if db is None:
        db = flask.g._database = sqlite3.connect(DATABASE_FILE)

    db.row_factory = make_dicts
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(flask.g, '_database', None)
    if db is not None:
        db.close()


# TODO: Configurable
def highlight_log(data):
    match = re.compile(r"((ERROR|FAILURE|FAILED))", re.MULTILINE)
    ret = match.sub("<span class='text-white bg-danger'>\\1</span>", data)
    match = re.compile(r"((SUCCESS))", re.MULTILINE)
    ret = match.sub("<span class='text-white bg-success'>\\1</span>", ret)

    match = re.compile(r'password\s*?[:=]([ ]*)?([^"\' \t\n]*)', re.MULTILINE)
    ret = match.sub(
        "password: <span class='bg-dark text-dark'>XXXXXXXXX</span>", ret)

    return ret.replace("\n", "<br/>")


def build_pipelineruns_status():
    ret = []
    cur = get_db().execute(
        "SELECT pr.id as id, json, pr.name as prname, pr.namespace, p.name as pipelinename "
        "from PipelineRun as pr, Pipeline as p where pr.pipelineid == p.id "
        "order by strftime('%s', start_time) desc")
    rv = cur.fetchall()

    for row in rv:
        j = json.loads(row['json'])
        completionTime = 'completionTime' in j and j['completionTime'] or j[
            'startedAt']
        if j['conditions'][0]['reason'] == 'Succeeded':
            classname = 'success'
        elif j['conditions'][0]['reason'] == 'Failed':
            classname = 'danger'
        else:
            classname = 'info'
        ret.append({
            'namespace': row['namespace'],
            'pipelinename': row['pipelinename'],
            'id': row['id'],
            'finishtime': dtparse.parse(completionTime),
            'classname': classname,
            'prname': row['prname']
        })

    cur.close()
    return sorted(ret, key=lambda p: p['finishtime'], reverse=True)


def steps_status(taskrun, namespace, steps):
    ret = []
    for container in steps:
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
            classname = 'secondary'
        else:
            classname = 'warning'
            starttime = None

        cur = get_db().execute(
            "SELECT log from Steps as s, TaskRun as t WHERE s.id == t.id AND t.name==? AND t.namespace==?",
            (taskrun, namespace))
        row = cur.fetchone()
        cur.close()

        # TODO: step time
        ret.append({
            'time': starttime,
            'classname': classname,
            'log': highlight_log(row['log']),
            'stepname': container['name'],
        })

    return sorted(ret, key=lambda p: p['time'])


def build_pr_log(pr):
    # TODO: Query TaskRUNS instead
    cur = get_db().execute(
        "SELECT pr.id as id, json, pr.name as prname, pr.namespace, p.name as pipelinename "
        "from PipelineRun as pr, Pipeline as p where pr.pipelineid == p.id and pr.name == ?"
        "order by strftime('%s', start_time) desc limit 1", (pr, ))
    row = cur.fetchone()
    cur.close()
    if not row:
        flask.abort(404)

    ret = []
    j = json.loads(row['json'])
    pr = row['prname']
    for trn in j['taskRuns']:
        tr = j['taskRuns'][trn]
        if tr['status']['conditions'][0]['reason'] == 'Succeeded':
            emoji = '🤙'
        elif tr['status']['conditions'][0]['reason'] == 'Failed':
            emoji = '🚫'
        elif j['conditions'][0]['status'] == "False" and tr['status'][
                'conditions'][0]['reason'] == 'Running':
            emoji = '🤷'
        else:
            emoji = '🤔'

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
            steps_status(trn, row['namespace'], tr['status']['steps']),
        })

    return sorted(ret, key=lambda p: p['time'])


@app.route('/log/<pr>')
def log(pr):
    return flask.render_template('log.html', pr=pr, prlog=build_pr_log(pr))


@app.route('/')
def index():
    return flask.render_template('index.html', prs=build_pipelineruns_status())


if __name__ == '__main__':
    app.run()
