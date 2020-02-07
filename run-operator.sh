#!/usr/bin/env bash
set -eu
args=""
TARGET_NAMESPACE=${TARGET_NAMESPACE:-""}

[[ -n ${TARGET_NAMESPACE} ]] && args="-n ${TARGET_NAMESPACE}"
[[ -e ./operator/collectlogs.py ]] && operator_path=./operator/collectlogs.py
[[ -e /src/operator/collectlogs.py ]] && operator_path=/src/operator/collectlogs.py


exec kopf run ${args} ${operator_path}
