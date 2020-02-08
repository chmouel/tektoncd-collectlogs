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
import sys

import flask
import humanfriendly
from dateutil import parser as dtparse

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common")))

import db as dbcommon  # noqa: E402
import common  # noqa: E402

DATADIR = os.environ.get(
    'DATADIR',
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "data")))

DATABASE_FILE = os.environ.get(
    'DATABASE_FILE', os.path.abspath(os.path.join(DATADIR, "database.sqlite")))

app = flask.Flask(__name__, static_url_path='')
Engine, Session = dbcommon.start_engine(DATABASE_FILE)


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
    pipelineruns = flask.g.session.query(dbcommon.Pipelineruns,
                                         dbcommon.Pipelines).join(
                                             dbcommon.Pipelines).all()

    for pipelinerun, pipeline in pipelineruns:
        j = json.loads(pipelinerun.json)
        if j['conditions'][0]['reason'] == 'Succeeded':
            classname = 'success'
        elif j['conditions'][0]['reason'] == 'Failed':
            classname = 'danger'
        else:
            classname = 'info'
        tooltip = f"""
        Status: {j['conditions'][0]['reason']}
        Reason: {j['conditions'][0]['message']}
        StartTime: {j['startTime']}
        """
        if 'completionTime' in j:
            elapsed = humanfriendly.format_timespan(
                dtparse.parse(j['completionTime']) -
                dtparse.parse(j['startTime']))
            tooltip += f"""CompletionTime: {j['completionTime']}
        ElapsedTime: {elapsed}"""

        ret.append({
            'namespace': pipelinerun.namespace,
            'pipelinename': pipeline.name,
            'id': pipelinerun.id,
            'starttime': pipelinerun.start_time,
            'classname': classname,
            'prname': pipelinerun.name,
            'tooltip': tooltip
        })

    return sorted(ret, key=lambda p: p['starttime'], reverse=True)


def steps_status(taskrun_id, jeez):
    ret = []
    steps = flask.g.session.query(
        dbcommon.Steps).filter(dbcommon.Steps.taskrun_id == taskrun_id).all()

    for step in steps:
        # Using the json which me no like we need to store the status in table
        # and be done with this, until then doing that stupid thing
        for x in jeez['steps']:
            if x['name'] == step.name:
                container = x
        # TODO: handle erorr not found
        if 'terminated' in container and container['terminated'][
                'exitCode'] == common.statusName("SUCCESS"):
            classname = 'success'
            starttime = dtparse.parse(container['terminated']['startedAt'])
        elif 'terminated' in container and container['terminated'][
                'exitCode'] > common.statusName("SUCCESS"):
            classname = 'danger'
            starttime = dtparse.parse(container['terminated']['startedAt'])
        elif 'running' in container:
            starttime = dtparse.parse(container['running']['startedAt'])
            classname = 'secondary'
        else:
            classname = 'warning'
            starttime = None

        # TODO: step time
        ret.append({
            'time': starttime,
            'classname': classname,
            'log': highlight_log(step.log),
            'stepname': step.name,
        })

    return sorted(ret, key=lambda p: p['time'])


def build_pr_log(pr_name):
    pr_id = flask.request.args.get('id')
    if not pr_id:
        filter_by = (dbcommon.Pipelineruns.name == pr_name)
        pr = flask.g.session.query(
            dbcommon.Pipelineruns).filter(filter_by).first()
        if not pr:
            flask.abort(404)
        pr_id = pr.id

    taskruns = flask.g.session.query(dbcommon.Taskruns).filter(
        dbcommon.Taskruns.pipelinerun_id == pr_id).all()

    if not taskruns:
        flask.abort(404)

    ret = []
    for task in taskruns:
        elapsed = ""
        if task.status == common.statusName("SUCCESS"):
            status = 'SUCCESS'
            classname = 'success'
        elif task.status == common.statusName("FAILURE"):
            status = 'FAILURE'
            classname = 'danger'
        elif task.status == common.statusName("WAITING"):
            status = "WAIT"
            classname = 'secondary'
        else:
            status = "UNKNOWN"
            classname = 'warning'

        if task.completion_time:
            time = task.completion_time
        else:
            time = task.start_time

        if task.completion_time:
            elapsed = humanfriendly.format_timespan(task.completion_time -
                                                    task.start_time)
        ret.append({
            'time': time,
            'elapsed': elapsed,
            'start_time': task.start_time,
            'classname': classname,
            'status': status,
            'taskrun': task.name,
            'steps': steps_status(task.id, json.loads(task.json)),
        })

    return sorted(ret, key=lambda p: p['time'])


@app.before_request
def create_session():
    flask.g.session = Session()


@app.teardown_appcontext
def shutdown_session(response_or_exc):
    flask.g.session.commit()


@app.route('/log/<pr>')
def log(pr):
    return flask.render_template('log.html', pr=pr, prlog=build_pr_log(pr))


@app.route('/')
def index():
    return flask.render_template('index.html', prs=build_pipelineruns_status())


if __name__ == '__main__':
    app.run()
