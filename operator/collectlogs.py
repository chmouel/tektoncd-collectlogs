import json
import os
import sqlite3
import sys

import kopf

import kubernetes.client

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common")))

import db
import common

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

DB_CONN = sqlite3.connect(DBFILE, check_same_thread=False)
CURSOR = DB_CONN.cursor()
db.create_table(CURSOR)


@kopf.on.field(
    'tekton.dev', 'v1alpha1', 'pipelineruns', field='status.conditions')
def condition_change(spec, **kwargs):
    if 'new' not in kwargs:
        return

    fpath = os.path.join(DATADIR, kwargs['name'] + ".json")
    if os.path.exists(fpath):
        counter = 0
        while True:
            counter += 1
            fpath = os.path.join(DATADIR,
                                 "%s-%d.json" % (kwargs['name'], counter))
            if not os.path.exists(fpath):
                break
    pipelineName = kwargs['body']['spec']['pipelineRef']['name']
    pipelineRunName = kwargs['name']
    namespace = kwargs['namespace']
    start_time = kwargs['status']['startTime']
    completion_time = kwargs['status']['completionTime']
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
        taskRunID = db.insert_if_not_exists(
            CURSOR,
            "TaskRun",
            existence=("name", "namespace", "pipelineRunID"),
            name=tr,
            namespace=namespace,
            start_time=trinfo['status']['startTime'],
            completion_time=trinfo['status']['completionTime'],
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
                name=container['name'],
                namespace=namespace,
                taskRunID=taskRunID,
                log=cntlog,
            )

    DB_CONN.commit()
