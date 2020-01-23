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
        with open(fpath, 'w') as fp:
            fp.write(json.dumps(dict(kwargs['status'])))
        apicustom = kubernetes.client.CustomObjectsApi()
        apiv1 = kubernetes.client.CoreV1Api()

        prinfo = apicustom.get_namespaced_custom_object(
            namespace=NAMESPACE,
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
                    namespace=NAMESPACE)
                flog = os.path.join(
                    DATADIR, kwargs['name'] + "-" + podname + "-" +
                    container['container'] + ".log")
                open(flog, 'w').write(cntlog)
    return
