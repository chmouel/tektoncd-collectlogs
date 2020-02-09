import asyncio
import http.client
import json
import os
import sys
import ssl
import urllib.parse

import kopf
from dateutil import parser as dtparse

import kubernetes.client

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common")))

import common  # noqa: E402
import db  # noqa: E402

TRIGGERS_URL = os.environ.get('TRIGGERS_URL')
NAMESPACE = os.environ.get('NAMESPACE', 'collectlogs')
DATADIR = os.environ.get('DATADIR', "./data")
DATABASE_FILE = os.environ.get(
    'DATABASE_FILE', os.path.abspath(os.path.join(DATADIR, "database.sqlite")))

if os.environ.get("KUBECONFIG"):
    kubernetes.config.load_kube_config(
        config_file=os.environ.get("KUBECONFIG"))
else:
    kubernetes.config.load_incluster_config()

LOCK: asyncio.Lock  # requires a loop on creation

Engine, Session = db.start_engine(DATABASE_FILE)


@kopf.on.startup()
async def startup_fn_simple(logger, **kwargs):
    logger.info("Initialising the task-lock...")
    global LOCK
    LOCK = asyncio.Lock()  # in the current asyncio loop


def store_pipelinerun(kwargs):
    session = Session()

    pipelineName = kwargs['body']['spec']['pipelineRef']['name']
    pipelineRunName = kwargs['name']
    namespace = kwargs['namespace']
    start_time = kwargs['status']['startTime']
    if 'completion_time' in kwargs['status']:
        completion_time = kwargs['status']['completionTime']
    else:
        completion_time = None
    jeez = dict(kwargs['status'])
    jeez['namespace'] = namespace
    jeez['pipelineName'] = pipelineName
    jeez['pipelinerunName'] = pipelineRunName

    status = common.statusName("SUCCESS")
    if kwargs['status']['conditions'][0]['reason'].lower().startswith("fail"):
        status = common.statusName("FAILURE")

    pipeline = db.get_or_create(
        session, db.Pipelines, name=pipelineName, namespace=namespace)

    pipelinerun = db.get_or_create(
        session,
        db.Pipelineruns,
        name=pipelineRunName,
        namespace=namespace,
        start_time=dtparse.parse(start_time),
        completion_time=completion_time and dtparse.parse(completion_time),
        status=status,
        pipeline_id=pipeline.id,
        json=json.dumps(jeez),
    )

    apiv1 = kubernetes.client.CoreV1Api()
    prinfo = kwargs['body']
    for tr in prinfo['status']['taskRuns']:
        trinfo = prinfo['status']['taskRuns'][tr]
        trstatus = common.statusName("SUCCESS")
        trname = trinfo['pipelineTaskName']
        if trinfo['status']['conditions'][0]['reason'].lower().startswith(
                "fail"):
            trstatus = common.statusName("FAILURE")

        podname = trinfo['status']['podName']
        if 'completionTime' in trinfo['status']:
            completionTime = dtparse.parse(trinfo['status']['completionTime'])
        else:
            completionTime = None

        taskrun = db.get_or_create(
            session,
            db.Taskruns,
            name=trname,
            namespace=namespace,
            start_time=dtparse.parse(trinfo['status']['startTime']),
            completion_time=completionTime,
            pod_name=podname,
            status=trstatus,
            json=json.dumps(trinfo['status']),
            pipelinerun_id=pipelinerun.id)
        taskrun_id = taskrun.id

        for container in prinfo['status']['taskRuns'][tr]['status']['steps']:
            cntlog = apiv1.read_namespaced_pod_log(
                pretty=True,
                container=container['container'],
                name=podname,
                namespace=kwargs['namespace'])

            db.get_or_create(
                session,
                db.Steps,
                name=container['name'],
                namespace=namespace,
                taskrun_id=taskrun_id,
                log=cntlog,
            )


def send_triggers(jeez):
    u = urllib.parse.urlparse(TRIGGERS_URL)
    conn = http.client.HTTPSConnection(
        u.netloc,
        context="TRIGGERS_URL_SELF_SIGNED" in os.environ
        and ssl._create_unverified_context() or None)
    conn.request(
        "POST",
        u.path,
        body=json.dumps(jeez),
        headers={
            "User-Agent": "Tekton Collectlogs your friendly neighbour",
        })
    resp = conn.getresponse()
    # json.dump(jeez, open("/tmp/dump.json", 'w'))
    if not str(resp.status).startswith("2"):
        print("Error: %d" % (resp.status))
        print(resp.read())
    else:
        print(f"Webhook result has been posted to {TRIGGERS_URL}")


@kopf.on.field(
    'tekton.dev', 'v1alpha1', 'pipelineruns', field='status.conditions')
async def condition_change(spec, **kwargs):
    if 'new' not in kwargs:
        return

    async with LOCK:
        store_pipelinerun(kwargs)
        if TRIGGERS_URL:
            send_triggers(dict(kwargs['body']))
