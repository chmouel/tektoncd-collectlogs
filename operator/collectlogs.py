import json
import os

import kopf
import kubernetes.client

DATADIR = os.environ.get('DATADIR', "./data")
NAMESPACE = os.environ.get('NAMESPACE', 'collectlogs')
if os.environ.get("KUBECONFIG"):
    kubernetes.config.load_kube_config(
        config_file=os.environ.get("KUBECONFIG"))
else:
    kubernetes.config.load_incluster_config()


@kopf.on.field(
    'tekton.dev', 'v1alpha1', 'pipelineruns', field='status.conditions')
def condition_change(spec, **kwargs):
    if 'new' in kwargs:
        fpath = os.path.join(DATADIR, kwargs['name'] + ".json")
        if os.path.exists(fpath):
            counter = 0
            while True:
                counter += 1
                fpath = os.path.join(DATADIR,
                                     "%s-%d.json" % (kwargs['name'], counter))
                if not os.path.exists(fpath):
                    break
        name = spec['pipelineRef']['name']
        reason = kwargs['status']['conditions'][0]['reason']
        msg = '%s has %s' % (name, reason)
        if reason == " FailedTasks: ":
            treason = '['
            for t in kwargs['status']['taskRuns']:
                tr = kwargs['status']['taskRuns'][t]
                taskName = tr['pipelineTaskName']
                treason = tr['status']['conditions'][0]['reason']
                if treason == "Failed":
                    treason += "taskName=%s Log:'%s', " % (
                        taskName, tr['status']['conditions'][0]['message'])
            treason += ']'
            msg += treason
        jeez = dict(kwargs['status'])
        jeez['namespace'] = kwargs['namespace']
        jeez['pipelineName'] = kwargs['body']['spec']['pipelineRef']['name']
        jeez['pipelinerunName'] = kwargs['name']
        # import pprint
        # with open("/tmp/debug.txt", 'w') as fp:
        #     fp.write(pprint.pformat(kwargs, indent=2))
        apicustom = kubernetes.client.CustomObjectsApi()

        with open(fpath, 'w') as fp:
            fp.write(json.dumps(jeez))
        apicustom = kubernetes.client.CustomObjectsApi()
        apiv1 = kubernetes.client.CoreV1Api()

        prinfo = apicustom.get_namespaced_custom_object(
            namespace=kwargs['namespace'],
            name=kwargs['name'],
            group="tekton.dev",
            version="v1alpha1",
            plural='pipelineruns')
        for tr in prinfo['status']['taskRuns']:
            podname = prinfo['status']['taskRuns'][tr]['status']['podName']
            for container in prinfo['status']['taskRuns'][tr]['status'][
                    'steps']:
                cntlog = apiv1.read_namespaced_pod_log(
                    pretty=True,
                    container=container['container'],
                    name=podname,
                    namespace=kwargs['namespace'])
                flog = os.path.join(
                    DATADIR, kwargs['name'] + "-" + podname + "-" +
                    container['container'] + ".log")
                if not cntlog:
                    cntlog = "No log 🤨"
                open(flog, 'w').write(cntlog)
    return
