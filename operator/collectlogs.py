import json
import asyncio
import os
import sqlite3
import sys

import kopf
import kubernetes.client

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common")))

import common
import db

DATADIR = os.environ.get('DATADIR', "./data")
NAMESPACE = os.environ.get('NAMESPACE', 'collectlogs')
DBFILE = os.environ.get(
    'DBFILE',
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data", "database.sqlite")))
if os.environ.get("KUBECONFIG"):
    kubernetes.config.load_kube_config(
        config_file=os.environ.get("KUBECONFIG"))
else:
    kubernetes.config.load_incluster_config()

LOCK: asyncio.Lock  # requires a loop on creation

DB_CONN = sqlite3.connect(DBFILE, check_same_thread=False)
CURSOR = DB_CONN.cursor()
db.create_table(CURSOR)


@kopf.on.startup()
async def startup_fn_simple(logger, **kwargs):
    logger.info("Initialising the task-lock...")
    global LOCK
    LOCK = asyncio.Lock()  # in the current asyncio loop


def parse_event(kwargs):
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

    pipelineID = db.insert_if_not_exists(
        CURSOR, "Pipeline", name=pipelineName, namespace=namespace)
    pipelineRunID = db.insert_if_not_exists(
        CURSOR,
        "PipelineRun",
        existence=("name", "namespace", "start_time"),
        name=pipelineRunName,
        namespace=namespace,
        start_time=start_time,
        completion_time=completion_time,
        status=status,
        pipelineID=pipelineID,
        json=json.dumps(jeez),
    )

    apiv1 = kubernetes.client.CoreV1Api()
    prinfo = kwargs['body']
    for tr in prinfo['status']['taskRuns']:
        trinfo = prinfo['status']['taskRuns'][tr]
        trstatus = common.statusName("SUCCESS")
        if trinfo['status']['conditions'][0]['reason'].lower().startswith(
                "fail"):
            trstatus = common.statusName("FAILURE")

        podname = trinfo['status']['podName']
        if 'completionTime' in trinfo['status']:
            completionTime = trinfo['status']['completionTime']
        else:
            completionTime = None
        taskRunID = db.insert_if_not_exists(
            CURSOR,
            "TaskRun",
            existence=("name", "namespace", "pipelineRunID"),
            name=tr,
            namespace=namespace,
            start_time=trinfo['status']['startTime'],
            completion_time=completionTime,
            podName=podname,
            status=trstatus,
            json=json.dumps(trinfo['status']),
            pipelineRunID=pipelineRunID)

        for container in prinfo['status']['taskRuns'][tr]['status']['steps']:
            cntlog = apiv1.read_namespaced_pod_log(
                pretty=True,
                container=container['container'],
                name=podname,
                namespace=kwargs['namespace'])

            db.insert_if_not_exists(
                CURSOR,
                "Steps",
                existence=("name", "namespace", "taskRunID"),
                name=container['name'],
                namespace=namespace,
                taskRunID=taskRunID,
                log=cntlog,
            )

    DB_CONN.commit()


@kopf.on.field(
    'tekton.dev', 'v1alpha1', 'pipelineruns', field='status.conditions')
async def condition_change(spec, **kwargs):
    if 'new' not in kwargs:
        return

    async with LOCK:
        parse_event(kwargs)
