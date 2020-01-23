#!/usr/bin/env bash
TARGET_NAMESPACE=collectlogs

K="kubectl -n ${TARGET_NAMESPACE}"
O="oc -n ${TARGET_NAMESPACE}"

# Create Project where we are going to work on
oc project ${TARGET_NAMESPACE} 2>/dev/null >/dev/null || {
	oc new-project ${TARGET_NAMESPACE} >/dev/null
}

for file in templates/pipeline-randomwords.yaml templates/triggers-collectlogs.yaml;do
    ${K} delete -f  ${file} 2>/dev/null || true
    ${K} create -f ${file}
done


echo "Webhook Endpoint available at: https://$(${O} get route el-collectlogs -o jsonpath='{.spec.host}')"
